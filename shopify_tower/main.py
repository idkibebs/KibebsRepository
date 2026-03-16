"""
Shopify Inventory Control Tower — Entry point.

Commands:
    python main.py full-sync        Run full Shopify sync (first time setup)
    python main.py sync             Run incremental sync
    python main.py metrics          Compute metrics only (no sync)
    python main.py reports          Generate all CSV reports
    python main.py briefing         Print today's briefing to console
    python main.py run              Sync + metrics + reports + briefing (one shot)
    python main.py scheduler        Start the daily scheduler daemon
"""
import sys
import logging
from pathlib import Path

# ── Logging setup ─────────────────────────────────────────────────────────────
from config.settings import LOGS_DIR

LOGS_DIR = Path(LOGS_DIR)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOGS_DIR / "tower.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger(__name__)

# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_full_sync():
    from jobs.full_sync import run_full_sync
    run_full_sync()


def cmd_incremental_sync():
    from jobs.incremental_sync import run_incremental_sync
    run_incremental_sync()


def cmd_metrics():
    from metrics.compute import compute_metrics
    metrics = compute_metrics()
    logger.info("Metrics computed for %d variants.", len(metrics))
    return metrics


def cmd_reports():
    from metrics.compute import compute_metrics
    from reports.outputs import generate_all_reports
    metrics = compute_metrics()
    paths = generate_all_reports(metrics)
    for name, path in paths.items():
        logger.info("  %s → %s", name, path)


def cmd_briefing():
    from metrics.compute import compute_metrics
    from reports.briefing import print_briefing
    metrics = compute_metrics()
    print_briefing(metrics)


def cmd_run():
    """Full one-shot pipeline without scheduler."""
    from jobs.incremental_sync import run_incremental_sync
    from metrics.compute import compute_metrics
    from reports.outputs import generate_all_reports
    from reports.briefing import print_briefing, save_briefing

    run_incremental_sync()
    metrics = compute_metrics()
    generate_all_reports(metrics)
    print_briefing(metrics)
    save_briefing(metrics)


def cmd_scheduler():
    from jobs.scheduler import start_scheduler
    start_scheduler()


# ── Dispatch ──────────────────────────────────────────────────────────────────

COMMANDS = {
    "full-sync":  cmd_full_sync,
    "sync":       cmd_incremental_sync,
    "metrics":    cmd_metrics,
    "reports":    cmd_reports,
    "briefing":   cmd_briefing,
    "run":        cmd_run,
    "scheduler":  cmd_scheduler,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        print("Available commands:", ", ".join(COMMANDS))
        sys.exit(1)

    command = sys.argv[1]
    logger.info("Running command: %s", command)
    COMMANDS[command]()
