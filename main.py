from __future__ import annotations

import logging
import time
from collections import Counter
from dataclasses import dataclass
from typing import Optional

import click
import schedule
from rich.console import Console
from rich.table import Table

from services.auth_service import AuthService
from services.email_classifier import EmailClassifier
from services.gmail_service import GmailService
from services.ml_classifier import MLClassifier
from services.persistence_service import ProcessedStore
from services.sentiment_service import SentimentResult, SentimentService
from services.statistics_service import StatisticsService
from services.strategies import MLStrategy, RuleBasedStrategy
from utils.config import AccountConfig, AppConfig, load_config
from utils.logger import configure_logging
from utils.rules_engine import RulesEngine


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class AppContext:
    config: AppConfig
    account: AccountConfig
    gmail: GmailService
    classifier: EmailClassifier
    stats: StatisticsService
    processed_store: ProcessedStore
    console: Console
    sentiment: Optional[SentimentService]


def build_context(env_file: str, account_name: str | None) -> AppContext:
    config = load_config(env_file)
    configure_logging(config.log_dir, config.log_level)
    account = config.get_account(account_name)
    console = Console()

    auth_service = AuthService(account)
    gmail_service = GmailService(account, auth_service)
    rules_engine = RulesEngine(config.rules_file)
    strategies = [RuleBasedStrategy(rules_engine)]
    ml_classifier = MLClassifier.from_config(config)
    if ml_classifier and ml_classifier.is_ready:
        strategies.append(MLStrategy(ml_classifier))
    classifier = EmailClassifier(strategies)
    stats = StatisticsService(config.stats_file)
    processed_store = ProcessedStore(config.db_path)
    try:
        sentiment = SentimentService()
    except RuntimeError as exc:  # pragma: no cover - dependency is required at runtime
        LOGGER.warning("Sentiment analysis disabled: %s", exc)
        sentiment = None

    return AppContext(
        config=config,
        account=account,
        gmail=gmail_service,
        classifier=classifier,
        stats=stats,
        processed_store=processed_store,
        console=console,
        sentiment=sentiment,
    )


@click.group()
@click.option("--env-file", default=".env", show_default=True, help="Path to the .env file")
@click.option("--account", help="Account name defined in accounts.json")
@click.pass_context
def cli(ctx: click.Context, env_file: str, account: Optional[str]) -> None:
    """Command-line interface for the Gmail assistant."""

    try:
        ctx.obj = build_context(env_file, account)
    except KeyError as exc:  # invalid account
        raise click.BadParameter(str(exc), param_hint="--account") from exc


@cli.command("fetch")
@click.option("--max-results", type=int, default=None, help="Maximum number of emails to fetch")
@click.pass_obj
def fetch_emails(app: AppContext, max_results: int | None) -> None:
    """Fetch unread emails and print a summary."""

    emails = _perform_fetch(app, max_results)
    if emails:
        table = _build_fetch_table(app, emails)
        app.console.print(table)
    else:
        app.console.print("[bold green]No unread emails found.[/bold green]")


@cli.command("label")
@click.option("--max-results", type=int, default=None, help="Maximum number of emails to label")
@click.option("--dry-run/--apply", default=False, help="Preview actions without modifying Gmail")
@click.pass_obj
def label_emails(app: AppContext, max_results: int | None, dry_run: bool) -> None:
    """Fetch unread emails, classify them, and apply labels automatically."""

    result = _perform_label(app, max_results, dry_run=dry_run)
    if result is None:
        app.console.print("[bold green]No unread emails to label.[/bold green]")
        return

    applied_labels, skipped = result
    if applied_labels:
        summary = ", ".join(f"{label}: {count}" for label, count in applied_labels.items())
        prefix = "[bold blue]Dry-run[/bold blue]" if dry_run else "[bold blue]Applied labels[/bold blue]"
        app.console.print(f"{prefix} {summary}")
    else:
        app.console.print("[yellow]No labels were applied. Adjust your rules, ML model, or dry-run filters.[/yellow]")

    if skipped:
        app.console.print(f"[dim]{skipped} emails skipped because they were already processed.[/dim]")


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

    table = Table(title="Global stats")
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

    accounts = snapshot.get("accounts", {})
    if accounts:
        acct_table = Table(title="Per-account stats")
        acct_table.add_column("Account")
        acct_table.add_column("Fetch runs")
        acct_table.add_column("Emails seen")
        acct_table.add_column("Label runs")
        acct_table.add_column("Labels")
        for name, data in accounts.items():
            label_counts = data.get("labels", {})
            label_str = ", ".join(f"{label}: {count}" for label, count in label_counts.items()) or "-"
            acct_table.add_row(
                name,
                str(data.get("fetch_runs", 0)),
                str(data.get("emails_seen", 0)),
                str(data.get("label_runs", 0)),
                label_str,
            )
        app.console.print(acct_table)


@cli.command("schedule")
@click.option("--task", type=click.Choice(["fetch", "label"]), default="label", show_default=True)
@click.option("--interval", type=int, default=15, show_default=True, help="Interval in minutes")
@click.option("--max-results", type=int, default=None, help="Limit emails per run")
@click.option("--dry-run/--apply", default=False, help="Dry-run when scheduling label task")
@click.pass_obj
def schedule_tasks(app: AppContext, task: str, interval: int, max_results: int | None, dry_run: bool) -> None:
    """Run fetch or label tasks on an interval using the schedule library."""

    def job() -> None:
        if task == "fetch":
            emails = _perform_fetch(app, max_results)
            app.console.print(
                f"[scheduler] Retrieved {len(emails)} unread email(s) for {app.account.name}."
            )
            if emails:
                table = _build_fetch_table(app, emails)
                app.console.print(table)
        else:
            result = _perform_label(app, max_results, dry_run=dry_run)
            if result is None:
                app.console.print("[scheduler] No unread emails to label.")
                return
            applied, skipped = result
            summary = ", ".join(f"{label}: {count}" for label, count in applied.items()) or "none"
            prefix = "would label" if dry_run else "applied"
            app.console.print(
                f"[scheduler] {prefix} {summary} (skipped {skipped} already processed)."
            )

    schedule.every(interval).minutes.do(job)

    app.console.print(
        f"Scheduling '{task}' every {interval} minute(s) for account {app.account.name}. Press Ctrl+C to stop."
    )
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        app.console.print("Scheduler stopped.")


def main() -> None:
    cli(standalone_mode=True)


if __name__ == "__main__":
    main()


def _perform_fetch(app: AppContext, max_results: int | None):
    limit = max_results or app.config.fetch_batch_size
    emails = app.gmail.fetch_unread_messages(limit)
    app.stats.record_fetch(app.account.name, len(emails))
    return emails


def _perform_label(app: AppContext, max_results: int | None, dry_run: bool) -> Optional[tuple[Counter[str], int]]:
    limit = max_results or app.config.fetch_batch_size
    emails = app.gmail.fetch_unread_messages(limit)
    if not emails:
        return None

    label_cache: dict[str, str] = {}
    applied_labels: Counter[str] = Counter()
    skipped = 0

    for email in emails:
        if app.processed_store.is_processed(app.account.name, email.id):
            skipped += 1
            continue
        labels = app.classifier.classify(email)
        if not labels:
            LOGGER.info("Skipping %s because no labels matched", email.id)
            continue

        if dry_run:
            app.console.print(f"[dry-run] Would apply {labels} to '{email.subject}' ({email.id})")
        else:
            label_ids = []
            for label in labels:
                if label not in label_cache:
                    label_cache[label] = app.gmail.ensure_label(label)
                label_ids.append(label_cache[label])
            app.gmail.apply_labels(email.id, label_ids)
            app.processed_store.mark_processed(app.account.name, email.id)
        for label in labels:
            applied_labels[label] += 1

    if applied_labels and not dry_run:
        app.stats.record_label_application(app.account.name, applied_labels)

    return applied_labels, skipped


def _build_fetch_table(app: AppContext, emails) -> Table:
    table = Table(title=f"Unread emails for {app.account.name}", show_lines=False)
    table.add_column("ID", overflow="fold")
    table.add_column("Subject")
    table.add_column("Sender")
    table.add_column("Snippet")
    if app.sentiment:
        table.add_column("Sentiment")

    for email in emails:
        sentiment_display = "N/A"
        if app.sentiment:
            sentiment = app.sentiment.analyze(email)
            sentiment_display = _format_sentiment(sentiment)
        row = [email.id, email.subject, email.sender or "Unknown", email.snippet]
        if app.sentiment:
            row.append(sentiment_display)
        table.add_row(*row)
    return table


def _format_sentiment(sentiment: SentimentResult) -> str:
    return f"{sentiment.label} ({sentiment.compound:.2f})"
