from litellm import completion
from .config import ConfigManager, PROVIDER_TEMPLATES
import os
from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """LLM 客户端基类"""
    
    @abstractmethod
    def chat(self, messages, stream=False):
        """调用大模型 API"""
        pass


class LiteLLMClient(BaseLLMClient):
    """使用 litellm 的通用客户端"""
    
    def __init__(self, model_config):
        self.model_config = model_config
        self.provider = model_config.get("provider", "openai")
        self.model = model_config.get("model", "gpt-3.5-turbo")
        self.api_key = model_config.get("api_key", "")
        self.api_base = model_config.get("api_base", "")
    
    def _set_env(self):
        """根据提供商设置环境变量"""
        provider_info = PROVIDER_TEMPLATES.get(self.provider, {})
        env_key = provider_info.get("env_key", "OPENAI_API_KEY")
        os.environ[env_key] = self.api_key
    
    def chat(self, messages, stream=False):
        """调用大模型 API"""
        if not self.api_key:
            raise ValueError("API Key 未配置，请先在模型配置页面设置 API Key")
        
        # 设置环境变量
        self._set_env()
        
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "stream": stream,
            }
            
            if self.api_base:
                kwargs["api_base"] = self.api_base
            
            response = completion(**kwargs)
            
            if stream:
                full_content = ""
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        full_content += chunk.choices[0].delta.content
                return full_content
            else:
                return response.choices[0].message.content
                
        except Exception as e:
            error_msg = str(e)
            if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
                raise ValueError(f"API Key 无效: {error_msg}")
            elif "model" in error_msg.lower():
                raise ValueError(f"模型不可用: {error_msg}")
            else:
                raise Exception(f"API 调用失败: {error_msg}")


class LangChainClient(BaseLLMClient):
    """使用 LangChain 的客户端"""
    
    def __init__(self, model_config):
        self.model_config = model_config
        self.provider = model_config.get("provider", "openai")
        self.model = model_config.get("model", "gpt-3.5-turbo")
        self.api_key = model_config.get("api_key", "")
        self.api_base = model_config.get("api_base", "")
        self._llm = None
    
    def _create_llm(self):
        """创建 LangChain LLM 实例"""
        if not self.api_key:
            raise ValueError("API Key 未配置，请先在模型配置页面设置 API Key")
        
        # 延迟导入，避免未安装时报错
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        except ImportError:
            raise ImportError("请先安装 langchain: pip install langchain langchain-openai langchain-core")
        
        # 根据提供商创建对应的 LLM
        if self.provider in ["openai", "deepseek", "qwen", "zhipu"]:
            # 这些提供商都兼容 OpenAI API
            return ChatOpenAI(
                model=self._get_model_name(),
                api_key=self.api_key,
                base_url=self._get_base_url(),
                temperature=0.7
            )
        elif self.provider == "anthropic":
            try:
                from langchain_anthropic import ChatAnthropic
                return ChatAnthropic(
                    model=self._get_model_name(),
                    api_key=self.api_key,
                    temperature=0.7
                )
            except ImportError:
                raise ImportError("请先安装 langchain-anthropic: pip install langchain-anthropic")
        else:
            # 默认使用 OpenAI 兼容接口
            return ChatOpenAI(
                model=self._get_model_name(),
                api_key=self.api_key,
                base_url=self.api_base or None,
                temperature=0.7
            )
    
    def _get_model_name(self):
        """获取模型名称（去除前缀）"""
        # litellm 格式的模型名如 "deepseek/deepseek-chat"
        # LangChain 需要去除前缀
        if "/" in self.model:
            return self.model.split("/")[-1]
        return self.model
    
    def _get_base_url(self):
        """获取 API 基础地址"""
        if self.api_base:
            return self.api_base
        
        # 使用提供商默认地址
        provider_info = PROVIDER_TEMPLATES.get(self.provider, {})
        return provider_info.get("default_api_base", None)
    
    def _convert_messages(self, messages):
        """转换消息格式为 LangChain 格式"""
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        
        langchain_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))
            elif role == "system":
                langchain_messages.append(SystemMessage(content=content))
        
        return langchain_messages
    
    def chat(self, messages, stream=False):
        """调用大模型 API"""
        if self._llm is None:
            self._llm = self._create_llm()
        
        try:
            # 转换消息格式
            langchain_messages = self._convert_messages(messages)
            
            if stream:
                # 流式输出
                full_content = ""
                for chunk in self._llm.stream(langchain_messages):
                    if chunk.content:
                        full_content += chunk.content
                return full_content
            else:
                # 非流式输出
                response = self._llm.invoke(langchain_messages)
                return response.content
                
        except Exception as e:
            error_msg = str(e)
            if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
                raise ValueError(f"API Key 无效: {error_msg}")
            elif "model" in error_msg.lower():
                raise ValueError(f"模型不可用: {error_msg}")
            else:
                raise Exception(f"API 调用失败: {error_msg}")


class LLMClientFactory:
    """LLM 客户端工厂"""
    
    # 默认使用 litellm
    DEFAULT_CLIENT_TYPE = "litellm"
    
    @staticmethod
    def create_client(model_config, client_type="langchain"):
        """
        创建 LLM 客户端
        
        Args:
            model_config: 模型配置
            client_type: 客户端类型，可选 "litellm" 或 "langchain"
        """
        if client_type is None:
            client_type = LLMClientFactory.DEFAULT_CLIENT_TYPE
        
        if client_type == "langchain":
            return LangChainClient(model_config)
        else:
            return LiteLLMClient(model_config)
    
    @staticmethod
    def set_default_client(client_type):
        """设置默认客户端类型"""
        if client_type in ["litellm", "langchain"]:
            LLMClientFactory.DEFAULT_CLIENT_TYPE = client_type


class LLMClient:
    """大模型客户端 - 使用工厂模式"""
    
    def __init__(self, client_type=None):
        self.config_manager = ConfigManager()
        self.client_type = client_type
    
    def _get_client(self):
        """获取当前模型的客户端"""
        model_config = self.config_manager.get_current_model_config()
        if not model_config:
            raise ValueError("未配置模型，请先在模型配置页面添加模型")
        return LLMClientFactory.create_client(model_config, self.client_type)
    
    def chat(self, messages, stream=False):
        """调用大模型 API"""
        client = self._get_client()
        return client.chat(messages, stream)
    
    def chat_with_history(self, user_message, history=None):
        """带历史记录的对话"""
        if history is None:
            history = []
        
        messages = history.copy()
        messages.append({"role": "user", "content": user_message})
        
        return self.chat(messages)
