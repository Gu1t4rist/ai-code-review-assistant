"""Simple tests for LLM clients."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ai_code_review.ai.llm_client import OpenAIClient, AnthropicClient, get_llm_client


class TestOpenAIClient:
    """Basic OpenAI client tests."""

    @pytest.mark.asyncio
    async def test_generate_completion(self):
        """Test generating completion."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]
        mock_response.usage = MagicMock(total_tokens=100, prompt_tokens=80, completion_tokens=20)
        
        with patch("ai_code_review.ai.llm_client.openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client
            
            client = OpenAIClient()
            result = await client.generate_completion("Test prompt")
            
            assert result == "Test response"


class TestAnthropicClient:
    """Basic Anthropic client tests."""

    @pytest.mark.asyncio
    async def test_generate_completion(self):
        """Test generating completion."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Test response")]
        mock_response.usage = MagicMock(input_tokens=80, output_tokens=20)
        
        with patch("ai_code_review.ai.llm_client.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.return_value = mock_client
            
            client = AnthropicClient()
            result = await client.generate_completion("Test prompt")
            
            assert result == "Test response"

    @pytest.mark.asyncio
    async def test_structured_output(self):
        """Test structured output parsing."""
        test_data = {"issues": [], "assessment": "good"}
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(test_data))]
        mock_response.usage = MagicMock(input_tokens=80, output_tokens=20)
        
        with patch("ai_code_review.ai.llm_client.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.return_value = mock_client
            
            client = AnthropicClient()
            result = await client.generate_structured_output("Test")
            
            assert result == test_data


class TestClientFactory:
    """Test client factory."""

    @patch("ai_code_review.ai.llm_client.get_settings")
    def test_get_openai_client(self, mock_settings):
        """Test getting OpenAI client."""
        mock_settings.return_value.ai_provider = "openai"
        
        with patch("ai_code_review.ai.llm_client.OpenAIClient"):
            client = get_llm_client()
            assert client is not None

    @patch("ai_code_review.ai.llm_client.get_settings")
    def test_get_anthropic_client(self, mock_settings):
        """Test getting Anthropic client."""
        mock_settings.return_value.ai_provider = "anthropic"
        
        with patch("ai_code_review.ai.llm_client.AnthropicClient"):
            client = get_llm_client()
            assert client is not None
