"""Simple tests for GitLab client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ai_code_review.gitlab.client import GitLabClient


class TestGitLabClient:
    """Basic tests for GitLab client."""

    @pytest.mark.asyncio
    async def test_client_close(self):
        """Test closing the client."""
        mock_httpx = AsyncMock()
        with patch("ai_code_review.gitlab.client.httpx.AsyncClient", return_value=mock_httpx):
            client = GitLabClient()
            await client.close()
            mock_httpx.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_merge_request(self):
        """Test fetching merge request."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": 1,
            "iid": 45,
            "title": "Test MR",
            "state": "opened",
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_httpx = AsyncMock()
        mock_httpx.get.return_value = mock_response
        
        with patch("ai_code_review.gitlab.client.httpx.AsyncClient", return_value=mock_httpx):
            client = GitLabClient()
            mr = await client.get_merge_request(123, 45)
            
            assert mr["iid"] == 45
            assert mr["title"] == "Test MR"
            mock_httpx.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_changes(self):
        """Test parsing changes from diff."""
        with patch("ai_code_review.gitlab.client.httpx.AsyncClient"):
            client = GitLabClient()
            
            changes_data = {
                "changes": [
                    {
                        "new_path": "test.py",
                        "old_path": "test.py",
                        "new_file": False,
                        "deleted_file": False,
                        "renamed_file": False,
                        "diff": "@@ -1,2 +1,3 @@\n-old\n+new1\n+new2",
                    }
                ]
            }
            
            changes = client._parse_changes(changes_data)
            
            assert len(changes) == 1
            assert changes[0].file_path == "test.py"
            assert changes[0].additions == 2
            assert changes[0].deletions == 1
