"""Tests for GitLab client."""

import pytest
from unittest.mock import MagicMock, patch

from ai_code_review.gitlab.client import GitLabClient
from ai_code_review.gitlab.models import (
    IssueCategory,
    IssueSeverity,
    MergeRequestLabel,
    ReviewIssue,
    ReviewRecommendation,
    ReviewSummary,
)


class TestGitLabClient:
    """Tests for GitLabClient class."""

    @patch("ai_code_review.gitlab.client.gitlab.Gitlab")
    def test_initialization(self, mock_gitlab):
        """Test client initialization."""
        client = GitLabClient()
        assert client.gl is not None
        mock_gitlab.assert_called_once()

    @patch("ai_code_review.gitlab.client.gitlab.Gitlab")
    def test_get_project(self, mock_gitlab):
        """Test getting a project."""
        mock_gl = MagicMock()
        mock_project = MagicMock()
        mock_project.name = "Test Project"
        mock_gl.projects.get.return_value = mock_project
        mock_gitlab.return_value = mock_gl

        client = GitLabClient()
        project = client.get_project(123)

        assert project.name == "Test Project"
        mock_gl.projects.get.assert_called_once_with(123)

    @patch("ai_code_review.gitlab.client.gitlab.Gitlab")
    def test_post_comment(self, mock_gitlab):
        """Test posting a comment."""
        mock_gl = MagicMock()
        mock_project = MagicMock()
        mock_mr = MagicMock()
        mock_gl.projects.get.return_value = mock_project
        mock_project.mergerequests.get.return_value = mock_mr
        mock_gitlab.return_value = mock_gl

        client = GitLabClient()
        client.post_comment(123, 45, "Test comment")

        mock_mr.notes.create.assert_called_once()

    @patch("ai_code_review.gitlab.client.gitlab.Gitlab")
    def test_add_labels(self, mock_gitlab):
        """Test adding labels to MR."""
        mock_gl = MagicMock()
        mock_project = MagicMock()
        mock_mr = MagicMock()
        mock_mr.labels = ["existing-label"]
        mock_gl.projects.get.return_value = mock_project
        mock_project.mergerequests.get.return_value = mock_mr
        mock_gitlab.return_value = mock_gl

        client = GitLabClient()
        client.add_labels(123, 45, ["new-label"])

        assert "new-label" in mock_mr.labels
        mock_mr.save.assert_called_once()

    @patch("ai_code_review.gitlab.client.gitlab.Gitlab")
    def test_format_issue_comment(self, mock_gitlab):
        """Test formatting an issue comment."""
        mock_gl = MagicMock()
        mock_gitlab.return_value = mock_gl

        client = GitLabClient()
        issue = ReviewIssue(
            severity=IssueSeverity.HIGH,
            category=IssueCategory.SECURITY,
            file_path="test.py",
            line_number=10,
            title="SQL Injection",
            description="Potential SQL injection vulnerability",
            suggestion="Use parameterized queries",
        )

        comment = client._format_issue_comment(issue)

        assert "SQL Injection" in comment
        assert "Security" in comment
        assert "High" in comment
        assert "Use parameterized queries" in comment

    @patch("ai_code_review.gitlab.client.gitlab.Gitlab")
    def test_format_summary_comment(self, mock_gitlab):
        """Test formatting a summary comment."""
        mock_gl = MagicMock()
        mock_gitlab.return_value = mock_gl

        client = GitLabClient()
        summary = ReviewSummary(
            recommendation=ReviewRecommendation.NEEDS_FIXES,
            total_files=5,
            total_additions=100,
            total_deletions=50,
            issues=[
                ReviewIssue(
                    severity=IssueSeverity.CRITICAL,
                    category=IssueCategory.SECURITY,
                    file_path="test.py",
                    title="Security issue",
                    description="Test",
                )
            ],
            positive_points=["Good test coverage"],
            key_concerns=["Security vulnerability found"],
            overall_comment="Please fix the security issue",
        )

        comment = client._format_summary_comment(summary)

        assert "AI Code Review Summary" in comment
        assert "Needs Fixes" in comment
        assert "Files changed: 5" in comment
        assert "Critical: 1" in comment
        assert "Good test coverage" in comment
