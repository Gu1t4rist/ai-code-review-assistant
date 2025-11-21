"""GitLab integration package."""

from ai_code_review.gitlab.client import GitLabClient
from ai_code_review.gitlab.models import (
    IssueCategory,
    IssueSeverity,
    MergeRequestInfo,
    MergeRequestLabel,
    ReviewIssue,
    ReviewRecommendation,
    ReviewSummary,
)

__all__ = [
    "GitLabClient",
    "MergeRequestInfo",
    "ReviewIssue",
    "ReviewSummary",
    "ReviewRecommendation",
    "IssueSeverity",
    "IssueCategory",
    "MergeRequestLabel",
]
