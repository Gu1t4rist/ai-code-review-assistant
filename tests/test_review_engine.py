"""Tests for code review engine."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ai_code_review.ai.review_engine import CodeReviewEngine
from ai_code_review.gitlab.models import (
    DiffChange,
    IssueCategory,
    IssueSeverity,
    MergeRequestInfo,
    ReviewRecommendation,
)


class TestCodeReviewEngine:
    """Tests for CodeReviewEngine class."""

    @pytest.fixture
    def engine(self):
        """Create a review engine instance."""
        with patch("ai_code_review.ai.review_engine.get_llm_client"):
            return CodeReviewEngine()

    def test_filter_changes(self, engine: CodeReviewEngine):
        """Test filtering changes."""
        changes = [
            DiffChange(
                file_path="src/main.py",
                diff="test diff",
                new_file=False,
                deleted_file=False,
                renamed_file=False,
                additions=10,
                deletions=5,
            ),
            DiffChange(
                file_path="package-lock.json",
                diff="test diff",
                new_file=False,
                deleted_file=False,
                renamed_file=False,
                additions=100,
                deletions=50,
            ),
            DiffChange(
                file_path="deleted.py",
                diff="test diff",
                new_file=False,
                deleted_file=True,
                renamed_file=False,
                additions=0,
                deletions=10,
            ),
        ]

        filtered = engine._filter_changes(changes)

        assert len(filtered) == 1
        assert filtered[0].file_path == "src/main.py"

    def test_is_ignored_file(self, engine: CodeReviewEngine):
        """Test ignored file detection."""
        assert engine._is_ignored_file("package-lock.json") is True
        assert engine._is_ignored_file("dist/bundle.js") is True
        assert engine._is_ignored_file("src/main.py") is False
        assert engine._is_ignored_file("README.md") is False

    def test_is_code_file(self, engine: CodeReviewEngine):
        """Test code file detection."""
        assert engine._is_code_file("src/main.py") is True
        assert engine._is_code_file("app.js") is True
        assert engine._is_code_file("README.md") is False
        assert engine._is_code_file("config.json") is False

    def test_is_test_file(self, engine: CodeReviewEngine):
        """Test test file detection."""
        assert engine._is_test_file("test_main.py") is True
        assert engine._is_test_file("tests/test_app.py") is True
        assert engine._is_test_file("app.test.js") is True
        assert engine._is_test_file("src/main.py") is False

    def test_rule_based_recommendation(self, engine: CodeReviewEngine):
        """Test rule-based recommendation logic."""
        # No issues
        assert engine._rule_based_recommendation([]) == ReviewRecommendation.APPROVE

        # Critical issue
        critical_issue = MagicMock()
        critical_issue.severity = IssueSeverity.CRITICAL
        assert engine._rule_based_recommendation([critical_issue]) == ReviewRecommendation.REJECT

        # Multiple high issues
        high_issue = MagicMock()
        high_issue.severity = IssueSeverity.HIGH
        assert engine._rule_based_recommendation([high_issue] * 4) == ReviewRecommendation.NEEDS_FIXES

        # Few low issues
        low_issue = MagicMock()
        low_issue.severity = IssueSeverity.LOW
        assert engine._rule_based_recommendation([low_issue] * 3) == ReviewRecommendation.APPROVE

    @pytest.mark.asyncio
    async def test_review_file_change(self, engine: CodeReviewEngine, sample_diff_change: DiffChange, sample_mr_info: MergeRequestInfo):
        """Test reviewing a single file change."""
        # Mock LLM response
        mock_response = {
            "issues": [
                {
                    "severity": "medium",
                    "category": "code_quality",
                    "title": "Test issue",
                    "description": "Test description",
                    "line_number": 5,
                    "suggestion": "Fix this",
                }
            ],
            "positive_points": ["Good code"],
            "assessment": "Looks good",
        }

        engine.llm_client.generate_structured_output = AsyncMock(return_value=mock_response)

        result = await engine._review_file_change(sample_diff_change, sample_mr_info)

        assert result["file_path"] == "src/example.py"
        assert len(result["issues"]) == 1
        assert result["issues"][0].title == "Test issue"
        assert "Good code" in result["positive_points"]

    def test_create_empty_summary(self, engine: CodeReviewEngine, sample_mr_info: MergeRequestInfo):
        """Test creating an empty summary."""
        summary = engine._create_empty_summary(sample_mr_info)

        assert summary.recommendation == ReviewRecommendation.APPROVE
        assert summary.total_files == len(sample_mr_info.changes)
        assert len(summary.issues) == 0
        assert "No reviewable code changes" in summary.overall_comment
