
import logging
from openai import AsyncOpenAI
from app.core.config import get_settings
from app.core.db import db

settings = get_settings()
logger = logging.getLogger(__name__)

PRICING = {
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    # Default fallback
    "default": {"input": 1.00, "output": 1.00}
}

class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        price = PRICING.get(model, PRICING["default"])
        cost = (prompt_tokens / 1_000_000 * price["input"]) + \
               (completion_tokens / 1_000_000 * price["output"])
        return round(cost, 6)

    async def generate_response(
        self, 
        messages: list[dict], 
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        mission_id: str = None
    ) -> str:
        """
        Generate a response from OpenAI based on a list of messages.
        Handles basic error logging and cost tracking.
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
            
            # Track Usage
            if response.usage:
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
                total_tokens = response.usage.total_tokens
                cost = self._calculate_cost(model, prompt_tokens, completion_tokens)
                
                logger.info(f"LLM Usage: {total_tokens} tokens (${cost})")
                
                try:
                    await db.tokenusage.create(data={
                        "missionId": mission_id,
                        "model": model,
                        "promptTokens": prompt_tokens,
                        "completionTokens": completion_tokens,
                        "totalTokens": total_tokens,
                        "cost": cost
                    })
                except Exception as db_err:
                    logger.error(f"Failed to save token usage: {db_err}")

            logger.info("Received response from OpenAI")
            return content
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise

llm_service = LLMService()

