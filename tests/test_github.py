"""Tests for GitHub API client."""

import base64
import httpx
import pytest

from src.github import Repository, GitHubClient, AsyncGitHubClient


def test_repository_from_api_response():
    """Repository parses from GitHub API response."""
    api_data = {
        "full_name": "owner/repo",
        "html_url": "https://github.com/owner/repo",
        "description": "A cool project",
        "stargazers_count": 150,
        "language": "Python",
        "topics": ["ai", "cli"],
        "created_at": "2025-12-10T10:00:00Z",
        "fork": False,
    }

    repo = Repository.from_api(api_data)

    assert repo.full_name == "owner/repo"
    assert repo.url == "https://github.com/owner/repo"
    assert repo.description == "A cool project"
    assert repo.stars == 150
    assert repo.language == "Python"
    assert repo.topics == ["ai", "cli"]
    assert repo.is_fork is False


def test_repository_handles_missing_fields():
    """Repository handles None/missing fields gracefully."""
    api_data = {
        "full_name": "owner/repo",
        "html_url": "https://github.com/owner/repo",
        "description": None,
        "stargazers_count": 10,
        "language": None,
        "topics": [],
        "created_at": "2025-12-10T10:00:00Z",
    }

    repo = Repository.from_api(api_data)

    assert repo.description == ""
    assert repo.language == ""
    assert repo.topics == []
    assert repo.is_fork is False  # Default when not present


def test_repository_detects_fork():
    """Repository correctly identifies forks."""
    api_data = {
        "full_name": "owner/forked-repo",
        "html_url": "https://github.com/owner/forked-repo",
        "description": "A forked project",
        "stargazers_count": 50,
        "language": "Python",
        "topics": [],
        "fork": True,
    }

    repo = Repository.from_api(api_data)

    assert repo.is_fork is True


@pytest.fixture
def mock_search_response():
    """Mock GitHub search API response with mix of forks and non-forks."""
    return {
        "total_count": 3,
        "items": [
            {
                "full_name": "owner/repo1",
                "html_url": "https://github.com/owner/repo1",
                "description": "First repo",
                "stargazers_count": 200,
                "language": "Python",
                "topics": ["ai"],
                "created_at": "2025-12-10T10:00:00Z",
                "fork": False,
            },
            {
                "full_name": "owner/forked-repo",
                "html_url": "https://github.com/owner/forked-repo",
                "description": "A fork",
                "stargazers_count": 180,
                "language": "Python",
                "topics": [],
                "created_at": "2025-12-10T10:30:00Z",
                "fork": True,
            },
            {
                "full_name": "owner/repo2",
                "html_url": "https://github.com/owner/repo2",
                "description": "Second repo",
                "stargazers_count": 150,
                "language": "Rust",
                "topics": ["cli"],
                "created_at": "2025-12-10T11:00:00Z",
                "fork": False,
            },
        ],
    }


def test_github_client_search_repos(mock_search_response):
    """GitHubClient fetches and parses repositories with fork:false in query."""
    request_count = 0
    captured_url = None

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count, captured_url
        request_count += 1
        captured_url = str(request.url)
        assert "api.github.com/search/repositories" in captured_url
        assert "Authorization" in request.headers

        # Return data only on first page (only non-forks since API filters them)
        if request_count == 1:
            # Simulate API already filtering forks with fork:false
            non_fork_response = {
                "total_count": 2,
                "items": [item for item in mock_search_response["items"] if not item.get("fork", False)]
            }
            return httpx.Response(200, json=non_fork_response)
        else:
            return httpx.Response(200, json={"total_count": 0, "items": []})

    transport = httpx.MockTransport(mock_handler)
    client = GitHubClient(token="test-token", transport=transport)

    repos = client.search_repos(since_date="2025-12-10", max_repos=100, exclude_forks=True)

    # Verify fork:false is in the query
    assert "fork" in captured_url
    # Should return 2 repos (API excluded forks)
    assert len(repos) == 2
    assert repos[0].full_name == "owner/repo1"
    assert repos[0].stars == 200
    assert repos[1].full_name == "owner/repo2"


def test_github_client_search_repos_include_forks(mock_search_response):
    """GitHubClient can include forks when requested."""
    request_count = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        if request_count == 1:
            return httpx.Response(200, json=mock_search_response)
        else:
            return httpx.Response(200, json={"total_count": 0, "items": []})

    transport = httpx.MockTransport(mock_handler)
    client = GitHubClient(token="test-token", transport=transport)

    repos = client.search_repos(since_date="2025-12-10", max_repos=100, exclude_forks=False)

    # Should return all 3 repos including fork
    assert len(repos) == 3
    assert any(repo.is_fork for repo in repos)


def test_github_client_search_repos_with_keywords(mock_search_response):
    """GitHubClient builds OR query with keywords."""
    captured_url = None

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_url
        captured_url = str(request.url)
        return httpx.Response(200, json={"total_count": 0, "items": []})

    transport = httpx.MockTransport(mock_handler)
    client = GitHubClient(token="test-token", transport=transport)

    client.search_repos(
        since_date="2025-12-10",
        max_repos=100,
        keywords=["kubernetes", "devops", "terraform"]
    )

    # Query should include keywords with OR logic
    assert "kubernetes" in captured_url
    assert "devops" in captured_url
    assert "terraform" in captured_url


def test_github_client_search_repos_without_keywords(mock_search_response):
    """GitHubClient works without keywords (default behavior)."""
    captured_url = None

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_url
        captured_url = str(request.url)
        return httpx.Response(200, json={"total_count": 0, "items": []})

    transport = httpx.MockTransport(mock_handler)
    client = GitHubClient(token="test-token", transport=transport)

    client.search_repos(since_date="2025-12-10", max_repos=100)

    # Query should just have the date filter
    assert "created%3A%3E2025-12-10" in captured_url or "created:>2025-12-10" in captured_url


def test_github_client_fetch_readme():
    """GitHubClient fetches and decodes README."""
    readme_content = "# My Project\n\nThis is a cool project."
    encoded = base64.b64encode(readme_content.encode()).decode()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        if "readme" in str(request.url):
            return httpx.Response(200, json={"content": encoded, "encoding": "base64"})
        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)
    client = GitHubClient(token="test-token", transport=transport)

    readme = client.fetch_readme("owner/repo", max_chars=500)

    assert "My Project" in readme
    assert "cool project" in readme


def test_github_client_fetch_readme_not_found():
    """GitHubClient returns empty string when README not found."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)
    client = GitHubClient(token="test-token", transport=transport)

    readme = client.fetch_readme("owner/repo", max_chars=500)

    assert readme == ""


def test_github_client_fetch_readme_truncates():
    """GitHubClient truncates README to max_chars."""
    readme_content = "A" * 1000
    encoded = base64.b64encode(readme_content.encode()).decode()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"content": encoded, "encoding": "base64"})

    transport = httpx.MockTransport(mock_handler)
    client = GitHubClient(token="test-token", transport=transport)

    readme = client.fetch_readme("owner/repo", max_chars=100)

    assert len(readme) == 100


# Async client tests

@pytest.mark.asyncio
async def test_async_github_client_search_repos():
    """AsyncGitHubClient fetches repositories with fork:false in query."""
    # Response simulates GitHub API already filtering forks via fork:false query
    mock_response = {
        "total_count": 1,
        "items": [
            {
                "full_name": "owner/repo1",
                "html_url": "https://github.com/owner/repo1",
                "description": "First repo",
                "stargazers_count": 200,
                "language": "Python",
                "topics": ["devops"],
                "fork": False,
            },
        ],
    }

    request_count = 0
    captured_url = None

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count, captured_url
        request_count += 1
        captured_url = str(request.url)
        if request_count == 1:
            return httpx.Response(200, json=mock_response)
        return httpx.Response(200, json={"total_count": 0, "items": []})

    async with AsyncGitHubClient(token="test-token") as client:
        # Override the client with mock
        client._client = httpx.AsyncClient(
            base_url="https://api.github.com",
            transport=httpx.MockTransport(mock_handler),
        )

        repos = await client.search_repos(since_date="2025-12-10", exclude_forks=True)

        # Verify fork:false is in the query
        assert "fork" in captured_url
        assert len(repos) == 1
        assert repos[0].full_name == "owner/repo1"
        assert repos[0].is_fork is False


@pytest.mark.asyncio
async def test_async_github_client_search_repos_with_keywords():
    """AsyncGitHubClient builds OR query with keywords."""
    captured_url = None

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_url
        captured_url = str(request.url)
        return httpx.Response(200, json={"total_count": 0, "items": []})

    async with AsyncGitHubClient(token="test-token") as client:
        client._client = httpx.AsyncClient(
            base_url="https://api.github.com",
            transport=httpx.MockTransport(mock_handler),
        )

        await client.search_repos(
            since_date="2025-12-10",
            keywords=["helm", "gitops"]
        )

        assert "helm" in captured_url
        assert "gitops" in captured_url


@pytest.mark.asyncio
async def test_async_github_client_fetch_readmes():
    """AsyncGitHubClient fetches READMEs concurrently."""
    readme1 = base64.b64encode(b"# Repo 1 README").decode()
    readme2 = base64.b64encode(b"# Repo 2 README").decode()

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "repo1/readme" in url:
            return httpx.Response(200, json={"content": readme1, "encoding": "base64"})
        elif "repo2/readme" in url:
            return httpx.Response(200, json={"content": readme2, "encoding": "base64"})
        return httpx.Response(404)

    repos = [
        Repository("owner/repo1", "url1", "desc1", 100, "Python", [], False),
        Repository("owner/repo2", "url2", "desc2", 50, "Go", [], False),
    ]

    async with AsyncGitHubClient(token="test-token") as client:
        client._client = httpx.AsyncClient(
            base_url="https://api.github.com",
            transport=httpx.MockTransport(mock_handler),
        )

        readmes = await client.fetch_readmes(repos, max_chars=500)

        assert "Repo 1 README" in readmes["owner/repo1"]
        assert "Repo 2 README" in readmes["owner/repo2"]
