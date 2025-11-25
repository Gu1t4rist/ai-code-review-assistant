"""Simple tests for review engine."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ai_code_review.ai.review_engine import CodeReviewEngine
from ai_code_review.gitlab.models import DiffChange


class TestCodeReviewEngine:
    """Basic review engine tests."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM client."""
        mock = AsyncMock()
        mock.generate_structured_output = AsyncMock(
            return_value={
                "issues": [],
                "positive_points": ["Good code"],
                "assessment": "Looks good",
            }
        )
        return mock

    @pytest.fixture
    def engine(self, mock_llm):
        """Create review engine with mock."""
        with patch("ai_code_review.ai.review_engine.get_llm_client", return_value=mock_llm):
            return CodeReviewEngine()

    def test_filter_deleted_files(self, engine):
        """Test that deleted files are filtered."""
        changes = [
            DiffChange(
                file_path="deleted.py",
                diff="",
                new_file=False,
                deleted_file=True,
                renamed_file=False,
                additions=0,
                deletions=10,
            ),
            DiffChange(
                file_path="active.py",
                diff="test",
                new_file=False,
                deleted_file=False,
                renamed_file=False,
                additions=5,
                deletions=2,
            ),
        ]
        
        filtered = engine._filter_changes(changes)
        
        assert len(filtered) == 1
        assert filtered[0].file_path == "active.py"

    def test_ignore_patterns(self, engine):
        """Test file ignore patterns."""
        assert engine._is_ignored_file("package-lock.json") is True
        assert engine._is_ignored_file("yarn.lock") is True
        assert engine._is_ignored_file("dist/bundle.min.js") is True
        assert engine._is_ignored_file("src/main.py") is False

    @pytest.mark.asyncio
    async def test_review_file(self, engine, mock_llm):
        """Test reviewing a single file."""
        change = DiffChange(
            file_path="test.py",
            diff="@@ -1,2 +1,3 @@\n+new line",
            new_file=False,
            deleted_file=False,
            renamed_file=False,
            additions=1,
            deletions=0,
        )
        
        mr_info = MagicMock(description="Test MR")
        result = await engine._review_file_change(change, mr_info)
        
        assert result["file_path"] == "test.py"
        assert "issues" in result
        mock_llm.generate_structured_output.assert_called_once()
