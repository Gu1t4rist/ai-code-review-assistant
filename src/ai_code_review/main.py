"""Main application entry point."""

import asyncio
import sys
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from ai_code_review.ai.review_engine import CodeReviewEngine
from ai_code_review.config import get_settings
from ai_code_review.gitlab.client import GitLabClient
from ai_code_review.gitlab.models import WebhookEvent
from ai_code_review.gitlab.webhooks import WebhookHandler
from ai_code_review.utils.logger import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Code Review Assistant",
    description="AI-powered code review automation for GitLab",
    version="1.0.0",
)

# Initialize handlers
webhook_handler = WebhookHandler()


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": "AI Code Review Assistant",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/webhook")
async def webhook(request: Request) -> JSONResponse:
    """GitLab webhook endpoint."""
    try:
        # Verify webhook
        await webhook_handler.verify_webhook(request)

        # Parse event
        body = await request.json()
        event = WebhookEvent(**body)

        # Handle event in background
        result = await webhook_handler.handle_webhook(event)

        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("webhook_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/review")
async def trigger_review(data: dict[str, Any]) -> JSONResponse:
    """Manually trigger a review."""
    try:
        project_id = data.get("project_id")
        mr_iid = data.get("merge_request_iid")

        if not project_id or not mr_iid:
            raise HTTPException(status_code=400, detail="Missing project_id or merge_request_iid")

        # Process review in background
        asyncio.create_task(webhook_handler.process_mr_review(project_id, mr_iid))

        return JSONResponse(
            content={
                "status": "accepted",
                "project_id": project_id,
                "merge_request_iid": mr_iid,
                "message": "Review started",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("manual_review_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/metrics")
async def metrics() -> dict[str, Any]:
    """Get application metrics."""
    settings = get_settings()
    
    return {
        "ai_provider": settings.ai_provider,
        "ai_model": settings.ai_model,
        "status": "running",
    }


def run_webhook_server() -> None:
    """Run the webhook server."""
    settings = get_settings()
    logger.info(
        "starting_webhook_server",
        host=settings.host,
        port=settings.port,
        env=settings.app_env,
    )

    uvicorn.run(
        "ai_code_review.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )


async def run_single_review(project_id: int, mr_iid: int) -> None:
    """Run a single review."""
    logger.info("running_single_review", project_id=project_id, mr_iid=mr_iid)

    gitlab_client = GitLabClient()
    review_engine = CodeReviewEngine()

    try:
        # Get MR information
        mr_info = await gitlab_client.get_merge_request_info(project_id, mr_iid)
        logger.info("mr_info_retrieved", title=mr_info.title)

        # Perform review
        summary = await review_engine.review_merge_request(mr_info)

        # Post results
        for issue in summary.issues:
            if issue.severity in ["critical", "high"]:
                await gitlab_client.post_issue_comment(project_id, mr_iid, issue)

        await gitlab_client.post_review_summary(project_id, mr_iid, summary)

        logger.info("review_completed_successfully")
        print(f"\n✅ Review completed successfully!")
        print(f"Recommendation: {summary.recommendation.value}")
        print(f"Total issues: {len(summary.issues)}")
        print(f"  Critical: {len(summary.critical_issues)}")
        print(f"  High: {len(summary.high_issues)}")
        print(f"  Medium: {len(summary.medium_issues)}")
        print(f"  Low: {len(summary.low_issues)}")

    except Exception as e:
        logger.error("review_failed", error=str(e))
        print(f"\n❌ Review failed: {e}")
        sys.exit(1)
    finally:
        await gitlab_client.close()


def cli() -> None:
    """Command-line interface."""
    import argparse

    parser = argparse.ArgumentParser(description="AI Code Review Assistant")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Webhook server command
    subparsers.add_parser("webhook", help="Run webhook server")

    # Review command
    review_parser = subparsers.add_parser("review", help="Review a specific MR")
    review_parser.add_argument("--project-id", type=int, required=True, help="GitLab project ID")
    review_parser.add_argument("--mr-iid", type=int, required=True, help="Merge request IID")

    args = parser.parse_args()

    if args.command == "webhook":
        run_webhook_server()
    elif args.command == "review":
        asyncio.run(run_single_review(args.project_id, args.mr_iid))
    else:
        parser.print_help()


if __name__ == "__main__":
    cli()
