"""LLM client for AI-powered code review."""

import json
import time
from abc import ABC, abstractmethod
from typing import Any

import anthropic
import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from ai_code_review.config import get_settings
from ai_code_review.utils.logger import get_logger
from ai_code_review.utils.metrics import (
    ai_api_calls_total,
    ai_api_duration_seconds,
    ai_tokens_used,
)

logger = get_logger(__name__)


class BaseLLMClient(ABC):
    """Base class for LLM clients."""

    @abstractmethod
    async def generate_completion(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate a completion from the LLM."""
        pass

    @abstractmethod
    async def generate_structured_output(
        self, prompt: str, system_prompt: str | None = None, response_schema: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Generate structured output from the LLM."""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI LLM client."""

    def __init__(self) -> None:
        """Initialize OpenAI client."""
        settings = get_settings()
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.ai_model
        self.temperature = settings.ai_temperature
        self.max_tokens = settings.ai_max_tokens
        logger.info("openai_client_initialized", model=self.model)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_completion(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate a completion from OpenAI."""
        logger.debug("generating_openai_completion")
        
        start_time = time.time()
        status = "success"

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = await self.client.chat.completions.create(
                model=self.model, messages=messages, temperature=self.temperature, max_tokens=self.max_tokens
            )

            content = response.choices[0].message.content or ""
            
            # Track token usage
            if response.usage:
                ai_tokens_used.labels(
                    provider="openai",
                    model=self.model,
                    token_type="input",
                ).inc(response.usage.prompt_tokens)
                
                ai_tokens_used.labels(
                    provider="openai",
                    model=self.model,
                    token_type="output",
                ).inc(response.usage.completion_tokens)
            
            logger.info("openai_completion_generated", tokens=response.usage.total_tokens if response.usage else 0)
            return content
        except Exception as e:
            status = "error"
            raise
        finally:
            duration = time.time() - start_time
            ai_api_calls_total.labels(
                provider="openai",
                model=self.model,
                status=status,
            ).inc()
            ai_api_duration_seconds.labels(
                provider="openai",
                model=self.model,
            ).observe(duration)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_structured_output(
        self, prompt: str, system_prompt: str | None = None, response_schema: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Generate structured output from OpenAI."""
        logger.debug("generating_openai_structured_output")

        # Add JSON format instruction to prompt
        full_prompt = prompt + "\n\nRespond with valid JSON only."

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": full_prompt})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or "{}"
        logger.info("openai_structured_output_generated", tokens=response.usage.total_tokens if response.usage else 0)

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error("failed_to_parse_json", error=str(e), content=content)
            return {}


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude LLM client."""

    def __init__(self) -> None:
        """Initialize Anthropic client."""
        settings = get_settings()
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.ai_model
        self.temperature = settings.ai_temperature
        self.max_tokens = settings.ai_max_tokens
        logger.info("anthropic_client_initialized", model=self.model)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_completion(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate a completion from Anthropic."""
        logger.debug("generating_anthropic_completion")
        
        start_time = time.time()
        status = "success"

        try:
            kwargs: dict[str, Any] = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "messages": [{"role": "user", "content": prompt}],
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            response = await self.client.messages.create(**kwargs)

            content = response.content[0].text if response.content else ""
            
            # Track token usage
            ai_tokens_used.labels(
                provider="anthropic",
                model=self.model,
                token_type="input",
            ).inc(response.usage.input_tokens)
            
            ai_tokens_used.labels(
                provider="anthropic",
                model=self.model,
                token_type="output",
            ).inc(response.usage.output_tokens)
            
            logger.info("anthropic_completion_generated", tokens=response.usage.input_tokens + response.usage.output_tokens)
            return content
        except Exception as e:
            status = "error"
            raise
        finally:
            duration = time.time() - start_time
            ai_api_calls_total.labels(
                provider="anthropic",
                model=self.model,
                status=status,
            ).inc()
            ai_api_duration_seconds.labels(
                provider="anthropic",
                model=self.model,
            ).observe(duration)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_structured_output(
        self, prompt: str, system_prompt: str | None = None, response_schema: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Generate structured output from Anthropic."""
        logger.debug("generating_anthropic_structured_output")

        # Add JSON format instruction
        full_prompt = prompt + "\n\nRespond with valid JSON only."

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": full_prompt}],
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        response = await self.client.messages.create(**kwargs)

        content = response.content[0].text if response.content else "{}"
        logger.info(
            "anthropic_structured_output_generated", tokens=response.usage.input_tokens + response.usage.output_tokens
        )

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error("failed_to_parse_json", error=str(e), content=content)
            return {}


def get_llm_client() -> BaseLLMClient:
    """Get the configured LLM client."""
    settings = get_settings()

    if settings.ai_provider == "openai":
        return OpenAIClient()
    elif settings.ai_provider == "anthropic":
        return AnthropicClient()
    elif settings.ai_provider == "azure":
        # Azure OpenAI uses the same client as OpenAI
        return OpenAIClient()
    else:
        raise ValueError(f"Unsupported AI provider: {settings.ai_provider}")
