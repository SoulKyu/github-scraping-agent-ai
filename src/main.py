"""GitHub Scraping AI - Main entry point."""

import argparse
import asyncio
import logging
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from dateutil.relativedelta import relativedelta

from src.cache import RepoCache
from src.config import load_config
from src.discord import DiscordClient
from src.github import AsyncGitHubClient
from src.llm import create_provider
from src.prompt import load_prompt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def parse_since_date(since_value: str) -> str:
    """Parse --since value to ISO date string.

    Supports:
    - Relative time: 7d (days), 12h (hours), 1m (months)
    - ISO date: 2024-12-10

    Returns:
        ISO date string (YYYY-MM-DD)
    """
    # Check for relative time pattern
    match = re.match(r"^(\d+)([hdm])$", since_value.lower())
    if match:
        amount = int(match.group(1))
        unit = match.group(2)

        now = datetime.now()
        if unit == "h":
            result = now - timedelta(hours=amount)
        elif unit == "d":
            result = now - timedelta(days=amount)
        elif unit == "m":
            result = now - relativedelta(months=amount)

        return result.date().isoformat()

    # Assume ISO date format
    return since_value


def log_rejected_repo(log_path: Path, repo, reason: str) -> None:
    """Log a rejected repository to file for prompt fine-tuning."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a") as f:
        f.write(f"[{timestamp}] {repo.full_name} ({repo.stars}⭐)\n")
        f.write(f"  URL: {repo.url}\n")
        f.write(f"  Description: {repo.description or 'N/A'}\n")
        f.write(f"  Language: {repo.language or 'N/A'}\n")
        f.write(f"  Topics: {', '.join(repo.topics) if repo.topics else 'N/A'}\n")
        f.write(f"  Reason: {reason}\n")
        f.write("\n")


async def run_pipeline_async(
    config_path: Path,
    prompt_path: Path,
    cache_path: Path,
    dry_run: bool = False,
    since_date: str | None = None,
    rejected_log_path: Path | None = None,
    min_stars: int | None = None,
) -> dict:
    """Run the GitHub discovery pipeline asynchronously.

    Returns:
        Dict with 'processed' and 'matched' counts
    """
    # Load configuration
    config = load_config(config_path)
    prompt = load_prompt(prompt_path)
    cache = RepoCache(cache_path, cache_days=config.cache_days)

    # Calculate date range
    if since_date is None:
        since_date = (date.today() - timedelta(days=1)).isoformat()

    logger.info(f"Fetching repos created since {since_date}")

    # Resolve min_stars (CLI overrides config)
    effective_min_stars = min_stars if min_stars is not None else config.min_stars

    # Get cached repos to skip during fetch
    cached_repos = cache.get_seen_repos()
    logger.info(f"Repos in cache: {len(cached_repos)}")

    # Fetch repositories using async client (skips cached repos)
    async with AsyncGitHubClient(token=config.github_token, max_concurrency=10) as github:
        # Search repos (excludes forks and cached repos)
        new_repos = await github.search_repos(
            since_date=since_date,
            max_repos=config.max_repos,
            exclude_forks=True,
            keywords=config.keywords if config.keywords else None,
            skip_repos=cached_repos,
        )
        if config.keywords:
            logger.info(f"Found {len(new_repos)} new repositories matching keywords: {', '.join(config.keywords)}")
        else:
            logger.info(f"Found {len(new_repos)} new repositories (forks excluded)")

        # Filter by minimum stars
        if effective_min_stars > 0:
            new_repos = [r for r in new_repos if r.stars >= effective_min_stars]
            logger.info(f"After min_stars filter ({effective_min_stars}): {len(new_repos)} repositories")

        # Fetch READMEs concurrently for new repos only
        if new_repos:
            logger.info(f"Fetching READMEs for {len(new_repos)} repos concurrently...")
            readmes = await github.fetch_readmes(new_repos, max_chars=config.readme_max_chars)

            # Attach READMEs to repos
            for repo in new_repos:
                repo.readme = readmes.get(repo.full_name, "")

    # Evaluate with LLM
    llm = create_provider(config.llm_provider, config.llm_model, config.llm_api_key)
    matched = []
    rejected_count = 0

    for i, repo in enumerate(new_repos):
        logger.info(f"Evaluating {i+1}/{len(new_repos)}: {repo.full_name}")
        result = llm.evaluate(repo, prompt)

        if result.interested:
            matched.append((repo, result))
            logger.info(f"  ✓ Interested: {result.reason}")
        else:
            logger.debug(f"  ✗ Not interested: {result.reason}")
            rejected_count += 1
            if rejected_log_path:
                log_rejected_repo(rejected_log_path, repo, result.reason)

        # Mark as seen regardless of interest
        cache.mark_seen(repo.full_name)

    if rejected_log_path and rejected_count > 0:
        logger.info(f"Logged {rejected_count} rejected repos to {rejected_log_path}")

    logger.info(f"Matched {len(matched)} repos out of {len(new_repos)}")

    # Send to Discord
    if not dry_run and matched:
        discord = DiscordClient(webhook_url=config.discord_webhook_url)
        try:
            discord.send_summary(total_found=len(matched), total_processed=len(new_repos))
            discord.send_repos(matched, batch_size=config.batch_size)
            logger.info("Sent results to Discord")
        finally:
            discord.close()
    elif dry_run:
        logger.info("Dry run - not sending to Discord")
        for repo, result in matched:
            print(f"  {repo.full_name} ({repo.stars}⭐): {result.reason}")

    # Save cache
    cache.prune()
    cache.save()

    return {"processed": len(new_repos), "matched": len(matched)}


def run_pipeline(
    config_path: Path,
    prompt_path: Path,
    cache_path: Path,
    dry_run: bool = False,
    since_date: str | None = None,
    rejected_log_path: Path | None = None,
    min_stars: int | None = None,
) -> dict:
    """Run the GitHub discovery pipeline (sync wrapper).

    Returns:
        Dict with 'processed' and 'matched' counts
    """
    return asyncio.run(
        run_pipeline_async(
            config_path=config_path,
            prompt_path=prompt_path,
            cache_path=cache_path,
            dry_run=dry_run,
            since_date=since_date,
            rejected_log_path=rejected_log_path,
            min_stars=min_stars,
        )
    )


def main() -> int:
    """Run the GitHub scraping pipeline."""
    parser = argparse.ArgumentParser(description="Discover interesting GitHub projects")
    parser.add_argument("--dry-run", action="store_true", help="Show results without posting to Discord")
    parser.add_argument("--since", type=str, help="Time range: relative (7d, 12h, 1m) or ISO date (YYYY-MM-DD)")
    parser.add_argument("--config", type=str, default="config.json", help="Path to config file")
    parser.add_argument("--prompt", type=str, default="prompt.md", help="Path to prompt file")
    parser.add_argument("--cache", type=str, default="seen_repos.json", help="Path to cache file")
    parser.add_argument("--rejected-log", type=str, default="rejected_repos.log", help="Path to rejected repos log file")
    parser.add_argument("--min-stars", type=int, default=None, help="Minimum stars required (overrides config)")

    args = parser.parse_args()

    # Resolve paths relative to current directory
    base_dir = Path.cwd()
    config_path = base_dir / args.config
    prompt_path = base_dir / args.prompt
    cache_path = base_dir / args.cache
    rejected_log_path = base_dir / args.rejected_log

    # Parse since date if provided
    since_date = None
    if args.since:
        since_date = parse_since_date(args.since)
        logger.info(f"Using date filter: {since_date}")

    try:
        result = run_pipeline(
            config_path=config_path,
            prompt_path=prompt_path,
            cache_path=cache_path,
            dry_run=args.dry_run,
            since_date=since_date,
            rejected_log_path=rejected_log_path,
            min_stars=args.min_stars,
        )
        logger.info(f"Done! Processed {result['processed']}, matched {result['matched']}")
        return 0
    except FileNotFoundError as e:
        logger.error(str(e))
        return 1
    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
