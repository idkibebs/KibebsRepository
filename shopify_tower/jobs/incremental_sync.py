"""
Incremental sync job: pull only records updated since last successful run.
Designed to run daily.
"""
import logging
from datetime import datetime, timedelta, timezone

from db.database import db_conn, start_pipeline_run, finish_pipeline_run
from shopify.client import ShopifyClient
from shopify.sync_products import sync_products, sync_inventory
from shopify.sync_orders import sync_orders

logger = logging.getLogger(__name__)


def _last_successful_sync(run_type_prefix: str) -> str | None:
    """Return ISO timestamp of last successful run of the given type, or None."""
    with db_conn() as conn:
        row = conn.execute(
            """SELECT started_at FROM pipeline_runs
               WHERE run_type LIKE ? AND status='success'
               ORDER BY started_at DESC LIMIT 1""",
            (f"{run_type_prefix}%",),
        ).fetchone()
    if row:
        return row["started_at"]
    return None


def run_incremental_sync():
    logger.info("Starting INCREMENTAL SYNC...")
    run_id = start_pipeline_run("incremental_sync")
    total = 0

    try:
        client = ShopifyClient()

        # ── Products: use last sync timestamp or 24h ago as fallback ─────────
        last_product_sync = _last_successful_sync("full_sync") or \
                            _last_successful_sync("incremental_sync")
        if not last_product_sync:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        else:
            cutoff = last_product_sync

        logger.info("Step 1/3 — Syncing products updated since %s", cutoff)
        total += sync_products(client, updated_at_min=cutoff)

        logger.info("Step 2/3 — Refreshing all inventory levels...")
        total += sync_inventory(client)  # inventory levels: always full refresh

        # ── Orders: use last 24h ──────────────────────────────────────────────
        orders_cutoff = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        logger.info("Step 3/3 — Syncing orders since %s", orders_cutoff)
        total += sync_orders(client, created_at_min=orders_cutoff)

        finish_pipeline_run(run_id, "success", total)
        logger.info("Incremental sync complete. %d records updated.", total)

    except Exception as exc:
        finish_pipeline_run(run_id, "error", total, notes=str(exc))
        logger.error("Incremental sync FAILED: %s", exc)
        raise


if __name__ == "__main__":
    run_incremental_sync()
