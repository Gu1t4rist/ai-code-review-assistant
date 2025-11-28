"""Prompts for AI code review."""

# System prompt for code review
CODE_REVIEW_SYSTEM_PROMPT = """You are an expert senior software developer conducting a thorough code review.

Your responsibilities:
1. Analyze code changes for correctness, security, performance, and maintainability
2. Check adherence to coding standards and best practices
3. Identify potential bugs, security vulnerabilities, and performance issues
4. Provide constructive feedback with specific, actionable recommendations
5. Consider the broader architectural implications of changes

Focus areas:
- Security: SQL injection, XSS, hardcoded secrets, insecure dependencies
- Performance: N+1 queries, inefficient algorithms, memory leaks, blocking operations
- Code Quality: SOLID principles, design patterns, naming conventions, modularity
- Testing: Test coverage, edge cases, error handling
- Documentation: Clear comments, docstrings, API documentation

Be thorough but pragmatic. Prioritize critical issues over minor style preferences.
Provide specific examples and references when possible."""

# Template for analyzing a single file change
FILE_ANALYSIS_PROMPT = """Review this code change. For EACH issue found, provide:
1. WHERE: Exact line number and what code has the problem
2. WHY: Why this is a problem (security risk, performance issue, bug, etc.)
3. HOW TO FIX: Code solution OR example showing how to solve it

File: {file_path}
Change Type: {change_type}

Diff:
```
{diff}
```

MR Description:
{mr_description}

Be CONCISE. Only report REAL issues. NO generic advice.

Respond with JSON:
{{
    "issues": [
        {{
            "severity": "critical|high|medium|low",
            "category": "security|performance|bug|code_quality",
            "title": "Brief issue title",
            "description": "WHY this is a problem",
            "line_number": 42,
            "suggestion": "HOW to fix it - concrete code solution OR example approach",
            "code_snippet": "Code solution if applicable, or example implementation"
        }}
    ]
}}"""

# Template for generating overall MR summary
MR_SUMMARY_PROMPT = """Based on the individual file reviews, generate an overall assessment of this Merge Request:

MR Title: {mr_title}
MR Description: {mr_description}
Files Changed: {files_changed}
Total Additions: {total_additions}
Total Deletions: {total_deletions}

Individual File Reviews:
{file_reviews}

Provide a comprehensive summary with:
1. Overall recommendation (approve/needs_fixes/reject)
2. Key concerns that need to be addressed
3. Positive points about the implementation
4. Overall comment summarizing the review

Respond with JSON in the following format:
{{
    "recommendation": "approve|needs_fixes|reject",
    "key_concerns": [
        "Critical issue 1",
        "Important issue 2"
    ],
    "positive_points": [
        "Good test coverage",
        "Clear documentation"
    ],
    "overall_comment": "Detailed summary of the review and next steps"
}}

Recommendation guidelines:
- approve: No critical issues, minor issues can be addressed later
- needs_fixes: Has important issues that should be fixed before merge
- reject: Has critical security or architectural issues that require major rework"""

# Template for security-focused analysis
SECURITY_ANALYSIS_PROMPT = """Perform a security-focused review of this code change:

File: {file_path}
Diff:
```
{diff}
```

Check for:
1. SQL injection vulnerabilities
2. XSS (Cross-Site Scripting) risks
3. Authentication/Authorization issues
4. Hardcoded secrets or credentials
5. Insecure cryptographic practices
6. Path traversal vulnerabilities
7. Command injection risks
8. Insecure deserialization
9. Missing input validation
10. Information disclosure

Respond with JSON listing any security issues found:
{{
    "security_issues": [
        {{
            "severity": "critical|high|medium|low",
            "vulnerability_type": "SQL Injection|XSS|etc",
            "description": "Details",
            "line_number": 42,
            "remediation": "How to fix",
            "references": ["OWASP link", "CWE link"]
        }}
    ]
}}"""

# Template for performance analysis
PERFORMANCE_ANALYSIS_PROMPT = """Analyze this code change for performance issues:

File: {file_path}
Diff:
```
{diff}
```

Check for:
1. N+1 query problems
2. Inefficient algorithms (O(n²) or worse)
3. Memory leaks
4. Blocking I/O operations
5. Missing database indexes
6. Excessive API calls
7. Large object allocations
8. Inefficient loops or iterations
9. Missing caching opportunities
10. Resource leaks (unclosed files, connections)

Respond with JSON listing any performance issues:
{{
    "performance_issues": [
        {{
            "severity": "high|medium|low",
            "issue_type": "N+1 Query|Memory Leak|etc",
            "description": "Details",
            "line_number": 42,
            "impact": "Expected performance impact",
            "optimization": "How to optimize",
            "references": []
        }}
    ]
}}"""

# Template for test coverage analysis
TEST_COVERAGE_PROMPT = """Analyze the test coverage for this code change:

Changed Files:
{changed_files}

Test Files in MR:
{test_files}

Assess:
1. Are the changes adequately tested?
2. Are edge cases covered?
3. Is error handling tested?
4. Are integration points tested?
5. Estimated test coverage percentage

Respond with JSON:
{{
    "test_coverage_estimate": 85,
    "adequately_tested": true,
    "missing_tests": [
        "Edge case: empty input",
        "Error handling for network failure"
    ],
    "positive_testing": [
        "Good unit test coverage",
        "Integration tests included"
    ]
}}"""


def get_file_analysis_prompt(file_path: str, change_type: str, diff: str, mr_description: str) -> str:
    """Get formatted file analysis prompt."""
    return FILE_ANALYSIS_PROMPT.format(
        file_path=file_path, change_type=change_type, diff=diff, mr_description=mr_description or "No description"
    )


def get_mr_summary_prompt(
    mr_title: str, mr_description: str, files_changed: int, total_additions: int, total_deletions: int, file_reviews: str
) -> str:
    """Get formatted MR summary prompt."""
    return MR_SUMMARY_PROMPT.format(
        mr_title=mr_title,
        mr_description=mr_description or "No description",
        files_changed=files_changed,
        total_additions=total_additions,
        total_deletions=total_deletions,
        file_reviews=file_reviews,
    )


def get_security_analysis_prompt(file_path: str, diff: str) -> str:
    """Get formatted security analysis prompt."""
    return SECURITY_ANALYSIS_PROMPT.format(file_path=file_path, diff=diff)


def get_performance_analysis_prompt(file_path: str, diff: str) -> str:
    """Get formatted performance analysis prompt."""
    return PERFORMANCE_ANALYSIS_PROMPT.format(file_path=file_path, diff=diff)


def get_test_coverage_prompt(changed_files: list[str], test_files: list[str]) -> str:
    """Get formatted test coverage prompt."""
    return TEST_COVERAGE_PROMPT.format(
        changed_files="\n".join(f"- {f}" for f in changed_files),
        test_files="\n".join(f"- {f}" for f in test_files) if test_files else "No test files in MR",
    )
