from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List

import click
from rich.console import Console
from rich.table import Table

from services.auth_service import AuthService
from services.email_classifier import EmailClassifier
from services.gmail_service import GmailService
from services.ml_classifier import MLClassifier
from services.statistics_service import StatisticsService
from utils.config import AppConfig, load_config
from utils.logger import configure_logging
from utils.rules_engine import RulesEngine


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class AppContext:
    config: AppConfig
    gmail: GmailService
    classifier: EmailClassifier
    stats: StatisticsService
    console: Console


def build_context(env_file: str) -> AppContext:
    config = load_config(env_file)
    configure_logging(config.log_dir, config.log_level)
    console = Console()

    auth_service = AuthService(config)
    gmail_service = GmailService(config, auth_service)
    rules_engine = RulesEngine(config.rules_file)
    ml_classifier = MLClassifier.from_config(config)
    classifier = EmailClassifier(rules_engine, ml_classifier)
    stats = StatisticsService(config.stats_file)

    return AppContext(
        config=config,
        gmail=gmail_service,
        classifier=classifier,
        stats=stats,
        console=console,
    )


@click.group()
@click.option("--env-file", default=".env", show_default=True, help="Path to the .env file")
@click.pass_context
def cli(ctx: click.Context, env_file: str) -> None:
    """Command-line interface for the Gmail assistant."""

    ctx.obj = build_context(env_file)


@cli.command("fetch")
@click.option("--max-results", type=int, default=None, help="Maximum number of emails to fetch")
@click.pass_obj
def fetch_emails(app: AppContext, max_results: int | None) -> None:
    """Fetch unread emails and print a summary."""

    limit = max_results or app.config.fetch_batch_size
    emails = app.gmail.fetch_unread_messages(limit)
    app.stats.record_fetch(len(emails))

    if not emails:
        app.console.print("[bold green]No unread emails found.[/bold green]")
        return

    table = Table(title="Unread emails", show_lines=False)
    table.add_column("ID", overflow="fold")
    table.add_column("Subject")
    table.add_column("Sender")
    table.add_column("Snippet")

    for email in emails:
        table.add_row(email.id, email.subject, email.sender or "Unknown", email.snippet)

    app.console.print(table)


@cli.command("label")
@click.option("--max-results", type=int, default=None, help="Maximum number of emails to label")
@click.pass_obj
def label_emails(app: AppContext, max_results: int | None) -> None:
    """Fetch unread emails, classify them, and apply labels automatically."""

    limit = max_results or app.config.fetch_batch_size
    emails = app.gmail.fetch_unread_messages(limit)
    if not emails:
        app.console.print("[bold green]No unread emails to label.[/bold green]")
        return

    label_cache: Dict[str, str] = {}
    applied_labels: Counter[str] = Counter()

    for email in emails:
        labels = app.classifier.classify(email)
        if not labels:
            LOGGER.info("Skipping %s because no labels matched", email.id)
            continue
        label_ids: List[str] = []
        for label in labels:
            if label not in label_cache:
                label_cache[label] = app.gmail.ensure_label(label)
            label_ids.append(label_cache[label])
        app.gmail.apply_labels(email.id, label_ids)
        for label in labels:
            applied_labels[label] += 1

    if applied_labels:
        app.stats.record_label_application(applied_labels)
        summary = ", ".join(f"{label}: {count}" for label, count in applied_labels.items())
        app.console.print(f"[bold blue]Applied labels[/bold blue] {summary}")
    else:
        app.console.print("[yellow]No labels were applied. Adjust your rules or ML model.[/yellow]")


@cli.command("create-label")
@click.argument("label_name")
@click.pass_obj
def create_label(app: AppContext, label_name: str) -> None:
    """Create a Gmail label if it does not exist."""

    label_id = app.gmail.ensure_label(label_name)
    app.console.print(f"Label {label_name} is ready (id: {label_id}).")


@cli.command("stats")
@click.pass_obj
def stats(app: AppContext) -> None:
    """Display local activity statistics."""

    snapshot = app.stats.snapshot()
    if not snapshot:
        app.console.print("No stats recorded yet.")
        return

    table = Table(title="Assistant stats")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Fetch runs", str(snapshot.get("fetch_runs", 0)))
    table.add_row("Emails seen", str(snapshot.get("emails_seen", 0)))
    table.add_row("Label runs", str(snapshot.get("label_runs", 0)))

    labels = snapshot.get("labels", {})
    if labels:
        label_str = ", ".join(f"{label}: {count}" for label, count in labels.items())
        table.add_row("Label counts", label_str)

    app.console.print(table)


def main() -> None:
    cli(standalone_mode=True)


if __name__ == "__main__":
    main()
