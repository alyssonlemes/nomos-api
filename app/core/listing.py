from typing import Any, Optional

from sqlalchemy import asc, desc, nulls_last


def apply_listing_sort(
    query,
    *,
    columns: dict[str, Any],
    sort_by: Optional[str],
    sort_dir: Optional[str],
    default: str,
    tiebreaker: Any = None,
):
    """Ordena o queryset inteiro antes do skip/limit da paginação."""
    key = sort_by if sort_by in columns else default
    column = columns[key]
    descending = (sort_dir or "desc").lower() != "asc"
    order = desc if descending else asc

    try:
        primary = nulls_last(order(column))
    except Exception:
        primary = order(column)

    clauses = [primary]
    if tiebreaker is not None:
        clauses.append(order(tiebreaker))
    return query.order_by(*clauses)
