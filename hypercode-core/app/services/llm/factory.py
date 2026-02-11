
import os
from typing import Optional
from .base import LLMProvider
from .ollama import OllamaProvider
from .openai import OpenAIProvider

class LLMFactory:
    _instance: Optional[LLMProvider] = None
    
    @classmethod
    def create_provider(cls, name: str) -> LLMProvider:
        name = name.lower()
        if name == "ollama":
            url = os.getenv("OLLAMA_URL", "http://llama:11434")
            model = os.getenv("OLLAMA_MODEL", "tinyllama")
            return OllamaProvider(url, model)
        elif name == "openai":
            key = os.getenv("OPENAI_API_KEY", "")
            model = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
            return OpenAIProvider(key, model)
        else:
            raise ValueError(f"Unknown LLM provider: {name}")

    @classmethod
    def get_provider(cls) -> LLMProvider:
        if cls._instance:
            return cls._instance
            
        provider_name = os.getenv("LLM_PROVIDER", "ollama")
        cls._instance = cls.create_provider(provider_name)
        return cls._instance
    
    @classmethod
    def get_default_provider(cls) -> LLMProvider:
        return cls.get_provider()
