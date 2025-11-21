"""Tests for LLM client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ai_code_review.ai.llm_client import OpenAIClient, AnthropicClient, get_llm_client


class TestOpenAIClient:
    """Tests for OpenAI client."""

    @patch("ai_code_review.ai.llm_client.openai.AsyncOpenAI")
    @patch("ai_code_review.ai.llm_client.get_settings")
    def test_initialization(self, mock_settings, mock_openai):
        """Test OpenAI client initialization."""
        mock_settings.return_value.openai_api_key = "test-key"
        mock_settings.return_value.ai_model = "gpt-4"
        mock_settings.return_value.ai_temperature = 0.3
        mock_settings.return_value.ai_max_tokens = 4096

        client = OpenAIClient()

        assert client.model == "gpt-4"
        assert client.temperature == 0.3
        assert client.max_tokens == 4096

    @pytest.mark.asyncio
    @patch("ai_code_review.ai.llm_client.openai.AsyncOpenAI")
    @patch("ai_code_review.ai.llm_client.get_settings")
    async def test_generate_completion(self, mock_settings, mock_openai):
        """Test generating a completion."""
        mock_settings.return_value.openai_api_key = "test-key"
        mock_settings.return_value.ai_model = "gpt-4"
        mock_settings.return_value.ai_temperature = 0.3
        mock_settings.return_value.ai_max_tokens = 4096

        # Mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage.total_tokens = 100

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        client = OpenAIClient()
        result = await client.generate_completion("Test prompt", "System prompt")

        assert result == "Test response"
        mock_client.chat.completions.create.assert_called_once()


class TestAnthropicClient:
    """Tests for Anthropic client."""

    @patch("ai_code_review.ai.llm_client.anthropic.AsyncAnthropic")
    @patch("ai_code_review.ai.llm_client.get_settings")
    def test_initialization(self, mock_settings, mock_anthropic):
        """Test Anthropic client initialization."""
        mock_settings.return_value.anthropic_api_key = "test-key"
        mock_settings.return_value.ai_model = "claude-3-opus"
        mock_settings.return_value.ai_temperature = 0.3
        mock_settings.return_value.ai_max_tokens = 4096

        client = AnthropicClient()

        assert client.model == "claude-3-opus"
        assert client.temperature == 0.3
        assert client.max_tokens == 4096

    @pytest.mark.asyncio
    @patch("ai_code_review.ai.llm_client.anthropic.AsyncAnthropic")
    @patch("ai_code_review.ai.llm_client.get_settings")
    async def test_generate_completion(self, mock_settings, mock_anthropic):
        """Test generating a completion."""
        mock_settings.return_value.anthropic_api_key = "test-key"
        mock_settings.return_value.ai_model = "claude-3-opus"
        mock_settings.return_value.ai_temperature = 0.3
        mock_settings.return_value.ai_max_tokens = 4096

        # Mock response
        mock_content = MagicMock()
        mock_content.text = "Test response"
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_response.usage.input_tokens = 50
        mock_response.usage.output_tokens = 50

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        client = AnthropicClient()
        result = await client.generate_completion("Test prompt", "System prompt")

        assert result == "Test response"
        mock_client.messages.create.assert_called_once()


class TestGetLLMClient:
    """Tests for get_llm_client function."""

    @patch("ai_code_review.ai.llm_client.get_settings")
    def test_get_openai_client(self, mock_settings):
        """Test getting OpenAI client."""
        mock_settings.return_value.ai_provider = "openai"
        mock_settings.return_value.openai_api_key = "test-key"
        mock_settings.return_value.ai_model = "gpt-4"
        mock_settings.return_value.ai_temperature = 0.3
        mock_settings.return_value.ai_max_tokens = 4096

        with patch("ai_code_review.ai.llm_client.openai.AsyncOpenAI"):
            client = get_llm_client()
            assert isinstance(client, OpenAIClient)

    @patch("ai_code_review.ai.llm_client.get_settings")
    def test_get_anthropic_client(self, mock_settings):
        """Test getting Anthropic client."""
        mock_settings.return_value.ai_provider = "anthropic"
        mock_settings.return_value.anthropic_api_key = "test-key"
        mock_settings.return_value.ai_model = "claude-3-opus"
        mock_settings.return_value.ai_temperature = 0.3
        mock_settings.return_value.ai_max_tokens = 4096

        with patch("ai_code_review.ai.llm_client.anthropic.AsyncAnthropic"):
            client = get_llm_client()
            assert isinstance(client, AnthropicClient)

    @patch("ai_code_review.ai.llm_client.get_settings")
    def test_unsupported_provider(self, mock_settings):
        """Test unsupported provider raises error."""
        mock_settings.return_value.ai_provider = "unsupported"

        with pytest.raises(ValueError, match="Unsupported AI provider"):
            get_llm_client()
