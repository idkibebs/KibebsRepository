"""
Sync products, variants, and inventory levels from Shopify into SQLite.
Supports both full sync and incremental sync (updated_at_min filter).
"""
import logging
from datetime import datetime, timezone

from shopify.client import ShopifyClient
from db.database import db_conn

logger = logging.getLogger(__name__)


# ── Data cleaning helpers ─────────────────────────────────────────────────────

def _clean_price(value) -> float:
    """Convert Shopify price string ('9.99') to float, 0.0 on failure."""
    try:
        return float(str(value).replace(",", "").replace("$", "").strip())
    except (TypeError, ValueError):
        return 0.0


def _parse_dt(value: str) -> str | None:
    """Return ISO datetime string or None."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Upsert helpers ────────────────────────────────────────────────────────────

def _upsert_variant(conn, variant: dict, product_title: str, product_id: str):
    conn.execute(
        """INSERT INTO variants
               (id, product_id, sku, title, product_title, price, created_at, updated_at, synced_at)
           VALUES (?,?,?,?,?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET
               sku=excluded.sku, title=excluded.title,
               product_title=excluded.product_title, price=excluded.price,
               updated_at=excluded.updated_at, synced_at=excluded.synced_at""",
        (
            str(variant["id"]),
            product_id,
            variant.get("sku") or "",
            variant.get("title", ""),
            product_title,
            _clean_price(variant.get("price", 0)),
            _parse_dt(variant.get("created_at")),
            _parse_dt(variant.get("updated_at")),
            _now(),
        ),
    )


def _upsert_inventory_level(conn, level: dict, location_name: str):
    conn.execute(
        """INSERT INTO inventory_levels
               (variant_id, location_id, location_name, available, updated_at, synced_at)
           VALUES (?,?,?,?,?,?)
           ON CONFLICT(variant_id, location_id) DO UPDATE SET
               location_name=excluded.location_name,
               available=excluded.available,
               updated_at=excluded.updated_at,
               synced_at=excluded.synced_at""",
        (
            str(level["inventory_item_id"]),  # Note: mapped via inventory_item_id
            str(level["location_id"]),
            location_name,
            int(level.get("available") or 0),
            _parse_dt(level.get("updated_at")),
            _now(),
        ),
    )


# ── Public sync functions ─────────────────────────────────────────────────────

def sync_products(client: ShopifyClient, updated_at_min: str = None) -> int:
    """
    Pull all products/variants from Shopify and upsert into DB.
    Pass updated_at_min (ISO string) for incremental sync.
    Returns count of variants synced.
    """
    params = {}
    if updated_at_min:
        params["updated_at_min"] = updated_at_min

    total = 0
    for page in client.get_products(params=params):
        with db_conn() as conn:
            for product in page:
                product_id = str(product["id"])
                product_title = product.get("title", "")
                for variant in product.get("variants", []):
                    _upsert_variant(conn, variant, product_title, product_id)
                    total += 1
        logger.info("Products sync: %d variants upserted so far", total)

    logger.info("Products sync complete. Total variants: %d", total)
    return total


def sync_inventory(client: ShopifyClient) -> int:
    """
    Pull inventory levels for every location and upsert into DB.
    Maps inventory_item_id → variant_id via variants table.
    Returns count of inventory levels synced.
    """
    locations = client.get_locations()
    if not locations:
        logger.warning("No locations found in Shopify account.")
        return 0

    logger.info("Found %d location(s): %s",
                len(locations), [l["name"] for l in locations])

    # Build a map: inventory_item_id → variant_id from our DB
    item_to_variant = _build_inventory_item_map(client)

    total = 0
    for location in locations:
        loc_id = str(location["id"])
        loc_name = location.get("name", loc_id)
        for page in client.get_inventory_levels(loc_id):
            with db_conn() as conn:
                for level in page:
                    inv_item_id = str(level.get("inventory_item_id", ""))
                    # Remap to variant_id
                    level["inventory_item_id"] = item_to_variant.get(inv_item_id, inv_item_id)
                    _upsert_inventory_level(conn, level, loc_name)
                    total += 1
        logger.info("Location '%s': %d inventory levels synced", loc_name, total)

    logger.info("Inventory sync complete. Total records: %d", total)
    return total


def _build_inventory_item_map(client: ShopifyClient) -> dict:
    """
    Shopify inventory_levels use inventory_item_id, not variant_id.
    Fetch variants and build the mapping inventory_item_id → variant_id.
    """
    mapping = {}
    for page in client.get_products():
        for product in page:
            for variant in product.get("variants", []):
                inv_item_id = str(variant.get("inventory_item_id", ""))
                var_id = str(variant["id"])
                if inv_item_id:
                    mapping[inv_item_id] = var_id
    return mapping
