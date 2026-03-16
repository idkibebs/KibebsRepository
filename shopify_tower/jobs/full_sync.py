"""
Full sync job: pull everything from Shopify from scratch.
Run this once on first setup, or to force a complete refresh.
"""
import logging
import sys

from db.database import init_db, start_pipeline_run, finish_pipeline_run
from shopify.client import ShopifyClient
from shopify.sync_products import sync_products, sync_inventory
from shopify.sync_orders import sync_orders

logger = logging.getLogger(__name__)


def run_full_sync():
    logger.info("Starting FULL SYNC...")
    run_id = start_pipeline_run("full_sync")
    total = 0

    try:
        init_db()
        client = ShopifyClient()

        logger.info("Step 1/3 — Syncing products & variants...")
        total += sync_products(client)

        logger.info("Step 2/3 — Syncing inventory levels...")
        total += sync_inventory(client)

        logger.info("Step 3/3 — Syncing orders...")
        total += sync_orders(client)

        finish_pipeline_run(run_id, "success", total)
        logger.info("Full sync complete. %d total records.", total)

    except Exception as exc:
        finish_pipeline_run(run_id, "error", total, notes=str(exc))
        logger.error("Full sync FAILED: %s", exc)
        raise


if __name__ == "__main__":
    run_full_sync()
