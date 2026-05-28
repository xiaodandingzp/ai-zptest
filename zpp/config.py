import os
import json
from pathlib import Path

# 模型提供商配置模板
PROVIDER_TEMPLATES = {
    "openai": {
        "name": "OpenAI",
        "models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "gpt-4o"],
        "env_key": "OPENAI_API_KEY",
        "default_api_base": "https://api.openai.com/v1"
    },
    "deepseek": {
        "name": "DeepSeek",
        "models": ["deepseek-chat", "deepseek-coder", "deepseek-v4-pro"],
        "env_key": "DEEPSEEK_API_KEY",
        "default_api_base": "https://api.deepseek.com"
    },
    "anthropic": {
        "name": "Anthropic (Claude)",
        "models": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
        "env_key": "ANTHROPIC_API_KEY",
        "default_api_base": "https://api.anthropic.com"
    },
    "qwen": {
        "name": "通义千问",
        "models": ["qwen-turbo", "qwen-plus", "qwen-max"],
        "env_key": "DASHSCOPE_API_KEY",
        "default_api_base": "https://dashscope.aliyuncs.com/api/v1"
    },
    "zhipu": {
        "name": "智谱 AI",
        "models": ["glm-4", "glm-4-flash", "glm-3-turbo"],
        "env_key": "ZHIPUAI_API_KEY",
        "default_api_base": "https://open.bigmodel.cn/api/paas/v4"
    }
}


class ConfigManager:
    """管理应用配置 - 支持多模型配置"""
    
    def __init__(self):
        self.config_dir = Path.home() / '.zpp'
        self.config_file = self.config_dir / 'config.json'
        self.ensure_config_dir()
    
    def ensure_config_dir(self):
        """确保配置目录存在"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        if not self.config_file.exists():
            self.save_config(self._get_default_config())
    
    def _get_default_config(self):
        """获取默认配置"""
        return {
            "current_model": "deepseek-chat",
            "models": {
                "deepseek-chat": {
                    "provider": "deepseek",
                    "display_name": "DeepSeek Chat",
                    "model": "deepseek/deepseek-chat",
                    "api_key": "",
                    "api_base": "https://api.deepseek.com"
                },
                "gpt-3.5-turbo": {
                    "provider": "openai",
                    "display_name": "GPT-3.5 Turbo",
                    "model": "gpt-3.5-turbo",
                    "api_key": "",
                    "api_base": ""
                }
            }
        }
    
    def get_config(self):
        """获取完整配置"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 确保配置结构完整
                if "models" not in config:
                    config = self._get_default_config()
                    self.save_config(config)
                return config
        except Exception:
            return self._get_default_config()
    
    def save_config(self, config):
        """保存完整配置"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def get_current_model_config(self):
        """获取当前使用的模型配置"""
        config = self.get_config()
        current_model = config.get("current_model", "")
        models = config.get("models", {})
        return models.get(current_model, {})
    
    def get_current_model_name(self):
        """获取当前模型名称"""
        config = self.get_config()
        return config.get("current_model", "")
    
    def set_current_model(self, model_id):
        """设置当前使用的模型"""
        config = self.get_config()
        if model_id in config.get("models", {}):
            config["current_model"] = model_id
            self.save_config(config)
            return True
        return False
    
    def get_model_config(self, model_id):
        """获取指定模型的配置"""
        config = self.get_config()
        models = config.get("models", {})
        return models.get(model_id, {})
    
    def save_model_config(self, model_id, model_config):
        """保存指定模型的配置"""
        config = self.get_config()
        if "models" not in config:
            config["models"] = {}
        config["models"][model_id] = model_config
        self.save_config(config)
    
    def add_model(self, model_id, provider, display_name, model_name, api_key="", api_base=""):
        """添加新模型配置"""
        config = self.get_config()
        if "models" not in config:
            config["models"] = {}
        
        # 获取提供商默认 API base
        provider_info = PROVIDER_TEMPLATES.get(provider, {})
        default_base = provider_info.get("default_api_base", "")
        
        config["models"][model_id] = {
            "provider": provider,
            "display_name": display_name,
            "model": model_name,
            "api_key": api_key,
            "api_base": api_base or default_base
        }
        self.save_config(config)
    
    def delete_model(self, model_id):
        """删除模型配置"""
        config = self.get_config()
        if model_id in config.get("models", {}):
            del config["models"][model_id]
            # 如果删除的是当前模型，切换到第一个可用模型
            if config.get("current_model") == model_id:
                models = config.get("models", {})
                config["current_model"] = list(models.keys())[0] if models else ""
            self.save_config(config)
            return True
        return False
    
    def list_models(self):
        """列出所有模型配置"""
        config = self.get_config()
        return config.get("models", {})
    
    def get_providers(self):
        """获取支持的提供商列表"""
        return PROVIDER_TEMPLATES
