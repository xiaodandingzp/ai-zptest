from flask import Flask, render_template, jsonify, request
from .config import ConfigManager
from .llm import LLMClient
import os

def create_app():
    """创建 Flask 应用"""
    app = Flask(__name__,
                template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
    app.secret_key = 'zpp-secret-key-2024'
    
    config_manager = ConfigManager()
    llm_client = LLMClient()
    
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
        
        # 更新配置（只有提供了新值才更新）
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
        
        if not messages:
            return jsonify({'error': '消息不能为空'}), 400
        
        try:
            response = llm_client.chat(messages)
            return jsonify({'success': True, 'response': response})
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': f'对话失败: {str(e)}'}), 500
    
    return app
