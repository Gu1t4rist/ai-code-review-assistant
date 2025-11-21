"""GitLab integration models."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MergeRequestState(str, Enum):
    """Merge request states."""

    OPENED = "opened"
    CLOSED = "closed"
    MERGED = "merged"
    LOCKED = "locked"


class ReviewRecommendation(str, Enum):
    """Review recommendation types."""

    APPROVE = "approve"
    NEEDS_FIXES = "needs_fixes"
    REJECT = "reject"


class IssueSeverity(str, Enum):
    """Issue severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueCategory(str, Enum):
    """Issue category types."""

    SECURITY = "security"
    PERFORMANCE = "performance"
    CODE_QUALITY = "code_quality"
    STYLE = "style"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    ARCHITECTURE = "architecture"
    BUG = "bug"


class DiffChange(BaseModel):
    """Represents a single file change in a diff."""

    file_path: str
    old_path: str | None = None
    new_file: bool = False
    deleted_file: bool = False
    renamed_file: bool = False
    diff: str
    additions: int = 0
    deletions: int = 0


class MergeRequestInfo(BaseModel):
    """Merge request information."""

    id: int
    iid: int
    project_id: int
    title: str
    description: str | None = None
    state: MergeRequestState
    source_branch: str
    target_branch: str
    author: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    web_url: str
    changes: list[DiffChange] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    has_conflicts: bool = False


class ReviewIssue(BaseModel):
    """Represents a code review issue."""

    severity: IssueSeverity
    category: IssueCategory
    file_path: str
    line_number: int | None = None
    title: str
    description: str
    suggestion: str | None = None
    code_snippet: str | None = None
    references: list[str] = Field(default_factory=list)


class ReviewSummary(BaseModel):
    """Summary of the code review."""

    recommendation: ReviewRecommendation
    total_files: int
    total_additions: int
    total_deletions: int
    issues: list[ReviewIssue]
    positive_points: list[str] = Field(default_factory=list)
    key_concerns: list[str] = Field(default_factory=list)
    test_coverage: float | None = None
    overall_comment: str

    @property
    def critical_issues(self) -> list[ReviewIssue]:
        """Get critical severity issues."""
        return [issue for issue in self.issues if issue.severity == IssueSeverity.CRITICAL]

    @property
    def high_issues(self) -> list[ReviewIssue]:
        """Get high severity issues."""
        return [issue for issue in self.issues if issue.severity == IssueSeverity.HIGH]

    @property
    def medium_issues(self) -> list[ReviewIssue]:
        """Get medium severity issues."""
        return [issue for issue in self.issues if issue.severity == IssueSeverity.MEDIUM]

    @property
    def low_issues(self) -> list[ReviewIssue]:
        """Get low severity issues."""
        return [issue for issue in self.issues if issue.severity == IssueSeverity.LOW]

    @property
    def issues_by_category(self) -> dict[IssueCategory, list[ReviewIssue]]:
        """Group issues by category."""
        result: dict[IssueCategory, list[ReviewIssue]] = {}
        for issue in self.issues:
            if issue.category not in result:
                result[issue.category] = []
            result[issue.category].append(issue)
        return result


class WebhookEvent(BaseModel):
    """GitLab webhook event."""

    object_kind: str
    event_type: str | None = None
    project: dict[str, Any]
    object_attributes: dict[str, Any]
    user: dict[str, Any] | None = None


class MergeRequestLabel(str, Enum):
    """Predefined MR labels for AI review."""

    APPROVED = "ai-review:approved"
    NEEDS_FIXES = "ai-review:needs-fixes"
    REJECTED = "ai-review:rejected"
    IN_PROGRESS = "ai-review:in-progress"
    SECURITY_RISK = "ai-review:security-risk"
    PERFORMANCE_ISSUES = "ai-review:performance-issues"
    READY_FOR_MERGE = "ready-for-merge"
    NEEDS_REVIEW = "needs-review"
    CHANGES_REQUESTED = "changes-requested"
