
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> Optional[str]:
        """Generate text from prompt"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check provider health"""
        pass

    @abstractmethod
    async def get_embedding(self, text: str) -> List[float]:
        """Generate vector embedding for text"""
        pass
