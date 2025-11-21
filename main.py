#!/usr/bin/env python3
"""
Job Search Assistant CLI
Search for remote jobs and identify companies with Taiwan team members
"""
import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
import pandas as pd
from dotenv import load_dotenv
from loguru import logger
from rich.console import Console
from rich.table import Table

from src.scrapers import IndeedScraper, get_indeed_scraper, CRAWL4AI_AVAILABLE
from src.database import JobStorage
from src.utils import JobDeduplicator
from src.models import JobBoard

# Load environment variables
load_dotenv()

# Setup logging
logger.add("logs/job_search_{time}.log", rotation="1 day", retention="7 days")

console = Console()


@click.group()
def cli():
    """Job Search Assistant - Find remote jobs with Taiwan teams"""
    pass


@cli.command()
@click.argument('query')
@click.option('--location', default='Remote', help='Location filter')
@click.option('--max-results', default=50, help='Maximum number of results')
@click.option('--board', default='indeed', type=click.Choice(['indeed']), help='Job board to scrape')
@click.option('--remote-only/--no-remote-only', default=True, help='Filter for remote jobs only')
@click.option('--save/--no-save', default=True, help='Save results to database')
@click.option('--export', type=click.Path(), help='Export to CSV file')
@click.option('--browser', default='chromium', type=click.Choice(['chromium', 'firefox']), help='Browser type (firefox is often less detectable)')
@click.option('--headless/--no-headless', default=True, help='Run browser in headless mode')
@click.option('--scraper', default='playwright', type=click.Choice(['playwright', 'crawl4ai']), help='Scraper implementation (crawl4ai has better anti-detection)')
@click.option('--extraction-mode', default='css', type=click.Choice(['css', 'llm', 'hybrid']), help='Crawl4AI extraction mode (llm/hybrid requires API key)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose debug logging')
def search(query: str, location: str, max_results: int, board: str, remote_only: bool, save: bool, export: Optional[str], browser: str, headless: bool, scraper: str, extraction_mode: str, verbose: bool):
    """
    Search for jobs on job boards

    Example: python main.py search "software engineer" --max-results 20

    For debugging Indeed blocks, try:
      python main.py search "your query" --no-headless --verbose

    For better anti-detection with Crawl4AI:
      python main.py search "your query" --scraper crawl4ai

    For LLM-based extraction (higher accuracy, requires API key):
      python main.py search "your query" --scraper crawl4ai --extraction-mode hybrid
    """
    # Configure logging level
    if verbose:
        logger.remove()
        logger.add(lambda msg: console.print(msg, end=''), level="DEBUG")
        console.print("[yellow]🐛 Verbose logging enabled[/yellow]")
    else:
        logger.remove()
        logger.add(lambda msg: console.print(msg, end=''), level="INFO")

    console.print(f"\n[bold blue]Searching for:[/bold blue] {query}")
    console.print(f"[dim]Location: {location} | Board: {board} | Max results: {max_results}[/dim]")

    if not headless:
        console.print(f"[yellow]⚠️  Running in VISIBLE browser mode (debugging)[/yellow]")
        console.print(f"[dim]You'll see the browser window open. This helps identify blocking issues.[/dim]")

    console.print()

    if browser == 'firefox':
        console.print(f"[cyan]🦊 Using Firefox browser (often less detectable)[/cyan]")

    # Show scraper info
    if scraper == 'crawl4ai':
        if not CRAWL4AI_AVAILABLE:
            console.print("[red]Error: crawl4ai not installed. Install with: pip install crawl4ai[/red]")
            return
        console.print(f"[cyan]🤖 Using Crawl4AI scraper (enhanced anti-detection)[/cyan]")
        console.print(f"[dim]Extraction mode: {extraction_mode}[/dim]")
        if extraction_mode in ('llm', 'hybrid'):
            if not os.getenv('OPENAI_API_KEY') and not os.getenv('ANTHROPIC_API_KEY'):
                console.print("[yellow]⚠️  No LLM API key found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY for LLM extraction.[/yellow]")

    # Run async scraping
    jobs = asyncio.run(_search_jobs(query, location, max_results, board, remote_only, browser, headless, scraper, extraction_mode))

    if not jobs:
        console.print("[yellow]No jobs found.[/yellow]")
        return

    console.print(f"[green]Found {len(jobs)} jobs[/green]\n")

    # Deduplicate
    unique_jobs = JobDeduplicator.deduplicate_jobs(jobs)
    console.print(f"[green]After deduplication: {len(unique_jobs)} unique jobs[/green]\n")

    # Save to database
    if save:
        db = JobStorage(os.getenv('DATABASE_URL', 'sqlite:///jobs.db'))
        saved = db.save_jobs(unique_jobs)
        console.print(f"[green]Saved {saved} new jobs to database[/green]\n")

    # Display results
    _display_jobs_table(unique_jobs[:20])  # Show top 20

    # Export to CSV
    if export:
        _export_to_csv(unique_jobs, export)
        console.print(f"\n[green]Exported to {export}[/green]")


@cli.command()
@click.option('--limit', default=50, help='Number of jobs to show')
@click.option('--min-taiwan-team', default=0, help='Minimum Taiwan team members')
@click.option('--enriched-only', is_flag=True, help='Show only enriched jobs')
@click.option('--export', type=click.Path(), help='Export to CSV file')
def list(limit: int, min_taiwan_team: int, enriched_only: bool, export: Optional[str]):
    """
    List jobs from database

    Example: python main.py list --limit 20 --min-taiwan-team 1
    """
    db = JobStorage(os.getenv('DATABASE_URL', 'sqlite:///jobs.db'))
    jobs = db.get_jobs(limit=limit, min_taiwan_team=min_taiwan_team, enriched_only=enriched_only)

    if not jobs:
        console.print("[yellow]No jobs found in database.[/yellow]")
        return

    console.print(f"\n[bold blue]Jobs from database:[/bold blue] {len(jobs)} jobs\n")

    # Convert to JobListing for display
    from src.models import JobListing
    job_listings = []
    for job in jobs:
        job_listing = JobListing(
            id=job.id,
            title=job.title,
            company=job.company,
            location=job.location,
            description=job.description,
            url=job.url,
            posted_date=job.posted_date,
            board_source=JobBoard[job.board_source.name],
            scraped_at=job.scraped_at
        )
        # Add enrichment info if available
        if enriched_only or job.taiwan_team_count > 0:
            console.print(f"  Taiwan team: {job.taiwan_team_count}, Score: {job.ranking_score}")

        job_listings.append(job_listing)

    _display_jobs_table(job_listings, show_score=enriched_only)

    if export:
        _export_to_csv(job_listings, export)
        console.print(f"\n[green]Exported to {export}[/green]")


@cli.command()
@click.option('--service', default='peopledatalabs', type=click.Choice(['peopledatalabs', 'coresignal']), help='Enrichment service')
@click.option('--max-jobs', default=50, help='Maximum number of jobs to enrich')
@click.option('--min-taiwan-team', default=1, help='Minimum Taiwan team members to keep')
@click.option('--export', type=click.Path(), help='Export enriched jobs to CSV')
def enrich(service: str, max_jobs: int, min_taiwan_team: int, export: Optional[str]):
    """
    Enrich jobs with LinkedIn company data

    Example: python main.py enrich --service peopledatalabs --max-jobs 20
    """
    console.print(f"\n[bold blue]Enriching jobs with {service}[/bold blue]\n")

    # Get unenriched jobs from database
    db = JobStorage(os.getenv('DATABASE_URL', 'sqlite:///jobs.db'))
    jobs_db = db.get_jobs(limit=max_jobs, enriched_only=False)

    if not jobs_db:
        console.print("[yellow]No jobs found in database. Run 'search' first.[/yellow]")
        return

    # Convert to JobListing
    from src.models import JobListing
    jobs = []
    for job_db in jobs_db:
        job = JobListing(
            id=job_db.id,
            title=job_db.title,
            company=job_db.company,
            location=job_db.location,
            description=job_db.description,
            url=job_db.url,
            posted_date=job_db.posted_date,
            board_source=JobBoard[job_db.board_source.name],
            scraped_at=job_db.scraped_at
        )
        jobs.append(job)

    console.print(f"Found {len(jobs)} jobs to enrich\n")

    # Run enrichment
    from src.enrichment import EnrichmentService
    from src.utils.ranker import RankingConfig

    # Load config from env
    target_industries = os.getenv('TARGET_INDUSTRIES', 'Technology,SaaS,Fintech').split(',')
    target_sizes = os.getenv('TARGET_COMPANY_SIZES', '11-50,51-200').split(',')

    ranking_config = RankingConfig(
        target_industries=target_industries,
        target_company_sizes=target_sizes,
        min_taiwan_team=min_taiwan_team
    )

    enriched_jobs = asyncio.run(_enrich_jobs_async(jobs, service, ranking_config))

    console.print(f"\n[green]Enriched {len(enriched_jobs)} jobs[/green]\n")

    # Display top results
    if enriched_jobs:
        _display_enriched_jobs_table(enriched_jobs[:20])

    # Export if requested
    if export:
        _export_enriched_to_csv(enriched_jobs, export)
        console.print(f"\n[green]Exported to {export}[/green]")


@cli.command()
@click.option('--days', default=30, help='Delete jobs older than N days')
def cleanup(days: int):
    """
    Clean up old jobs from database

    Example: python main.py cleanup --days 30
    """
    db = JobStorage(os.getenv('DATABASE_URL', 'sqlite:///jobs.db'))
    deleted = db.cleanup_old_jobs(days=days)
    console.print(f"[green]Deleted {deleted} jobs older than {days} days[/green]")


async def _search_jobs(query: str, location: str, max_results: int, board: str, remote_only: bool, browser: str = 'chromium', headless: bool = True, scraper_type: str = 'playwright', extraction_mode: str = 'css'):
    """Async job search"""
    if board == 'indeed':
        config = {
            'headless': headless,
            'browser': browser,
            'extraction_mode': extraction_mode,
        }

        # Choose scraper implementation
        use_crawl4ai = scraper_type == 'crawl4ai'
        scraper = get_indeed_scraper(use_crawl4ai=use_crawl4ai, config=config)

        async with scraper:
            jobs = await scraper.search(
                query=query,
                location=location,
                max_results=max_results,
                remote_only=remote_only
            )
            return jobs
    else:
        console.print(f"[red]Board '{board}' not yet implemented[/red]")
        return []


async def _enrich_jobs_async(jobs, service, ranking_config):
    """Async job enrichment"""
    from src.enrichment import EnrichmentService

    async with EnrichmentService(service=service) as enrichment_service:
        enriched_jobs = await enrichment_service.enrich_jobs(jobs, ranking_config)
        return enriched_jobs


def _display_jobs_table(jobs, show_score=False):
    """Display jobs in a rich table"""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Title", style="cyan", width=40)
    table.add_column("Company", style="green", width=20)
    table.add_column("Location", width=15)
    table.add_column("Posted", width=12)
    if show_score:
        table.add_column("Score", width=8)
        table.add_column("TW Team", width=8)

    for job in jobs:
        posted = job.posted_date.strftime('%Y-%m-%d') if job.posted_date else 'Unknown'

        if show_score:
            score = getattr(job, 'ranking_score', 0.0)
            tw_count = getattr(job, 'taiwan_team_count', 0)
            table.add_row(
                job.title[:40],
                job.company[:20],
                job.location[:15],
                posted,
                f"{score:.1f}",
                str(tw_count)
            )
        else:
            table.add_row(
                job.title[:40],
                job.company[:20],
                job.location[:15],
                posted
            )

    console.print(table)


def _display_enriched_jobs_table(jobs):
    """Display enriched jobs in a rich table"""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Title", style="cyan", width=35)
    table.add_column("Company", style="green", width=20)
    table.add_column("Industry", width=15)
    table.add_column("TW Team", width=8)
    table.add_column("Score", width=8)
    table.add_column("Size", width=10)

    for job in jobs:
        table.add_row(
            job.title[:35],
            job.company[:20],
            (job.industry or 'N/A')[:15],
            str(job.taiwan_team_count),
            f"{job.ranking_score:.1f}",
            job.company_size or 'N/A'
        )

    console.print(table)


def _export_to_csv(jobs, filepath: str):
    """Export jobs to CSV"""
    data = []
    for job in jobs:
        data.append({
            'title': job.title,
            'company': job.company,
            'location': job.location,
            'url': job.url,
            'posted_date': job.posted_date.isoformat() if job.posted_date else '',
            'description': job.description[:200] + '...' if len(job.description) > 200 else job.description,
            'board': job.board_source.value,
            'scraped_at': job.scraped_at.isoformat() if job.scraped_at else ''
        })

    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False)


def _export_enriched_to_csv(jobs, filepath: str):
    """Export enriched jobs to CSV"""
    data = []
    for job in jobs:
        data.append({
            'title': job.title,
            'company': job.company,
            'location': job.location,
            'url': job.url,
            'taiwan_team_count': job.taiwan_team_count,
            'ranking_score': job.ranking_score,
            'industry': job.industry or '',
            'company_size': job.company_size or '',
            'posted_date': job.posted_date.isoformat() if job.posted_date else '',
            'description': job.description[:200] + '...' if len(job.description) > 200 else job.description,
            'board': job.board_source.value
        })

    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False)


if __name__ == '__main__':
    cli()
