
import logging
from openai import AsyncOpenAI
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def generate_response(
        self, 
        messages: list[dict], 
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        Generate a response from OpenAI based on a list of messages.
        Handles basic error logging.
        """
        try:
            logger.info(f"Sending request to OpenAI model {model}")
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            content = response.choices[0].message.content
            logger.info("Received response from OpenAI")
            return content
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise

llm_service = LLMService()
