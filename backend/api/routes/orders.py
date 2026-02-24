from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["orders"])


def _parse_current_orders(raw_orders):
    """Parse raw current orders from lightweight API response."""
    orders = []
    for o in raw_orders:
        if isinstance(o, dict):
            orders.append({
                "betId": o.get("betId"),
                "marketId": o.get("marketId"),
                "selectionId": o.get("selectionId"),
                "side": o.get("side"),
                "price": o.get("priceSize", {}).get("price") if isinstance(o.get("priceSize"), dict) else o.get("price"),
                "size": o.get("priceSize", {}).get("size") if isinstance(o.get("priceSize"), dict) else o.get("size"),
                "sizeMatched": o.get("sizeMatched", 0),
                "sizeRemaining": o.get("sizeRemaining", 0),
                "status": o.get("status"),
                "placedDate": o.get("placedDate"),
                "matchedDate": o.get("matchedDate"),
            })
        else:
            price_size = getattr(o, "price_size", None)
            orders.append({
                "betId": getattr(o, "bet_id", None),
                "marketId": getattr(o, "market_id", None),
                "selectionId": getattr(o, "selection_id", None),
                "side": getattr(o, "side", None),
                "price": getattr(price_size, "price", None) if price_size else None,
                "size": getattr(price_size, "size", None) if price_size else None,
                "sizeMatched": getattr(o, "size_matched", 0),
                "sizeRemaining": getattr(o, "size_remaining", 0),
                "status": getattr(o, "status", None),
                "placedDate": str(getattr(o, "placed_date", "")),
                "matchedDate": str(getattr(o, "matched_date", "")),
            })
    return orders


def _enrich_with_catalogue(client, orders):
    """Enrich orders with event/runner names from market catalogue."""
    market_ids = list({o["marketId"] for o in orders if o.get("marketId")})
    if not market_ids:
        return orders

    # Build a lookup: (marketId, selectionId) -> {eventName, marketName, runnerName, scheduledTime}
    lookup = {}
    try:
        # Fetch in batches of 40 (API limit)
        for i in range(0, len(market_ids), 40):
            batch = market_ids[i:i + 40]
            catalogues = client.betting.list_market_catalogue(
                filter={"marketIds": batch},
                market_projection=["EVENT", "RUNNER_DESCRIPTION", "MARKET_START_TIME", "MARKET_DESCRIPTION"],
                max_results=str(len(batch)),
            )
            if isinstance(catalogues, list):
                for cat in catalogues:
                    if isinstance(cat, dict):
                        mid = cat.get("marketId", "")
                        event = cat.get("event", {})
                        event_name = event.get("name", "") if isinstance(event, dict) else ""
                        market_name = cat.get("marketName", "")
                        scheduled_time = cat.get("marketStartTime", "")
                        description = cat.get("description", {}) or {}
                        is_ew = bool(description.get("eachWayDivisor")) if isinstance(description, dict) else False
                        for runner in cat.get("runners", []):
                            if isinstance(runner, dict):
                                sid = runner.get("selectionId")
                                lookup[(mid, sid)] = {
                                    "eventName": event_name,
                                    "marketName": market_name,
                                    "runnerName": runner.get("runnerName", ""),
                                    "scheduledTime": scheduled_time,
                                    "isEachWay": is_ew,
                                }
                    else:
                        mid = getattr(cat, "market_id", "")
                        event = getattr(cat, "event", None)
                        event_name = getattr(event, "name", "") if event else ""
                        market_name = getattr(cat, "market_name", "")
                        scheduled_time = str(getattr(cat, "market_start_time", ""))
                        description = getattr(cat, "description", None)
                        is_ew = bool(getattr(description, "each_way_divisor", None)) if description else False
                        for runner in getattr(cat, "runners", []):
                            sid = getattr(runner, "selection_id", None)
                            lookup[(mid, sid)] = {
                                "eventName": event_name,
                                "marketName": market_name,
                                "runnerName": getattr(runner, "runner_name", ""),
                                "scheduledTime": scheduled_time,
                                "isEachWay": is_ew,
                            }
    except Exception as e:
        logger.warning(f"Failed to enrich orders with catalogue data: {e}")

    # Merge lookup into orders
    for order in orders:
        key = (order.get("marketId"), order.get("selectionId"))
        info = lookup.get(key, {})
        order["eventName"] = info.get("eventName", "")
        order["marketName"] = info.get("marketName", "")
        order["runnerName"] = info.get("runnerName", "")
        order["scheduledTime"] = info.get("scheduledTime", "")
        order["isEachWay"] = info.get("isEachWay", False)

    return orders


@router.get("/current")
async def get_current_orders(request: Request):
    """Get current open/matched orders from Betfair Exchange."""
    client = getattr(request.app.state, "betfair_client", None)
    if client is None:
        return JSONResponse(
            status_code=503,
            content={"detail": "Betfair client not available"},
        )

    try:
        result = client.betting.list_current_orders()

        if isinstance(result, dict):
            raw_orders = result.get("currentOrders", [])
        elif isinstance(result, list):
            raw_orders = result
        else:
            raw_orders = result.orders if hasattr(result, "orders") else []

        orders = _parse_current_orders(raw_orders)
        orders = _enrich_with_catalogue(client, orders)

        return {"orders": orders}

    except Exception as e:
        logger.error(f"Error fetching current orders: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Failed to fetch current orders: {str(e)}"},
        )


@router.get("/cleared")
async def get_cleared_orders(
    request: Request,
    settled_date: str = Query(None, description="Settled date in YYYY-MM-DD format (default: today UTC)"),
):
    """Get settled/cleared orders from Betfair Exchange with daily P/L."""
    client = getattr(request.app.state, "betfair_client", None)
    if client is None:
        return JSONResponse(
            status_code=503,
            content={"detail": "Betfair client not available"},
        )

    try:
        if settled_date:
            start = datetime.strptime(settled_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        else:
            now = datetime.now(timezone.utc)
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        end = start + timedelta(days=1)

        time_range = {
            "from": start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "to": end.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        }

        result = client.betting.list_cleared_orders(
            bet_status="SETTLED",
            settled_date_range=time_range,
            include_item_description=True,
        )

        if isinstance(result, dict):
            raw_orders = result.get("clearedOrders", [])
        elif isinstance(result, list):
            raw_orders = result
        else:
            raw_orders = result.orders if hasattr(result, "orders") else []

        orders = []
        total_profit = 0.0

        for o in raw_orders:
            if isinstance(o, dict):
                profit = float(o.get("profit", 0))
                item_desc = o.get("itemDescription", {}) or {}
                order = {
                    "betId": o.get("betId"),
                    "marketId": o.get("marketId"),
                    "selectionId": o.get("selectionId"),
                    "side": o.get("side"),
                    "priceMatched": o.get("priceMatched"),
                    "sizeSettled": o.get("sizeSettled"),
                    "profit": profit,
                    "placedDate": o.get("placedDate"),
                    "settledDate": o.get("settledDate"),
                    "marketName": item_desc.get("marketDesc", ""),
                    "eventName": item_desc.get("eventDesc", ""),
                    "runnerName": item_desc.get("runnerDesc", ""),
                    "isEachWay": bool(item_desc.get("eachWayDivisor")),
                }
            else:
                item_desc = getattr(o, "item_description", None)
                profit = float(getattr(o, "profit", 0))
                order = {
                    "betId": getattr(o, "bet_id", None),
                    "marketId": getattr(o, "market_id", None),
                    "selectionId": getattr(o, "selection_id", None),
                    "side": getattr(o, "side", None),
                    "priceMatched": getattr(o, "price_matched", None),
                    "sizeSettled": getattr(o, "size_settled", None),
                    "profit": profit,
                    "placedDate": str(getattr(o, "placed_date", "")),
                    "settledDate": str(getattr(o, "settled_date", "")),
                    "marketName": getattr(item_desc, "market_desc", "") if item_desc else "",
                    "eventName": getattr(item_desc, "event_desc", "") if item_desc else "",
                    "runnerName": getattr(item_desc, "runner_desc", "") if item_desc else "",
                    "isEachWay": bool(getattr(item_desc, "each_way_divisor", None)) if item_desc else False,
                }

            total_profit += profit
            orders.append(order)

        return {
            "orders": orders,
            "totalProfit": round(total_profit, 2),
            "settledDate": settled_date or start.strftime("%Y-%m-%d"),
        }

    except Exception as e:
        logger.error(f"Error fetching cleared orders: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Failed to fetch cleared orders: {str(e)}"},
        )
