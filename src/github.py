"""GitHub API client for repository discovery."""

import asyncio
import base64
from dataclasses import dataclass

import httpx


@dataclass
class Repository:
    """A GitHub repository."""

    full_name: str
    url: str
    description: str
    stars: int
    language: str
    topics: list[str]
    is_fork: bool = False
    readme: str = ""

    @classmethod
    def from_api(cls, data: dict) -> "Repository":
        """Create Repository from GitHub API response."""
        return cls(
            full_name=data["full_name"],
            url=data["html_url"],
            description=data.get("description") or "",
            stars=data["stargazers_count"],
            language=data.get("language") or "",
            topics=data.get("topics") or [],
            is_fork=data.get("fork", False),
        )


class GitHubClient:
    """Synchronous client for GitHub API (for backwards compatibility)."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str, transport: httpx.BaseTransport | None = None):
        """Initialize with GitHub token."""
        self.token = token
        self._client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            transport=transport,
            timeout=30.0,
        )

    def search_repos(
        self,
        since_date: str,
        max_repos: int = 1000,
        exclude_forks: bool = True,
        keywords: list[str] | None = None,
    ) -> list[Repository]:
        """Search for repositories created since given date, sorted by stars.

        Args:
            since_date: ISO date string (YYYY-MM-DD) to search from
            max_repos: Maximum number of repositories to return
            exclude_forks: Whether to exclude forked repositories
            keywords: Optional list of keywords for OR-based full-text search
        """
        # GitHub limits to 5 OR operators, so max 6 keywords per query
        MAX_KEYWORDS_PER_QUERY = 6

        if keywords and len(keywords) > MAX_KEYWORDS_PER_QUERY:
            # Split into batches and combine results
            keyword_batches = [
                keywords[i:i + MAX_KEYWORDS_PER_QUERY]
                for i in range(0, len(keywords), MAX_KEYWORDS_PER_QUERY)
            ]
            all_repos: dict[str, Repository] = {}
            for batch in keyword_batches:
                batch_repos = self._search_repos_single(
                    since_date, max_repos, exclude_forks, batch
                )
                for repo in batch_repos:
                    if repo.full_name not in all_repos:
                        all_repos[repo.full_name] = repo
            # Sort by stars descending and limit
            sorted_repos = sorted(all_repos.values(), key=lambda r: r.stars, reverse=True)
            return sorted_repos[:max_repos]
        else:
            return self._search_repos_single(since_date, max_repos, exclude_forks, keywords)

    def _search_repos_single(
        self,
        since_date: str,
        max_repos: int,
        exclude_forks: bool,
        keywords: list[str] | None,
    ) -> list[Repository]:
        """Execute a single search query."""
        repos: list[Repository] = []
        page = 1
        per_page = 100

        # Build query with optional keywords and fork filter
        query = f"created:>{since_date}"
        if exclude_forks:
            query = f"{query} fork:false"
        if keywords:
            keyword_query = " OR ".join(keywords)
            query = f"{query} ({keyword_query})"

        while len(repos) < max_repos:
            response = self._client.get(
                "/search/repositories",
                params={
                    "q": query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": per_page,
                    "page": page,
                },
            )
            response.raise_for_status()
            data = response.json()

            items = data.get("items", [])
            if not items:
                break

            for item in items:
                repo = Repository.from_api(item)
                repos.append(repo)
                if len(repos) >= max_repos:
                    break

            page += 1
            if page > 10:  # GitHub limits to 1000 results
                break

        return repos

    def fetch_readme(self, full_name: str, max_chars: int = 500) -> str:
        """Fetch README for a repository, truncated to max_chars."""
        try:
            response = self._client.get(f"/repos/{full_name}/readme")
            if response.status_code == 404:
                return ""
            response.raise_for_status()

            data = response.json()
            content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            return content[:max_chars]
        except httpx.HTTPError:
            return ""

    def close(self):
        """Close the HTTP client."""
        self._client.close()


class AsyncGitHubClient:
    """Async client for GitHub API with concurrent README fetching."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str, max_concurrency: int = 10):
        """Initialize with GitHub token and concurrency limit."""
        self.token = token
        self.max_concurrency = max_concurrency
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "AsyncGitHubClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    async def search_repos(
        self,
        since_date: str,
        max_repos: int = 1000,
        exclude_forks: bool = True,
        keywords: list[str] | None = None,
    ) -> list[Repository]:
        """Search for repositories created since given date, sorted by stars.

        Args:
            since_date: ISO date string (YYYY-MM-DD) to search from
            max_repos: Maximum number of repositories to return
            exclude_forks: Whether to exclude forked repositories
            keywords: Optional list of keywords for OR-based full-text search
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        # GitHub limits to 5 OR operators, so max 6 keywords per query
        MAX_KEYWORDS_PER_QUERY = 6

        if keywords and len(keywords) > MAX_KEYWORDS_PER_QUERY:
            # Split into batches and combine results
            keyword_batches = [
                keywords[i:i + MAX_KEYWORDS_PER_QUERY]
                for i in range(0, len(keywords), MAX_KEYWORDS_PER_QUERY)
            ]
            all_repos: dict[str, Repository] = {}
            for batch in keyword_batches:
                batch_repos = await self._search_repos_single(
                    since_date, max_repos, exclude_forks, batch
                )
                for repo in batch_repos:
                    if repo.full_name not in all_repos:
                        all_repos[repo.full_name] = repo
            # Sort by stars descending and limit
            sorted_repos = sorted(all_repos.values(), key=lambda r: r.stars, reverse=True)
            return sorted_repos[:max_repos]
        else:
            return await self._search_repos_single(since_date, max_repos, exclude_forks, keywords)

    async def _search_repos_single(
        self,
        since_date: str,
        max_repos: int,
        exclude_forks: bool,
        keywords: list[str] | None,
    ) -> list[Repository]:
        """Execute a single search query."""
        repos: list[Repository] = []
        page = 1
        per_page = 100

        # Build query with optional keywords and fork filter
        query = f"created:>{since_date}"
        if exclude_forks:
            query = f"{query} fork:false"
        if keywords:
            keyword_query = " OR ".join(keywords)
            query = f"{query} ({keyword_query})"

        while len(repos) < max_repos:
            response = await self._client.get(
                "/search/repositories",
                params={
                    "q": query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": per_page,
                    "page": page,
                },
            )
            response.raise_for_status()
            data = response.json()

            items = data.get("items", [])
            if not items:
                break

            for item in items:
                repo = Repository.from_api(item)
                repos.append(repo)
                if len(repos) >= max_repos:
                    break

            page += 1
            if page > 10:  # GitHub limits to 1000 results
                break

        return repos

    async def _fetch_single_readme(
        self, full_name: str, max_chars: int, semaphore: asyncio.Semaphore
    ) -> tuple[str, str]:
        """Fetch README for a single repository with semaphore."""
        if not self._client:
            return full_name, ""

        async with semaphore:
            try:
                response = await self._client.get(f"/repos/{full_name}/readme")
                if response.status_code == 404:
                    return full_name, ""
                response.raise_for_status()

                data = response.json()
                content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
                return full_name, content[:max_chars]
            except httpx.HTTPError:
                return full_name, ""

    async def fetch_readmes(
        self, repos: list[Repository], max_chars: int = 500
    ) -> dict[str, str]:
        """Fetch READMEs for multiple repositories concurrently.

        Returns:
            Dict mapping full_name to README content
        """
        semaphore = asyncio.Semaphore(self.max_concurrency)

        tasks = [
            self._fetch_single_readme(repo.full_name, max_chars, semaphore)
            for repo in repos
        ]

        results = await asyncio.gather(*tasks)
        return dict(results)
