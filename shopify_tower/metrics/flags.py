"""
Filter helpers to extract flag-based subsets from a metrics list.
"""
from metrics.compute import compute_metrics


def get_low_stock(metrics: list[dict] = None) -> list[dict]:
    """Return variants flagged as Low or Critical, sorted by days_of_stock asc."""
    m = metrics or compute_metrics()
    subset = [r for r in m if r["flag"] in ("Low", "Critical")]
    return sorted(subset, key=lambda x: x["days_of_stock"])


def get_reorder_list(metrics: list[dict] = None) -> list[dict]:
    """Return variants that need reordering (reorder_qty > 0), sorted by urgency."""
    m = metrics or compute_metrics()
    subset = [r for r in m if r["reorder_qty"] > 0]
    return sorted(subset, key=lambda x: x["days_of_stock"])


def get_dead_stock(metrics: list[dict] = None) -> list[dict]:
    """Return variants flagged as Dead Stock, sorted by total_available desc."""
    m = metrics or compute_metrics()
    subset = [r for r in m if r["flag"] == "Dead Stock"]
    return sorted(subset, key=lambda x: x["total_available"], reverse=True)
