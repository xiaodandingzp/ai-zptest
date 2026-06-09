"""知识库处理模块"""

import os
from pathlib import Path
from typing import List, Tuple, Optional
from .config import ConfigManager
from .vector_store import VectorStore, is_vectorstore_available

# 尝试导入 docx 支持
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


class KnowledgeManager:
    """知识库管理类"""
    
    def __init__(self, knowledge_dir: Optional[str] = None):
        """
        初始化知识库管理器
        
        Args:
            knowledge_dir: 知识库目录，默认为项目下的 knowlage 文件夹
        """
        if knowledge_dir is None:
            # 默认使用 zpp 包下的 knowlage 目录
            package_dir = Path(__file__).parent
            knowledge_dir = package_dir / "knowlage"
        
        self.knowledge_dir = Path(knowledge_dir)
        self.config_manager = ConfigManager()
        self.vector_store = None
    
    def scan_knowledge_files(self) -> List[Path]:
        """扫描知识库目录下的所有文件"""
        if not self.knowledge_dir.exists():
            return []
        
        supported_extensions = ['.txt', '.md', '.json', '.py', '.js', '.html', '.css', '.docx']
        files = []
        
        for ext in supported_extensions:
            files.extend(self.knowledge_dir.glob(f'*{ext}'))
        
        # 也支持子目录
        for ext in supported_extensions:
            files.extend(self.knowledge_dir.glob(f'**/*{ext}'))
        
        # 去重
        files = list(set(files))
        
        return files
    
    def read_file(self, file_path: Path) -> Tuple[str, dict]:
        """
        读取文件内容
        
        Args:
            file_path: 文件路径
            
        Returns:
            (文件内容, 元数据)
        """
        metadata = {
            "source": str(file_path),
            "filename": file_path.name,
            "extension": file_path.suffix
        }
        
        try:
            # 处理 docx 文件
            if file_path.suffix.lower() == '.docx':
                if not DOCX_AVAILABLE:
                    print(f"跳过 {file_path}: 需要安装 python-docx: pip install python-docx")
                    return "", metadata
                
                return self._read_docx(file_path, metadata)
            
            # 处理其他文本文件
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return content, metadata
        except Exception as e:
            print(f"读取文件失败 {file_path}: {e}")
            return "", metadata
    
    def _read_docx(self, file_path: Path, metadata: dict) -> Tuple[str, dict]:
        """读取 docx 文件内容"""
        try:
            doc = Document(str(file_path))
            
            # 提取所有段落文本
            paragraphs = []
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    paragraphs.append(text)
            
            # 也提取表格内容
            for table in doc.tables:
                for row in table.rows:
                    row_text = ' | '.join(cell.text.strip() for cell in row.cells)
                    if row_text.strip():
                        paragraphs.append(row_text)
            
            content = '\n\n'.join(paragraphs)
            return content, metadata
            
        except Exception as e:
            print(f"读取 docx 文件失败 {file_path}: {e}")
            return "", metadata
    
    def init_knowledge_base(self, verbose: bool = True) -> dict:
        """
        初始化知识库 - 读取文件并构建向量数据库
        
        Args:
            verbose: 是否输出详细信息
            
        Returns:
            初始化结果
        """
        if not is_vectorstore_available():
            return {
                "success": False,
                "error": "向量数据库功能不可用，请安装依赖: pip install langchain langchain-community langchain-openai chromadb"
            }
        
        # 获取当前模型配置
        model_config = self.config_manager.get_current_model_config()
        if not model_config:
            return {
                "success": False,
                "error": "未配置模型，请先配置模型"
            }
        
        api_key = model_config.get("api_key", "")
        api_base = model_config.get("api_base", "")
        
        if not api_key:
            return {
                "success": False,
                "error": "API Key 未配置"
            }
        
        # 扫描文件
        files = self.scan_knowledge_files()
        if not files:
            return {
                "success": False,
                "error": f"知识库目录 {self.knowledge_dir} 下没有找到支持的文件"
            }
        
        if verbose:
            print(f"找到 {len(files)} 个文件:")
            for f in files:
                print(f"  - {f}")
        
        # 读取文件内容
        texts = []
        metadatas = []
        
        for file_path in files:
            content, metadata = self.read_file(file_path)
            if content:
                texts.append(content)
                metadatas.append(metadata)
                if verbose:
                    print(f"已读取: {file_path.name} ({len(content)} 字符)")
        
        if not texts:
            return {
                "success": False,
                "error": "没有成功读取任何文件内容"
            }
        
        # 创建向量数据库
        try:
            self.vector_store = VectorStore()
            chunk_count = self.vector_store.create_from_texts(
                texts=texts,
                metadatas=metadatas,
                api_key=api_key,
                api_base=api_base
            )
            
            if verbose:
                print(f"\n成功创建向量数据库:")
                print(f"  - 文件数: {len(files)}")
                print(f"  - 文本块数: {chunk_count}")
            
            return {
                "success": True,
                "file_count": len(files),
                "chunk_count": chunk_count,
                "files": [str(f) for f in files]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"创建向量数据库失败: {str(e)}"
            }
    
    def search(self, query: str, k: int = 4) -> List[dict]:
        """
        搜索相关知识
        
        Args:
            query: 查询文本
            k: 返回结果数量
            
        Returns:
            相关知识列表
        """
        if not is_vectorstore_available():
            return []
        
        try:
            # 获取配置
            model_config = self.config_manager.get_current_model_config()
            if not model_config:
                return []
            
            api_key = model_config.get("api_key", "")
            api_base = model_config.get("api_base", "")
            
            if not api_key:
                return []
            
            # 加载向量数据库
            if self.vector_store is None:
                self.vector_store = VectorStore()
                self.vector_store.load_vectorstore(api_key, api_base)
            
            # 搜索
            return self.vector_store.similarity_search(query, k=k)
            
        except Exception as e:
            print(f"搜索失败: {e}")
            return []
    
    def get_context_for_query(self, query: str, k: int = 4) -> str:
        """
        获取查询的上下文
        
        Args:
            query: 查询文本
            k: 返回结果数量
            
        Returns:
            拼接的上下文字符串
        """
        results = self.search(query, k)
        
        if not results:
            return ""
        
        context_parts = []
        for i, item in enumerate(results, 1):
            source = item.get("metadata", {}).get("filename", "未知来源")
            content = item.get("content", "")
            context_parts.append(f"[参考资料 {i} - {source}]\n{content}\n")
        
        return "\n".join(context_parts)
    
    def clear_knowledge_base(self):
        """清空知识库"""
        if self.vector_store:
            self.vector_store.clear()
        self.vector_store = None
    
    def get_supported_extensions(self) -> List[str]:
        """获取支持的文件扩展名"""
        return ['.txt', '.md', '.json', '.py', '.js', '.html', '.css', '.docx']
    
    def is_supported_file(self, filename: str) -> bool:
        """检查文件是否支持"""
        ext = Path(filename).suffix.lower()
        # 打印ext
        print(f"检查文件扩展名: {ext} filename: {filename}")
        return ext in self.get_supported_extensions()
    
    def list_knowledge_files(self) -> List[dict]:
        """列出知识库目录下的所有文件信息"""
        if not self.knowledge_dir.exists():
            return []
        
        files = []
        for file_path in self.knowledge_dir.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "name": file_path.name,
                    "path": str(file_path),
                    "extension": file_path.suffix,
                    "size": stat.st_size,
                    "size_display": self._format_file_size(stat.st_size),
                    "supported": self.is_supported_file(file_path.name),
                    "modified": stat.st_mtime
                })
        
        # 按修改时间排序
        files.sort(key=lambda x: x.get("modified", 0), reverse=True)
        return files
    
    def _format_file_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def add_file(self, filename: str, content: bytes) -> dict:
        """
        添加新文件到知识库
        
        Args:
            filename: 文件名
            content: 文件内容（字节）
            
        Returns:
            添加结果
        """
        # 检查文件名是否合法
        if not filename:
            return {"success": False, "error": "文件名不能为空"}
        
        # 检查文件扩展名
        if not self.is_supported_file(filename):
            return {
                "success": False, 
                "error": f"不支持的文件格式，支持的格式: {', '.join(self.get_supported_extensions())}"
            }
        
        # 检查文件是否已存在
        file_path = self.knowledge_dir / filename
        if file_path.exists():
            return {"success": False, "error": "文件已存在"}
        
        # 确保目录存在
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        try:
            with open(file_path, 'wb') as f:
                f.write(content)
            
            return {
                "success": True, 
                "message": f"文件 {filename} 添加成功",
                "file": {
                    "name": filename,
                    "path": str(file_path),
                    "size": len(content)
                }
            }
        except Exception as e:
            return {"success": False, "error": f"写入文件失败: {str(e)}"}
    
    def delete_file(self, filename: str) -> dict:
        """
        删除知识库中的文件
        
        Args:
            filename: 文件名
            
        Returns:
            删除结果
        """
        file_path = self.knowledge_dir / filename
        
        if not file_path.exists():
            return {"success": False, "error": "文件不存在"}
        
        # 安全检查：确保文件在知识库目录内
        try:
            file_path.resolve().relative_to(self.knowledge_dir.resolve())
        except ValueError:
            return {"success": False, "error": "非法文件路径"}
        
        try:
            file_path.unlink()
            return {"success": True, "message": f"文件 {filename} 已删除"}
        except Exception as e:
            return {"success": False, "error": f"删除文件失败: {str(e)}"}


def format_context_for_chat(query: str, context: str) -> str:
    """
    格式化上下文用于对话
    
    Args:
        query: 用户问题
        context: 检索到的上下文
        
    Returns:
        格式化后的系统提示
    """
    if not context:
        return ""
    
    return f"""基于以下参考资料回答用户问题。如果参考资料中没有相关信息，请根据你的知识回答。

参考资料:
{context}

用户问题: {query}

请回答:"""
