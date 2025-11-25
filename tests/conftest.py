"""Test configuration and fixtures."""

import os

# Set ALL required test environment variables FIRST before any imports
os.environ.setdefault("GITLAB_URL", "https://gitlab.test.com")
os.environ.setdefault("GITLAB_TOKEN", "test-token-123")
os.environ.setdefault("GITLAB_WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("AI_PROVIDER", "anthropic")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-123")
os.environ.setdefault("AI_MODEL", "claude-3-5-sonnet-20241022")
os.environ.setdefault("AI_TEMPERATURE", "0.3")
os.environ.setdefault("AI_MAX_TOKENS", "4000")

import pytest
from unittest.mock import MagicMock

from ai_code_review.gitlab.models import (
    DiffChange,
    IssueCategory,
    IssueSeverity,
    MergeRequestInfo,
    MergeRequestState,
    ReviewIssue,
)


@pytest.fixture
def sample_diff_change() -> DiffChange:
    """Create a sample diff change for testing."""
    return DiffChange(
        file_path="src/example.py",
        old_path=None,
        new_file=False,
        deleted_file=False,
        renamed_file=False,
        diff="""@@ -1,5 +1,7 @@
 def calculate_total(items):
-    total = 0
-    for item in items:
-        total += item.price
-    return total
+    # Calculate total price
+    return sum(item.price for item in items)
+
+def validate_items(items):
+    return all(item.price > 0 for item in items)
""",
        additions=5,
        deletions=3,
    )


@pytest.fixture
def sample_mr_info(sample_diff_change: DiffChange) -> MergeRequestInfo:
    """Create a sample merge request info for testing."""
    return MergeRequestInfo(
        id=123,
        iid=45,
        project_id=1,
        title="Add item validation",
        description="This MR adds validation for items to ensure prices are positive",
        state=MergeRequestState.OPENED,
        source_branch="feature/item-validation",
        target_branch="main",
        author={"name": "John Doe", "username": "johndoe"},
        created_at="2024-01-01T10:00:00Z",
        updated_at="2024-01-01T11:00:00Z",
        web_url="https://gitlab.example.com/project/repo/-/merge_requests/45",
        changes=[sample_diff_change],
        labels=[],
        has_conflicts=False,
    )


@pytest.fixture
def sample_review_issue() -> ReviewIssue:
    """Create a sample review issue for testing."""
    return ReviewIssue(
        severity=IssueSeverity.MEDIUM,
        category=IssueCategory.CODE_QUALITY,
        file_path="src/example.py",
        line_number=5,
        title="Consider error handling",
        description="The function doesn't handle the case when items is empty or None",
        suggestion="Add input validation: if not items: return 0",
        code_snippet="if not items:\\n    return 0",
        references=["https://docs.python.org/3/tutorial/errors.html"],
    )


@pytest.fixture
def mock_gitlab_client():
    """Create a mock GitLab client."""
    return MagicMock()


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    mock = MagicMock()
    mock.generate_completion = MagicMock(return_value="Test completion")
    mock.generate_structured_output = MagicMock(
        return_value={
            "issues": [],
            "positive_points": ["Good code quality"],
            "assessment": "Looks good",
        }
    )
    return mock
