"""Webhook handler for GitLab events."""

import hashlib
import hmac
from typing import Any

from fastapi import HTTPException, Request

from ai_code_review.ai.review_engine import CodeReviewEngine
from ai_code_review.config import get_settings
from ai_code_review.gitlab.client import GitLabClient
from ai_code_review.gitlab.models import WebhookEvent
from ai_code_review.utils.logger import get_logger

logger = get_logger(__name__)


class WebhookHandler:
    """Handler for GitLab webhook events."""

    def __init__(self) -> None:
        """Initialize webhook handler."""
        self.settings = get_settings()
        self.gitlab_client = GitLabClient()
        self.review_engine = CodeReviewEngine()
        logger.info("webhook_handler_initialized")

    async def verify_webhook(self, request: Request) -> None:
        """Verify webhook signature."""
        if not self.settings.webhook_verify_ssl:
            logger.warning("webhook_verification_disabled")
            return

        token = request.headers.get("X-Gitlab-Token")
        if not token:
            logger.error("missing_webhook_token")
            raise HTTPException(status_code=401, detail="Missing webhook token")

        if token != self.settings.webhook_secret:
            logger.error("invalid_webhook_token")
            raise HTTPException(status_code=401, detail="Invalid webhook token")

        logger.debug("webhook_verified")

    async def handle_webhook(self, event: WebhookEvent) -> dict[str, Any]:
        """Handle incoming webhook event."""
        logger.info(
            "handling_webhook",
            object_kind=event.object_kind,
            event_type=event.event_type,
        )

        if event.object_kind != "merge_request":
            logger.info("ignoring_non_mr_event", object_kind=event.object_kind)
            return {"status": "ignored", "reason": "Not a merge request event"}

        # Extract MR information
        mr_attrs = event.object_attributes
        action = mr_attrs.get("action")
        project_id = event.project.get("id")
        mr_iid = mr_attrs.get("iid")
        state = mr_attrs.get("state")

        logger.info(
            "mr_webhook_received",
            project_id=project_id,
            mr_iid=mr_iid,
            action=action,
            state=state,
        )

        # Only process opened and updated MRs
        if action not in ["open", "update", "reopen"]:
            logger.info("ignoring_mr_action", action=action)
            return {"status": "ignored", "reason": f"Action '{action}' not processed"}

        if state not in ["opened", "reopened"]:
            logger.info("ignoring_mr_state", state=state)
            return {"status": "ignored", "reason": f"State '{state}' not processed"}

        # Process the MR review
        try:
            await self.process_mr_review(project_id, mr_iid)
            return {"status": "success", "project_id": project_id, "mr_iid": mr_iid}
        except Exception as e:
            logger.error("webhook_processing_error", error=str(e), project_id=project_id, mr_iid=mr_iid)
            return {"status": "error", "error": str(e)}

    async def process_mr_review(self, project_id: int, mr_iid: int) -> None:
        """Process a merge request review."""
        logger.info("processing_mr_review", project_id=project_id, mr_iid=mr_iid)

        try:
            # Add in-progress label
            if self.settings.enable_auto_labeling:
                from ai_code_review.gitlab.models import MergeRequestLabel

                self.gitlab_client.add_labels(project_id, mr_iid, [MergeRequestLabel.IN_PROGRESS.value])

            # Get MR information
            mr_info = self.gitlab_client.get_merge_request_info(project_id, mr_iid)

            # Perform review
            summary = await self.review_engine.review_merge_request(mr_info)

            # Post individual issue comments
            for issue in summary.issues:
                if issue.severity in ["critical", "high"]:  # Only post critical and high issues as inline comments
                    self.gitlab_client.post_issue_comment(project_id, mr_iid, issue)

            # Post overall summary
            self.gitlab_client.post_review_summary(project_id, mr_iid, summary)

            logger.info("mr_review_completed", project_id=project_id, mr_iid=mr_iid)

        except Exception as e:
            logger.error("mr_review_failed", error=str(e), project_id=project_id, mr_iid=mr_iid)
            # Try to post error comment
            try:
                self.gitlab_client.post_comment(
                    project_id,
                    mr_iid,
                    f"❌ **AI Code Review Failed**\n\nAn error occurred during the automated review: {str(e)}\n\nPlease contact the development team.",
                )
            except Exception:
                pass
            raise
