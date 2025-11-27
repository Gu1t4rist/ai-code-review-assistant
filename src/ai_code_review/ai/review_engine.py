"""AI-powered code review engine."""

import asyncio
import time
from typing import Any

from ai_code_review.ai.llm_client import get_llm_client
from ai_code_review.ai.prompts import (
    CODE_REVIEW_SYSTEM_PROMPT,
    get_file_analysis_prompt,
    get_mr_summary_prompt,
    get_performance_analysis_prompt,
    get_security_analysis_prompt,
    get_test_coverage_prompt,
)
from ai_code_review.config import get_review_rules, get_settings
from ai_code_review.gitlab.models import (
    DiffChange,
    IssueCategory,
    IssueSeverity,
    MergeRequestInfo,
    ReviewIssue,
    ReviewRecommendation,
    ReviewRuleConfig,
    ReviewSummary,
)
from ai_code_review.utils.logger import get_logger
from ai_code_review.utils.metrics import (
    active_reviews,
    review_duration_seconds,
    review_files_processed,
    review_issues_found,
    review_total,
)

logger = get_logger(__name__)


class CodeReviewEngine:
    """Engine for AI-powered code review."""

    def __init__(self, review_rules: ReviewRuleConfig | None = None) -> None:
        """
        Initialize code review engine.
        
        Args:
            review_rules: Optional review rules config. If None, loads from settings.
        """
        self.settings = get_settings()
        self.llm_client = get_llm_client()
        
        # Load review rules (team-specific or default)
        if review_rules is None:
            try:
                self.review_rules = get_review_rules()
                logger.info("review_rules_loaded", profile=self.review_rules.team_name)
            except Exception as e:
                logger.warning("failed_to_load_review_rules", error=str(e))
                # Fallback to default rules
                self.review_rules = ReviewRuleConfig()
                logger.info("using_default_review_rules")
        else:
            self.review_rules = review_rules
        
        logger.info(
            "code_review_engine_initialized",
            team=self.review_rules.team_name,
            security=self.review_rules.check_security,
            performance=self.review_rules.check_performance,
            quality=self.review_rules.check_code_quality,
        )

    async def review_merge_request(self, mr_info: MergeRequestInfo) -> ReviewSummary:
        """Perform complete review of a merge request."""
        logger.info(
            "starting_mr_review",
            project_id=mr_info.project_id,
            mr_iid=mr_info.iid,
            files_changed=len(mr_info.changes),
        )
        
        start_time = time.time()
        active_reviews.inc()
        status = "success"

        try:
            # Filter changes based on settings
            changes_to_review = self._filter_changes(mr_info.changes)

            if not changes_to_review:
                logger.warning("no_changes_to_review")
                return self._create_empty_summary(mr_info)

            # Track files processed
            review_files_processed.labels(
                ai_provider=self.settings.ai_provider,
            ).observe(len(changes_to_review))

            # Review each file
            file_reviews: list[dict[str, Any]] = []
            all_issues: list[ReviewIssue] = []

            # Process files in parallel (with limit)
            semaphore = asyncio.Semaphore(self.settings.max_concurrent_reviews)

            async def review_with_semaphore(change: DiffChange) -> dict[str, Any] | None:
                async with semaphore:
                    return await self._review_file_change(change, mr_info)

            review_tasks = [review_with_semaphore(change) for change in changes_to_review]
            file_reviews_results = await asyncio.gather(*review_tasks, return_exceptions=True)

            for result in file_reviews_results:
                if isinstance(result, Exception):
                    logger.error("file_review_failed", error=str(result))
                    continue
                if result:
                    file_reviews.append(result)
                    # Filter issues by severity threshold and max per file
                    issues = result.get("issues", [])
                    filtered_issues = self._filter_issues_by_severity(issues)[:self.review_rules.max_issues_per_file]
                    all_issues.extend(filtered_issues)

            # Additional analyses based on review rules
            if self.review_rules.check_security and self.settings.enable_security_scan:
                logger.debug("performing_security_scan")
                security_issues = await self._perform_security_scan(changes_to_review)
                filtered_security = self._filter_issues_by_severity(security_issues)
                all_issues.extend(filtered_security)

            if self.review_rules.check_performance and self.settings.enable_performance_check:
                logger.debug("performing_performance_check")
                performance_issues = await self._perform_performance_check(changes_to_review)
                filtered_performance = self._filter_issues_by_severity(performance_issues)
                all_issues.extend(filtered_performance)

            # Analyze test coverage (if enabled in rules)
            test_coverage = None
            if self.review_rules.check_testing:
                test_coverage = await self._analyze_test_coverage(mr_info)

            # Generate overall summary
            summary = await self._generate_summary(mr_info, file_reviews, all_issues, test_coverage)
            
            # Track issues by severity
            for issue in all_issues:
                review_issues_found.labels(
                    severity=issue.severity.value,
                    ai_provider=self.settings.ai_provider,
                ).inc()

            logger.info(
                "mr_review_completed",
                recommendation=summary.recommendation,
                total_issues=len(summary.issues),
                critical_issues=len(summary.critical_issues),
            )

            return summary
        
        except Exception as e:
            status = "error"
            raise
        finally:
            # Record metrics
            duration = time.time() - start_time
            review_duration_seconds.labels(
                ai_provider=self.settings.ai_provider,
                ai_model=self.settings.ai_model,
            ).observe(duration)
            
            review_total.labels(
                ai_provider=self.settings.ai_provider,
                ai_model=self.settings.ai_model,
                status=status,
            ).inc()
            
            active_reviews.dec()

    def _filter_changes(self, changes: list[DiffChange]) -> list[DiffChange]:
        """Filter changes based on review settings and rules."""
        filtered = []

        for change in changes:
            # Skip deleted files
            if change.deleted_file:
                continue

            # Skip large files
            total_lines = change.additions + change.deletions
            if total_lines > self.settings.max_diff_size:
                logger.warning(
                    "skipping_large_file",
                    file_path=change.file_path,
                    lines=total_lines,
                )
                continue

            # Check against include/exclude patterns from review rules
            if not self._should_review_file(change.file_path):
                logger.debug("skipping_file_by_rules", file_path=change.file_path)
                continue

            filtered.append(change)

        logger.info("filtered_changes", original=len(changes), filtered=len(filtered))
        return filtered
    
    def _should_review_file(self, file_path: str) -> bool:
        """Check if file should be reviewed based on rules patterns."""
        from fnmatch import fnmatch
        
        # Check exclude patterns first
        for pattern in self.review_rules.exclude_patterns:
            if fnmatch(file_path, pattern):
                return False
        
        # Check include patterns
        for pattern in self.review_rules.include_patterns:
            if fnmatch(file_path, pattern):
                return True
        
        # Default: don't review if no patterns match
        return False

    def _is_ignored_file(self, file_path: str) -> bool:
        """Check if file should be ignored in review."""
        ignored_patterns = [
            ".lock",
            "package-lock.json",
            "yarn.lock",
            "poetry.lock",
            ".min.js",
            ".min.css",
            "dist/",
            "build/",
            "node_modules/",
            ".git/",
            "__pycache__/",
            ".pyc",
            ".jpg",
            ".png",
            ".gif",
            ".svg",
            ".pdf",
        ]

        file_lower = file_path.lower()
        return any(pattern in file_lower for pattern in ignored_patterns)

    async def _review_file_change(self, change: DiffChange, mr_info: MergeRequestInfo) -> dict[str, Any]:
        """Review a single file change."""
        logger.debug("reviewing_file", file_path=change.file_path)

        change_type = "new file" if change.new_file else "modified"
        if change.renamed_file:
            change_type = "renamed"

        prompt = get_file_analysis_prompt(
            file_path=change.file_path, change_type=change_type, diff=change.diff, mr_description=mr_info.description or ""
        )

        try:
            result = await self.llm_client.generate_structured_output(prompt, CODE_REVIEW_SYSTEM_PROMPT)

            # Convert to ReviewIssue objects
            issues = []
            for issue_data in result.get("issues", []):
                try:
                    issue = ReviewIssue(
                        severity=IssueSeverity(issue_data.get("severity", "medium")),
                        category=IssueCategory(issue_data.get("category", "code_quality")),
                        file_path=change.file_path,
                        line_number=issue_data.get("line_number"),
                        title=issue_data.get("title", "Code issue"),
                        description=issue_data.get("description", ""),
                        suggestion=issue_data.get("suggestion"),
                        code_snippet=issue_data.get("code_snippet"),
                        references=issue_data.get("references", []),
                    )
                    issues.append(issue)
                except Exception as e:
                    logger.warning("failed_to_parse_issue", error=str(e), issue_data=issue_data)

            return {
                "file_path": change.file_path,
                "issues": issues,
                "positive_points": result.get("positive_points", []),
                "assessment": result.get("assessment", ""),
            }

        except Exception as e:
            logger.error("file_review_error", file_path=change.file_path, error=str(e))
            return {"file_path": change.file_path, "issues": [], "positive_points": [], "assessment": "Review failed"}

    async def _perform_security_scan(self, changes: list[DiffChange]) -> list[ReviewIssue]:
        """Perform focused security analysis."""
        logger.info("performing_security_scan", files=len(changes))
        security_issues: list[ReviewIssue] = []

        for change in changes:
            if self._is_code_file(change.file_path):
                prompt = get_security_analysis_prompt(change.file_path, change.diff)

                try:
                    result = await self.llm_client.generate_structured_output(prompt, CODE_REVIEW_SYSTEM_PROMPT)

                    for issue_data in result.get("security_issues", []):
                        try:
                            issue = ReviewIssue(
                                severity=IssueSeverity(issue_data.get("severity", "high")),
                                category=IssueCategory.SECURITY,
                                file_path=change.file_path,
                                line_number=issue_data.get("line_number"),
                                title=issue_data.get("vulnerability_type", "Security Issue"),
                                description=issue_data.get("description", ""),
                                suggestion=issue_data.get("remediation"),
                                references=issue_data.get("references", []),
                            )
                            security_issues.append(issue)
                        except Exception as e:
                            logger.warning("failed_to_parse_security_issue", error=str(e))

                except Exception as e:
                    logger.error("security_scan_error", file_path=change.file_path, error=str(e))

        logger.info("security_scan_completed", issues_found=len(security_issues))
        return security_issues

    async def _perform_performance_check(self, changes: list[DiffChange]) -> list[ReviewIssue]:
        """Perform focused performance analysis."""
        logger.info("performing_performance_check", files=len(changes))
        performance_issues: list[ReviewIssue] = []

        for change in changes:
            if self._is_code_file(change.file_path):
                prompt = get_performance_analysis_prompt(change.file_path, change.diff)

                try:
                    result = await self.llm_client.generate_structured_output(prompt, CODE_REVIEW_SYSTEM_PROMPT)

                    for issue_data in result.get("performance_issues", []):
                        try:
                            issue = ReviewIssue(
                                severity=IssueSeverity(issue_data.get("severity", "medium")),
                                category=IssueCategory.PERFORMANCE,
                                file_path=change.file_path,
                                line_number=issue_data.get("line_number"),
                                title=issue_data.get("issue_type", "Performance Issue"),
                                description=f"{issue_data.get('description', '')}\\n\\nImpact: {issue_data.get('impact', 'Unknown')}",
                                suggestion=issue_data.get("optimization"),
                                references=issue_data.get("references", []),
                            )
                            performance_issues.append(issue)
                        except Exception as e:
                            logger.warning("failed_to_parse_performance_issue", error=str(e))

                except Exception as e:
                    logger.error("performance_check_error", file_path=change.file_path, error=str(e))

        logger.info("performance_check_completed", issues_found=len(performance_issues))
        return performance_issues

    async def _analyze_test_coverage(self, mr_info: MergeRequestInfo) -> float | None:
        """Analyze test coverage of the changes."""
        logger.info("analyzing_test_coverage")

        changed_files = [change.file_path for change in mr_info.changes if not change.deleted_file]
        test_files = [f for f in changed_files if self._is_test_file(f)]

        if not changed_files:
            return None

        prompt = get_test_coverage_prompt(changed_files, test_files)

        try:
            result = await self.llm_client.generate_structured_output(prompt, CODE_REVIEW_SYSTEM_PROMPT)
            coverage = result.get("test_coverage_estimate")
            logger.info("test_coverage_analyzed", coverage=coverage)
            return coverage
        except Exception as e:
            logger.error("test_coverage_analysis_error", error=str(e))
            return None

    async def _generate_summary(
        self, mr_info: MergeRequestInfo, file_reviews: list[dict[str, Any]], all_issues: list[ReviewIssue], test_coverage: float | None
    ) -> ReviewSummary:
        """Generate overall review summary."""
        logger.info("generating_summary")

        # Collect all positive points
        all_positive_points = []
        for review in file_reviews:
            all_positive_points.extend(review.get("positive_points", []))

        # Format file reviews for prompt
        file_reviews_text = "\\n\\n".join(
            [
                f"File: {r['file_path']}\\nIssues: {len(r['issues'])}\\nAssessment: {r['assessment']}"
                for r in file_reviews
            ]
        )

        # Calculate totals
        total_additions = sum(c.additions for c in mr_info.changes)
        total_deletions = sum(c.deletions for c in mr_info.changes)

        prompt = get_mr_summary_prompt(
            mr_title=mr_info.title,
            mr_description=mr_info.description or "",
            files_changed=len(mr_info.changes),
            total_additions=total_additions,
            total_deletions=total_deletions,
            file_reviews=file_reviews_text,
        )

        try:
            result = await self.llm_client.generate_structured_output(prompt, CODE_REVIEW_SYSTEM_PROMPT)

            recommendation = ReviewRecommendation(result.get("recommendation", "needs_fixes"))
            key_concerns = result.get("key_concerns", [])
            positive_points = result.get("positive_points", all_positive_points[:5])
            overall_comment = result.get("overall_comment", "Review completed")

        except Exception as e:
            logger.error("summary_generation_error", error=str(e))
            # Fallback to rule-based recommendation
            recommendation = self._rule_based_recommendation(all_issues)
            key_concerns = [f"{issue.title} in {issue.file_path}" for issue in all_issues[:5]]
            positive_points = all_positive_points[:5]
            overall_comment = "Automated review completed. Please review the findings."

        return ReviewSummary(
            recommendation=recommendation,
            total_files=len(mr_info.changes),
            total_additions=total_additions,
            total_deletions=total_deletions,
            issues=all_issues,
            positive_points=positive_points,
            key_concerns=key_concerns,
            test_coverage=test_coverage,
            overall_comment=overall_comment,
        )

    def _rule_based_recommendation(self, issues: list[ReviewIssue]) -> ReviewRecommendation:
        """Generate recommendation based on issue severity and review rules."""
        critical_count = sum(1 for issue in issues if issue.severity == IssueSeverity.CRITICAL)
        high_count = sum(1 for issue in issues if issue.severity == IssueSeverity.HIGH)

        # Check if we should block based on review rules
        if self.review_rules.block_merge_on_critical and critical_count > 0:
            return ReviewRecommendation.REJECT
        elif self.review_rules.block_merge_on_high and high_count > 0:
            return ReviewRecommendation.NEEDS_FIXES
        elif critical_count > 0:  # Critical without block rule
            return ReviewRecommendation.NEEDS_FIXES
        elif high_count > 3:
            return ReviewRecommendation.NEEDS_FIXES
        elif high_count > 0 or len(issues) > 5:
            return ReviewRecommendation.NEEDS_FIXES
        else:
            return ReviewRecommendation.APPROVE

    def _filter_issues_by_severity(self, issues: list[ReviewIssue]) -> list[ReviewIssue]:
        """Filter issues based on minimum severity threshold from review rules."""
        severity_order = {
            IssueSeverity.CRITICAL: 4,
            IssueSeverity.HIGH: 3,
            IssueSeverity.MEDIUM: 2,
            IssueSeverity.LOW: 1,
            IssueSeverity.INFO: 0,
        }
        
        min_severity_value = severity_order.get(self.review_rules.min_severity_for_comment, 2)
        
        filtered = [
            issue for issue in issues
            if severity_order.get(issue.severity, 0) >= min_severity_value
        ]
        
        logger.debug(
            "filtered_issues_by_severity",
            original_count=len(issues),
            filtered_count=len(filtered),
            min_severity=self.review_rules.min_severity_for_comment.value,
        )
        
        return filtered
    
    def _is_code_file(self, file_path: str) -> bool:
        """Check if file is a code file."""
        code_extensions = [".py", ".js", ".ts", ".java", ".go", ".rb", ".php", ".cpp", ".c", ".cs", ".rs"]
        return any(file_path.endswith(ext) for ext in code_extensions)

    def _is_test_file(self, file_path: str) -> bool:
        """Check if file is a test file."""
        test_patterns = ["test_", "_test.", "tests/", "/test/", ".spec.", ".test."]
        file_lower = file_path.lower()
        return any(pattern in file_lower for pattern in test_patterns)

    def _create_empty_summary(self, mr_info: MergeRequestInfo) -> ReviewSummary:
        """Create an empty summary when no files to review."""
        return ReviewSummary(
            recommendation=ReviewRecommendation.APPROVE,
            total_files=len(mr_info.changes),
            total_additions=sum(c.additions for c in mr_info.changes),
            total_deletions=sum(c.deletions for c in mr_info.changes),
            issues=[],
            positive_points=["No significant code changes to review"],
            key_concerns=[],
            test_coverage=None,
            overall_comment="No reviewable code changes found in this MR.",
        )
