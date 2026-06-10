from flask import Flask, render_template, jsonify, request
from .config import ConfigManager
from .llm import LLMClient
from .knowledge import (
    KnowledgeManager, KnowledgeBaseManager, 
    is_vectorstore_available, get_context_from_selected_bases
)
import os

def create_app():
    """创建 Flask 应用"""
    app = Flask(__name__,
                template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
    app.secret_key = 'zpp-secret-key-2024'
    
    config_manager = ConfigManager()
    llm_client = LLMClient()
    base_manager = KnowledgeBaseManager()
    
    @app.route('/')
    def index():
        """主页面"""
        return render_template('index.html')
    
    # ========== 模型管理 API ==========
    
    @app.route('/api/providers', methods=['GET'])
    def get_providers():
        """获取支持的提供商列表"""
        providers = config_manager.get_providers()
        return jsonify(providers)
    
    @app.route('/api/models', methods=['GET'])
    def list_models():
        """列出所有已配置的模型"""
        models = config_manager.list_models()
        current_model = config_manager.get_current_model_name()
        return jsonify({
            "models": models,
            "current_model": current_model
        })
    
    @app.route('/api/models/<model_id>', methods=['GET'])
    def get_model_config(model_id):
        """获取指定模型的配置"""
        model_config = config_manager.get_model_config(model_id)
        if not model_config:
            return jsonify({'error': '模型不存在'}), 404
        
        # 隐藏 API Key
        if model_config.get('api_key'):
            api_key = model_config['api_key']
            if len(api_key) > 8:
                model_config['api_key_display'] = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:]
            else:
                model_config['api_key_display'] = '*' * len(api_key)
        else:
            model_config['api_key_display'] = ''
        
        model_config['api_key'] = ''
        return jsonify(model_config)
    
    @app.route('/api/models/<model_id>', methods=['POST'])
    def save_model_config(model_id):
        """保存模型配置"""
        data = request.json
        current_config = config_manager.get_model_config(model_id)
        
        if not current_config:
            return jsonify({'error': '模型不存在'}), 404
        
        if data.get('api_key'):
            current_config['api_key'] = data['api_key']
        if data.get('api_base') is not None:
            current_config['api_base'] = data['api_base']
        if data.get('display_name'):
            current_config['display_name'] = data['display_name']
        if data.get('model'):
            current_config['model'] = data['model']
        
        config_manager.save_model_config(model_id, current_config)
        return jsonify({'success': True, 'message': '配置保存成功'})
    
    @app.route('/api/models', methods=['POST'])
    def add_model():
        """添加新模型"""
        data = request.json
        model_id = data.get('model_id')
        provider = data.get('provider')
        display_name = data.get('display_name')
        model_name = data.get('model')
        api_key = data.get('api_key', '')
        api_base = data.get('api_base', '')
        
        if not model_id or not provider or not model_name:
            return jsonify({'error': '缺少必要参数'}), 400
        
        config_manager.add_model(model_id, provider, display_name, model_name, api_key, api_base)
        return jsonify({'success': True, 'message': '模型添加成功'})
    
    @app.route('/api/models/<model_id>', methods=['DELETE'])
    def delete_model(model_id):
        """删除模型"""
        success = config_manager.delete_model(model_id)
        if success:
            return jsonify({'success': True, 'message': '模型删除成功'})
        return jsonify({'error': '模型不存在'}), 404
    
    @app.route('/api/models/current', methods=['POST'])
    def set_current_model():
        """设置当前使用的模型"""
        data = request.json
        model_id = data.get('model_id')
        
        if not model_id:
            return jsonify({'error': '缺少模型 ID'}), 400
        
        success = config_manager.set_current_model(model_id)
        if success:
            return jsonify({'success': True, 'message': '已切换模型'})
        return jsonify({'error': '模型不存在'}), 404
    
    # ========== 对话 API ==========
    
    @app.route('/api/chat', methods=['POST'])
    def chat():
        """处理对话请求"""
        data = request.json
        messages = data.get('messages', [])
        use_rag = data.get('use_rag', True)
        
        if not messages:
            return jsonify({'error': '消息不能为空'}), 400
        
        try:
            context = ""
            if use_rag and is_vectorstore_available():
                last_message = messages[-1] if messages else {}
                user_query = last_message.get('content', '')
                
                if user_query:
                    # 从选中的知识库获取上下文
                    context = get_context_from_selected_bases(user_query, k=4)
                    
                    if context:
                        system_message = {
                            "role": "system",
                            "content": f"""你是一个有帮助的AI助手。请根据用户问题，结合参考资料给出回答。如果参考资料中没有相关信息，请根据你的知识回答。

## 参考资料
{context}

## 回答要求
1. **简洁明了**：去除冗余信息，直接回答问题
2. **格式规范**：
   - 使用标题、列表等方式组织内容，便于阅读
   - 代码和命令使用代码块包裹，并标注语言
   - 步骤使用有序列表
   - 重要提示使用引用块
3. **如实回答**：如果参考资料中没有相关信息，请根据你的知识回答"""
                        }
                        messages_with_context = [system_message] + messages
                    else:
                        messages_with_context = messages
                else:
                    messages_with_context = messages
            else:
                messages_with_context = messages
            
            response = llm_client.chat(messages_with_context)
            return jsonify({
                'success': True, 
                'response': response,
                'used_rag': bool(context)
            })
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': f'对话失败: {str(e)}'}), 500
    
    # ========== 知识库管理 API（一级：知识库列表）==========
    
    @app.route('/api/knowledge/bases', methods=['GET'])
    def list_knowledge_bases():
        """列出所有知识库"""
        bases = base_manager.list_knowledge_bases()
        return jsonify({'bases': bases})
    
    @app.route('/api/knowledge/bases', methods=['POST'])
    def create_knowledge_base():
        """创建新知识库"""
        data = request.json
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        if not name:
            return jsonify({'success': False, 'error': '知识库名称不能为空'}), 400
        
        result = base_manager.create_knowledge_base(name, description)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
    
    @app.route('/api/knowledge/bases/<base_id>', methods=['DELETE'])
    def delete_knowledge_base(base_id):
        """删除知识库"""
        result = base_manager.delete_knowledge_base(base_id)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
    
    @app.route('/api/knowledge/bases/<base_id>/select', methods=['POST'])
    def select_knowledge_base(base_id):
        """选择/取消选择知识库"""
        data = request.json
        selected = data.get('selected', True)
        
        result = base_manager.select_knowledge_base(base_id, selected)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
    
    # ========== 知识库管理 API（二级：知识库内容）==========
    
    @app.route('/api/knowledge/bases/<base_id>/files', methods=['GET'])
    def list_base_files(base_id):
        """列出知识库文件"""
        manager = KnowledgeManager(base_id)
        files = manager.list_knowledge_files()
        base_info = base_manager.get_knowledge_base_info(base_id)
        
        return jsonify({
            'files': files,
            'base_info': base_info,
            'knowledge_dir': str(manager.knowledge_dir),
            'supported_extensions': manager.get_supported_extensions()
        })
    
    @app.route('/api/knowledge/bases/<base_id>/files', methods=['POST'])
    def add_base_file(base_id):
        """添加知识库文件"""
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '没有选择文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '没有选择文件'}), 400
        
        original_filename = file.filename
        filename = os.path.basename(original_filename)
        
        if not filename:
            return jsonify({'success': False, 'error': '无效的文件名'}), 400
        
        manager = KnowledgeManager(base_id)
        
        if not manager.is_supported_file(filename):
            return jsonify({
                'success': False, 
                'error': f"不支持的文件格式，支持: {', '.join(manager.get_supported_extensions())}"
            }), 400
        
        content = file.read()
        result = manager.add_file(filename, content)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
    
    @app.route('/api/knowledge/bases/<base_id>/files/<filename>', methods=['DELETE'])
    def delete_base_file(base_id, filename):
        """删除知识库文件"""
        manager = KnowledgeManager(base_id)
        result = manager.delete_file(filename)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
    
    @app.route('/api/knowledge/bases/<base_id>/init', methods=['POST'])
    def init_base_knowledge(base_id):
        """初始化知识库"""
        if not is_vectorstore_available():
            return jsonify({
                'success': False, 
                'error': '向量数据库功能不可用，请安装依赖'
            }), 400
        
        manager = KnowledgeManager(base_id)
        result = manager.init_knowledge_base(verbose=True)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
    
    @app.route('/api/knowledge/bases/<base_id>/clear', methods=['POST'])
    def clear_base_knowledge(base_id):
        """清空知识库向量数据"""
        manager = KnowledgeManager(base_id)
        manager.clear_knowledge_base()
        return jsonify({'success': True, 'message': '知识库已清空'})
    
    @app.route('/api/knowledge/bases/<base_id>/search', methods=['POST'])
    def search_base_knowledge(base_id):
        """搜索知识库"""
        data = request.json
        query = data.get('query', '')
        k = data.get('k', 4)
        
        if not query:
            return jsonify({'error': '查询不能为空'}), 400
        
        manager = KnowledgeManager(base_id)
        results = manager.search(query, k=k)
        
        return jsonify({'results': results})
    
    return app
