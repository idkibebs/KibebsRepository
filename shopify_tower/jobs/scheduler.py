"""
APScheduler-based daily job runner.
Runs incremental sync + metrics + briefing every day at SYNC_HOUR:SYNC_MINUTE.

Usage:
    python -m jobs.scheduler          # run the scheduler as a daemon
"""
import logging
import sys

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config.settings import SYNC_HOUR, SYNC_MINUTE

logger = logging.getLogger(__name__)


def daily_pipeline():
    """The full daily pipeline: sync → metrics → reports → briefing."""
    logger.info("Daily pipeline triggered.")
    try:
        from jobs.incremental_sync import run_incremental_sync
        from metrics.compute import compute_metrics
        from reports.outputs import generate_all_reports
        from reports.briefing import print_briefing, save_briefing

        run_incremental_sync()
        metrics = compute_metrics()
        generate_all_reports(metrics)
        print_briefing(metrics)
        save_briefing(metrics)

        logger.info("Daily pipeline complete.")
    except Exception as exc:
        logger.error("Daily pipeline FAILED: %s", exc)
        raise


def start_scheduler():
    scheduler = BlockingScheduler(timezone="UTC")
    trigger = CronTrigger(hour=SYNC_HOUR, minute=SYNC_MINUTE)
    scheduler.add_job(daily_pipeline, trigger, id="daily_pipeline",
                      name="Daily Inventory Sync")
    logger.info("Scheduler started. Daily job at %02d:%02d UTC.", SYNC_HOUR, SYNC_MINUTE)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    start_scheduler()
