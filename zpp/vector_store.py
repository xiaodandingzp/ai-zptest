"""向量数据库模块 - 使用 ChromaDB 存储 and 检索向量"""

import os
from pathlib import Path
from typing import List, Optional

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import Chroma
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

# Embeddings 可选：优先使用本地模型，其次使用 OpenAI
EMBEDDINGS_TYPE = None  # 'local' or 'openai'

try:
    from langchain_community.embeddings import HuggingFaceEmbeddings
    EMBEDDINGS_TYPE = 'local'
except ImportError:
    try:
        from langchain_openai import OpenAIEmbeddings
        EMBEDDINGS_TYPE = 'openai'
    except ImportError:
        pass


class VectorStore:
    """向量数据库管理类"""
    
    def __init__(self, persist_directory: Optional[str] = None):
        """
        初始化向量数据库
        
        Args:
            persist_directory: 数据库持久化目录，默认为 ~/.zpp/chroma_db
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError(
                "请安装 langchain 相关依赖: pip install langchain langchain-community langchain-openai chromadb"
            )
        
        if persist_directory is None:
            persist_directory = str(Path.home() / '.zpp' / 'chroma_db')
        
        self.persist_directory = persist_directory
        self._vectorstore = None
        self._embeddings = None
        
        # 确保目录存在
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
    
    def _get_embeddings(self, api_key: str = None, api_base: Optional[str] = None):
        """获取嵌入模型（优先使用本地模型）"""
        if self._embeddings is None:
            if EMBEDDINGS_TYPE == 'local':
                # 使用本地 HuggingFace 模型，不需要 API Key
                self._embeddings = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                    model_kwargs={'device': 'cpu'},
                    encode_kwargs={'normalize_embeddings': True}
                )
            elif EMBEDDINGS_TYPE == 'openai':
                if not api_key:
                    raise ValueError("使用 OpenAI Embeddings 需要提供 API Key")
                from langchain_openai import OpenAIEmbeddings
                self._embeddings = OpenAIEmbeddings(
                    openai_api_key=api_key,
                    openai_api_base=api_base
                )
            else:
                raise ImportError("没有可用的 Embeddings 模型，请安装: pip install sentence-transformers")
        return self._embeddings
    
    def create_from_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[dict]] = None,
        api_key: str = None,
        api_base: Optional[str] = None,
        collection_name: str = "knowledge"
    ):
        """
        从文本列表创建向量数据库
        
        Args:
            texts: 文本列表
            metadatas: 元数据列表
            api_key: OpenAI API Key (仅 OpenAI Embeddings 需要)
            api_base: API 基础地址
            collection_name: 集合名称
        """
        # 先清空旧的向量数据库
        self.clear()
        
        embeddings = self._get_embeddings(api_key, api_base)
        
        # 文本分割
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        
        split_texts = []
        split_metadatas = []
        
        for i, text in enumerate(texts):
            chunks = text_splitter.split_text(text)
            split_texts.extend(chunks)
            if metadatas:
                for chunk in chunks:
                    split_metadatas.append(metadatas[i] if i < len(metadatas) else {})
        
        # 创建向量数据库
        self._vectorstore = Chroma.from_texts(
            texts=split_texts,
            embedding=embeddings,
            metadatas=split_metadatas if split_metadatas else None,
            persist_directory=self.persist_directory,
            collection_name=collection_name
        )
        
        # 持久化
        self._vectorstore.persist()
        
        return len(split_texts)
    
    def load_vectorstore(
        self,
        api_key: str,
        api_base: Optional[str] = None,
        collection_name: str = "knowledge"
    ):
        """加载已有的向量数据库"""
        embeddings = self._get_embeddings(api_key, api_base)
        
        self._vectorstore = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=embeddings,
            collection_name=collection_name
        )
        
        return self._vectorstore
    
    def similarity_search(self, query: str, k: int = 4) -> List[dict]:
        """
        相似度搜索
        
        Args:
            query: 查询文本
            k: 返回结果数量
            
        Returns:
            匹配的文档列表
        """
        if self._vectorstore is None:
            raise ValueError("向量数据库未初始化，请先调用 load_vectorstore 或 create_from_texts")
        
        results = self._vectorstore.similarity_search(query, k=k)
        
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata
            }
            for doc in results
        ]
    
    def get_retriever(self, k: int = 4):
        """获取检索器"""
        if self._vectorstore is None:
            raise ValueError("向量数据库未初始化")
        
        return self._vectorstore.as_retriever(search_kwargs={"k": k})
    
    def clear(self, collection_name: str = "knowledge"):
        """清空向量数据库"""
        if os.path.exists(self.persist_directory):
            import shutil
            shutil.rmtree(self.persist_directory)
            Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        self._vectorstore = None


def is_vectorstore_available() -> bool:
    """检查向量数据库功能是否可用"""
    return LANGCHAIN_AVAILABLE and CHROMADB_AVAILABLE
