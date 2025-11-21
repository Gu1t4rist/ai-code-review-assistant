"""GitLab API client for interacting with GitLab."""

from typing import Any

import httpx

from ai_code_review.config import get_settings
from ai_code_review.gitlab.models import (
    DiffChange,
    MergeRequestInfo,
    MergeRequestLabel,
    MergeRequestState,
    ReviewIssue,
    ReviewSummary,
)
from ai_code_review.utils.logger import get_logger

logger = get_logger(__name__)


class GitLabClient:
    """Async client for GitLab API operations."""

    def __init__(self) -> None:
        """Initialize GitLab client."""
        settings = get_settings()
        self.base_url = settings.gitlab_url.rstrip("/")
        self.token = settings.gitlab_token
        self.verify_ssl = settings.webhook_verify_ssl
        
        # Create async client with connection pooling
        self.client = httpx.AsyncClient(
            base_url=f"{self.base_url}/api/v4",
            headers={
                "PRIVATE-TOKEN": self.token,
                "Content-Type": "application/json",
            },
            verify=self.verify_ssl,
            timeout=30.0,
        )
        logger.info("gitlab_client_initialized", url=self.base_url)
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def get_project(self, project_id: int) -> dict[str, Any]:
        """Get a GitLab project by ID."""
        logger.debug("fetching_project", project_id=project_id)
        response = await self.client.get(f"/projects/{project_id}")
        response.raise_for_status()
        project = response.json()
        logger.info("project_fetched", project_id=project_id, project_name=project.get("name"))
        return project

    async def get_merge_request(self, project_id: int, mr_iid: int) -> dict[str, Any]:
        """Get a merge request by project ID and MR IID."""
        logger.debug("fetching_merge_request", project_id=project_id, mr_iid=mr_iid)
        response = await self.client.get(f"/projects/{project_id}/merge_requests/{mr_iid}")
        response.raise_for_status()
        mr = response.json()
        logger.info(
            "merge_request_fetched",
            project_id=project_id,
            mr_iid=mr_iid,
            mr_title=mr.get("title"),
        )
        return mr

    async def get_merge_request_changes(self, project_id: int, mr_iid: int) -> dict[str, Any]:
        """Get merge request changes (diffs)."""
        logger.debug("fetching_mr_changes", project_id=project_id, mr_iid=mr_iid)
        response = await self.client.get(f"/projects/{project_id}/merge_requests/{mr_iid}/changes")
        response.raise_for_status()
        return response.json()

    async def get_merge_request_info(self, project_id: int, mr_iid: int) -> MergeRequestInfo:
        """Get detailed merge request information including changes."""
        logger.info("getting_mr_info", project_id=project_id, mr_iid=mr_iid)
        
        # Fetch MR data and changes in parallel
        import asyncio
        mr, changes_data = await asyncio.gather(
            self.get_merge_request(project_id, mr_iid),
            self.get_merge_request_changes(project_id, mr_iid),
        )

        # Parse changes
        changes = self._parse_changes(changes_data)

        return MergeRequestInfo(
            id=mr["id"],
            iid=mr["iid"],
            project_id=project_id,
            title=mr["title"],
            description=mr.get("description", ""),
            state=MergeRequestState(mr["state"]),
            source_branch=mr["source_branch"],
            target_branch=mr["target_branch"],
            author=mr["author"],
            created_at=mr["created_at"],
            updated_at=mr["updated_at"],
            web_url=mr["web_url"],
            changes=changes,
            labels=mr.get("labels", []),
            has_conflicts=mr.get("has_conflicts", False),
        )

    def _parse_changes(self, changes_data: dict[str, Any]) -> list[DiffChange]:
        """Parse changes from GitLab API response."""
        changes = []
        for change in changes_data.get("changes", []):
            diff_change = DiffChange(
                file_path=change.get("new_path", change.get("old_path", "")),
                old_path=change.get("old_path"),
                new_file=change.get("new_file", False),
                deleted_file=change.get("deleted_file", False),
                renamed_file=change.get("renamed_file", False),
                diff=change.get("diff", ""),
            )

            # Count additions and deletions
            diff_lines = diff_change.diff.split("\n")
            diff_change.additions = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
            diff_change.deletions = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))

            changes.append(diff_change)

        logger.debug("parsed_changes", total_files=len(changes))
        return changes

    async def post_comment(
        self,
        project_id: int,
        mr_iid: int,
        comment: str,
        file_path: str | None = None,
        line_number: int | None = None,
    ) -> None:
        """Post a comment on a merge request."""
        logger.info(
            "posting_comment",
            project_id=project_id,
            mr_iid=mr_iid,
            has_line_ref=bool(file_path and line_number),
        )

        if file_path and line_number:
            # Try to post inline comment
            try:
                mr = await self.get_merge_request(project_id, mr_iid)
                diff_refs = mr.get("diff_refs", {})
                
                if diff_refs:
                    # Create discussion with position
                    payload = {
                        "body": comment,
                        "position": {
                            "position_type": "text",
                            "new_path": file_path,
                            "new_line": line_number,
                            "base_sha": diff_refs.get("base_sha"),
                            "start_sha": diff_refs.get("start_sha"),
                            "head_sha": diff_refs.get("head_sha"),
                        },
                    }
                    response = await self.client.post(
                        f"/projects/{project_id}/merge_requests/{mr_iid}/discussions",
                        json=payload,
                    )
                    response.raise_for_status()
                    logger.info("inline_comment_posted")
                    return
            except Exception as e:
                logger.warning("failed_to_post_inline_comment", error=str(e))
                # Fallback to regular comment with file reference
                comment = f"**File: {file_path}:{line_number}**\n\n{comment}"

        # Post general comment (note)
        payload = {"body": comment}
        response = await self.client.post(
            f"/projects/{project_id}/merge_requests/{mr_iid}/notes",
            json=payload,
        )
        response.raise_for_status()
        logger.info("general_comment_posted")

    async def add_labels(self, project_id: int, mr_iid: int, labels: list[str]) -> None:
        """Add labels to a merge request."""
        logger.info("adding_labels", project_id=project_id, mr_iid=mr_iid, labels=labels)
        
        # Get current MR to fetch existing labels
        mr = await self.get_merge_request(project_id, mr_iid)
        current_labels = set(mr.get("labels", []))
        new_labels = list(current_labels.union(set(labels)))

        # Update MR with new labels
        payload = {"labels": ",".join(new_labels)}
        response = await self.client.put(
            f"/projects/{project_id}/merge_requests/{mr_iid}",
            json=payload,
        )
        response.raise_for_status()
        logger.info("labels_added", total_labels=len(new_labels))

    async def remove_labels(self, project_id: int, mr_iid: int, labels: list[str]) -> None:
        """Remove labels from a merge request."""
        logger.info("removing_labels", project_id=project_id, mr_iid=mr_iid, labels=labels)
        
        # Get current MR to fetch existing labels
        mr = await self.get_merge_request(project_id, mr_iid)
        current_labels = set(mr.get("labels", []))
        new_labels = list(current_labels - set(labels))

        # Update MR with remaining labels
        payload = {"labels": ",".join(new_labels)}
        response = await self.client.put(
            f"/projects/{project_id}/merge_requests/{mr_iid}",
            json=payload,
        )
        response.raise_for_status()
        logger.info("labels_removed", remaining_labels=len(new_labels))

    async def update_labels_for_review(self, project_id: int, mr_iid: int, summary: ReviewSummary) -> None:
        """Update MR labels based on review summary."""
        logger.info("updating_review_labels", project_id=project_id, mr_iid=mr_iid)

        # Remove all AI review labels
        all_review_labels = [label.value for label in MergeRequestLabel]
        await self.remove_labels(project_id, mr_iid, all_review_labels)

        # Add labels based on recommendation
        labels_to_add = []

        if summary.recommendation == "approve":
            labels_to_add.extend([MergeRequestLabel.APPROVED.value, MergeRequestLabel.READY_FOR_MERGE.value])
        elif summary.recommendation == "needs_fixes":
            labels_to_add.extend([MergeRequestLabel.NEEDS_FIXES.value, MergeRequestLabel.CHANGES_REQUESTED.value])
        elif summary.recommendation == "reject":
            labels_to_add.extend([MergeRequestLabel.REJECTED.value, MergeRequestLabel.CHANGES_REQUESTED.value])

        # Add category-specific labels
        if any(issue.category.value == "security" for issue in summary.issues):
            labels_to_add.append(MergeRequestLabel.SECURITY_RISK.value)

        if any(issue.category.value == "performance" for issue in summary.issues):
            labels_to_add.append(MergeRequestLabel.PERFORMANCE_ISSUES.value)

        if labels_to_add:
            await self.add_labels(project_id, mr_iid, labels_to_add)

        logger.info("review_labels_updated", labels=labels_to_add)

    async def post_review_summary(self, project_id: int, mr_iid: int, summary: ReviewSummary) -> None:
        """Post a comprehensive review summary as a comment."""
        logger.info("posting_review_summary", project_id=project_id, mr_iid=mr_iid)

        # Format summary comment
        comment = self._format_summary_comment(summary)

        # Post the summary
        await self.post_comment(project_id, mr_iid, comment)

        # Update labels
        await self.update_labels_for_review(project_id, mr_iid, summary)

        logger.info("review_summary_posted")

    def _format_summary_comment(self, summary: ReviewSummary) -> str:
        """Format review summary as a markdown comment."""
        # Recommendation emoji
        rec_emoji = {
            "approve": "✅",
            "needs_fixes": "⚠️",
            "reject": "❌",
        }

        emoji = rec_emoji.get(summary.recommendation.value, "📊")

        lines = [
            "## 📊 AI Code Review Summary",
            "",
            f"**Overall Recommendation**: {emoji} {summary.recommendation.value.replace('_', ' ').title()}",
            "",
            "### Statistics",
            f"- Files changed: {summary.total_files}",
            f"- Lines added: {summary.total_additions}",
            f"- Lines removed: {summary.total_deletions}",
            f"- Comments posted: {len(summary.issues)}",
        ]

        if summary.test_coverage is not None:
            lines.append(f"- Test coverage: {summary.test_coverage:.1f}%")

        # Issues by severity
        lines.extend(
            [
                "",
                "### Issues Found",
                f"- 🔴 Critical: {len(summary.critical_issues)}",
                f"- 🟠 High: {len(summary.high_issues)}",
                f"- 🟡 Medium: {len(summary.medium_issues)}",
                f"- 🟢 Low: {len(summary.low_issues)}",
            ]
        )

        # Key concerns
        if summary.key_concerns:
            lines.extend(["", "### Key Concerns"])
            for i, concern in enumerate(summary.key_concerns, 1):
                lines.append(f"{i}. {concern}")

        # Positive points
        if summary.positive_points:
            lines.extend(["", "### Positive Points"])
            for point in summary.positive_points:
                lines.append(f"✅ {point}")

        # Overall comment
        lines.extend(["", "### Overall Assessment", summary.overall_comment])

        return "\n".join(lines)

    async def post_issue_comment(self, project_id: int, mr_iid: int, issue: ReviewIssue) -> None:
        """Post a comment for a specific review issue."""
        logger.debug(
            "posting_issue_comment",
            project_id=project_id,
            mr_iid=mr_iid,
            severity=issue.severity,
            category=issue.category,
        )

        # Format issue comment
        comment = self._format_issue_comment(issue)

        # Post the comment
        await self.post_comment(project_id, mr_iid, comment, issue.file_path, issue.line_number)

    def _format_issue_comment(self, issue: ReviewIssue) -> str:
        """Format a review issue as a markdown comment."""
        severity_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢",
            "info": "ℹ️",
        }

        lines = [
            "🤖 **AI Code Review**",
            "",
            f"**Severity**: {severity_emoji.get(issue.severity.value, '❓')} {issue.severity.value.title()}",
            f"**Category**: {issue.category.value.replace('_', ' ').title()}",
            "",
            f"### {issue.title}",
            "",
            issue.description,
        ]

        if issue.suggestion:
            lines.extend(["", "**Recommendation**:", issue.suggestion])

        if issue.code_snippet:
            lines.extend(["", "```python", issue.code_snippet, "```"])

        if issue.references:
            lines.extend(["", "**References**:"])
            for ref in issue.references:
                lines.append(f"- {ref}")

        return "\n".join(lines)
