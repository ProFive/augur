"""Market data API routes — fetch, search, sparkline, overview widgets, sector performance.

Extracted from dashboard/app.py (router split R2).
Mounts via: app.include_router(market_router)
"""

import hashlib
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from augur.optional_deps import get_install_hint, is_available as _is_available

logger = logging.getLogger(__name__)

_HAS_AUGUR_DATA = _is_available("augur.data")

router = APIRouter()


def _safe_float(value) -> float:
    try:
        f = float(value)
        if f != f or f in (float("inf"), float("-inf")):
            return 0.0
        return f
    except (TypeError, ValueError):
        return 0.0


# ---- Ticker fetch / search / sparkline ----

@router.get("/api/fetch/{ticker}", summary="Fetch real-time market data for a ticker")
def api_fetch_ticker(ticker: str):
    """Fetch real-time market data for a ticker via yfinance.

    Synchronous def: fetch_market_context calls yfinance synchronously, async def will block the event loop.
    """
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(
            status_code=400,
            detail="Invalid ticker format. Use 1-15 alphanumeric characters, dots, or hyphens.",
        )
    if not _HAS_AUGUR_DATA:
        feature, install_cmd = get_install_hint("augur.data")
        raise HTTPException(
            status_code=501,
            detail=f"Package 'yfinance' is required for {feature} but is not installed. Install with: {install_cmd}"
        )
    try:
        from augur.data import fetch_market_context
        ctx = fetch_market_context(ticker)
        return {
            "status": "ok",
            "ticker": ctx.ticker,
            "source": "yfinance",
            "data": ctx.to_dict(),
        }
    except ImportError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch data: {e}")


@router.get("/api/search", summary="Search for tickers by name/symbol")
def api_search_tickers(q: str = ""):
    """Search for tickers by name/symbol.

    Synchronous def: search_ticker calls yfinance synchronously, async def will block the event loop.
    """
    if not q or len(q) < 1:
        return {"results": []}
    if len(q) > 64:
        raise HTTPException(status_code=400, detail="Search query too long (max 64 characters).")
    if any(ord(c) < 0x20 for c in q):
        raise HTTPException(status_code=400, detail="Search query contains invalid control characters.")
    if not _HAS_AUGUR_DATA:
        feature, install_cmd = get_install_hint("augur.data")
        raise HTTPException(
            status_code=501,
            detail=f"Package 'yfinance' is required for {feature} but is not installed. Install with: {install_cmd}"
        )
    try:
        from augur.data import search_ticker
        results = search_ticker(q)
        return {"status": "ok", "query": q, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


@router.get("/api/sparkline/{ticker}", summary="Get 7-day mini sparkline data for a ticker")
def api_sparkline(ticker: str):
    """Return last 7 trading days close prices for sparkline rendering. 

    synchronous def: fetch_history calls yfinance synchronously on cache miss, 
    async def will block the event loop - the homepage needs to render mini-charts of multiple targets concurrently at one time. 
    """
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format")
    try:
        from augur.data import fetch_history
        history = fetch_history(ticker, period="1mo")
        prices = [h["close"] for h in history[-7:]] if history else []
        trend = "flat"
        if len(prices) >= 2:
            trend = "up" if prices[-1] > prices[0] else "down" if prices[-1] < prices[0] else "flat"
        return {"status": "ok", "ticker": ticker.upper(), "prices": prices, "trend": trend}
    except Exception as e:
        return {"status": "error", "ticker": ticker.upper(), "prices": [], "trend": "flat", "error": str(e)}


# ---- Home dashboard market feeds ----

@router.get("/api/hot-tickers", summary="Real-time market data for hot tickers")
def api_hot_tickers(request: Request, refresh: bool = False):
    """Real-time market data for hot tickers: AAPL, NVDA, TSLA, MSFT, GOOGL, AMZN, BTC-USD, ETH-USD, META, AMD.

    Used by the "Hot Tickers" panel on the homepage. Gracefully degrades to an empty list if yfinance is not available.

    Synchronous def: fetch_hot_tickers will synchronously call yfinance if the cache is missed,
    declaring it as async def will block the event loop during that I/O operation.
    """
    try:
        if not _HAS_AUGUR_DATA:
            return {"status": "degraded", "tickers": [], "note": "yfinance 未安装，热门标的不可用。"}
        from augur.data import fetch_hot_tickers
        tickers = fetch_hot_tickers(force_refresh=refresh)
        data = {"status": "ok", "tickers": tickers}
        data_error = getattr(tickers, "data_error", None)
        if data_error:
            data["data_error"] = data_error
        data_source = getattr(tickers, "data_source", None)
        if data_source:
            data["data_source"] = data_source
        data_json = json.dumps(data, sort_keys=True, default=str)
        etag = hashlib.md5(data_json.encode()).hexdigest()
        if_none_match = request.headers.get("if-none-match")
        if if_none_match and if_none_match.strip('"') == etag:
            return JSONResponse(status_code=304, content=None, headers={"ETag": f'"{etag}"'})
        return JSONResponse(content=data, headers={"ETag": f'"{etag}"'})
    except Exception as e:
        logger.warning("hot tickers failed: %s", e)
        return {"status": "error", "tickers": [], "error": str(e)}


@router.get("/api/market-overview", summary="Global Market Overview")
def api_market_overview(request: Request, refresh: bool = False):
    """Snapshot of the global market: major indices, VIX, interest rates, commodities, and crypto real-time prices and changes.

    Used by the "Global Market Overview" panel on the homepage dashboard. Gracefully degrades to an empty list if yfinance is not available.

    Synchronous def: fetch_market_overview will synchronously call yfinance if the cache is missed,
    declaring it as async def will block the event loop during that I/O operation.
    """
    if not _HAS_AUGUR_DATA:
        return {
            "status": "degraded",
            "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "items": [],
            "source": "none",
            "note": "yfinance is not installed, global market overview is unavailable. Install: pip install 'augur-agents[data]'",
        }
    try:
        from augur.data import fetch_market_overview
        overview = fetch_market_overview(force_refresh=refresh)
        data = {"status": "ok", **overview}
        if overview.get("data_error"):
            data["status"] = "partial" if overview.get("items") else "degraded"
        data_json = json.dumps(data, sort_keys=True, default=str)
        etag = hashlib.md5(data_json.encode()).hexdigest()
        if_none_match = request.headers.get("if-none-match")
        if if_none_match and if_none_match.strip('"') == etag:
            return JSONResponse(status_code=304, content=None, headers={"ETag": f'"{etag}"'})
        return JSONResponse(content=data, headers={"ETag": f'"{etag}"'})
    except Exception as e:
        logger.warning("market overview failed: %s", e)
        return {
            "status": "degraded",
            "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "items": [],
            "source": "none",
            "note": f"Failed to fetch global market overview: {e}",
        }


@router.get("/api/market-movers", summary="Top Market Movers")
def api_market_movers():
    """Top 5 gainers and top 5 losers extracted from hot tickers data.

    Synchronous def: fetch_hot_tickers will synchronously call yfinance if the cache is missed,
    declaring it as async def will block the event loop during that I/O operation.
    """
    if not _HAS_AUGUR_DATA:
        return {"status": "degraded", "gainers": [], "losers": []}
    try:
        from augur.data import fetch_hot_tickers
        tickers = fetch_hot_tickers(force_refresh=False)
        if not tickers:
            return {"status": "degraded", "gainers": [], "losers": []}
        sorted_tickers = sorted(tickers, key=lambda t: t.get("change_pct", 0), reverse=True)
        gainers = sorted_tickers[:5]
        losers = sorted_tickers[-5:][::-1]
        return {"status": "ok", "gainers": gainers, "losers": losers}
    except Exception as e:
        logger.warning("market movers failed: %s", e)
        return {"status": "degraded", "gainers": [], "losers": [], "error": str(e)}


@router.get("/api/crypto-overview", summary="Crypto Overview")
def api_crypto_overview():
    """Fetch BTC, ETH, SOL, DOGE, XRP prices and 24h change from yfinance.

    Synchronous def: internally uses ThreadPoolExecutor + future.result(timeout) to fetch multiple tickers,
    declaring it as async def will still block the event loop during future.result(); by using def,
    Starlette will execute the entire function in a thread pool, leaving the event loop unaffected.
    """
    if not _HAS_AUGUR_DATA:
        return {"status": "degraded", "coins": []}

    CRYPTO_SYMBOLS = [
        ("BTC-USD", "Bitcoin"),
        ("ETH-USD", "Ethereum"),
        ("SOL-USD", "Solana"),
        ("DOGE-USD", "Dogecoin"),
        ("XRP-USD", "XRP"),
    ]

    try:
        yf = __import__("yfinance")
    except ImportError:
        return {"status": "degraded", "coins": []}

    def _fetch_crypto(entry):
        symbol, name = entry
        price = prev = market_cap = 0.0
        try:
            tk = yf.Ticker(symbol)
            fi = getattr(tk, "fast_info", None)
            if fi is not None:
                price = _safe_float(getattr(fi, "last_price", 0))
                prev = _safe_float(getattr(fi, "previous_close", 0))
                market_cap = _safe_float(getattr(fi, "market_cap", 0))
            if price <= 0 or prev <= 0:
                hist = tk.history(period="5d")
                if hist is not None and not hist.empty:
                    closes = [c for c in hist["Close"].tolist() if c and c == c]
                    if closes:
                        price = price or float(closes[-1])
                        prev = prev or (float(closes[-2]) if len(closes) >= 2 else float(closes[-1]))
        except Exception as exc:
            logger.debug("crypto fetch failed for %s: %s", symbol, exc)
        change_pct = ((price - prev) / prev) if prev else 0.0
        return {
            "symbol": symbol,
            "name": name,
            "price": round(price, 2),
            "change_pct": round(change_pct, 4),
            "market_cap": round(market_cap, 0),
        }

    coins = []
    try:
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(_fetch_crypto, entry): entry for entry in CRYPTO_SYMBOLS}
            for future in futures:
                try:
                    coins.append(future.result(timeout=10))
                except (FuturesTimeoutError, Exception) as exc:
                    entry = futures[future]
                    logger.debug("crypto timeout for %s: %s", entry[0], exc)
                    coins.append({"symbol": entry[0], "name": entry[1], "price": 0.0, "change_pct": 0.0, "market_cap": 0.0})
    except Exception as e:
        logger.warning("crypto overview failed: %s", e)
        return {"status": "degraded", "coins": []}

    return {"status": "ok", "coins": coins}


@router.get("/api/commodities", summary="Commodities Overview")
def api_commodities():
    """Fetch Gold, Silver, Oil (WTI), and Natural Gas prices and changes from yfinance."""
    if not _HAS_AUGUR_DATA:
        return {"status": "degraded", "commodities": []}

    COMMODITY_SYMBOLS = [
        ("GC=F", "Gold"),
        ("SI=F", "Silver"),
        ("CL=F", "Oil WTI"),
        ("NG=F", "Natural Gas"),
    ]

    try:
        yf = __import__("yfinance")
    except ImportError:
        return {"status": "degraded", "commodities": []}

    def _fetch_commodity(entry):
        symbol, name = entry
        price = prev = 0.0
        try:
            tk = yf.Ticker(symbol)
            fi = getattr(tk, "fast_info", None)
            if fi is not None:
                price = _safe_float(getattr(fi, "last_price", 0))
                prev = _safe_float(getattr(fi, "previous_close", 0))
            if price <= 0 or prev <= 0:
                hist = tk.history(period="5d")
                if hist is not None and not hist.empty:
                    closes = [c for c in hist["Close"].tolist() if c and c == c]
                    if closes:
                        price = price or float(closes[-1])
                        prev = prev or (float(closes[-2]) if len(closes) >= 2 else float(closes[-1]))
        except Exception as exc:
            logger.debug("commodity fetch failed for %s: %s", symbol, exc)
        change_pct = ((price - prev) / prev) if prev else 0.0
        return {"symbol": symbol, "name": name, "price": round(price, 2), "change_pct": round(change_pct, 4)}

    commodities = []
    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(_fetch_commodity, entry): entry for entry in COMMODITY_SYMBOLS}
            for future in futures:
                try:
                    commodities.append(future.result(timeout=10))
                except (FuturesTimeoutError, Exception) as exc:
                    entry = futures[future]
                    logger.debug("commodity timeout for %s: %s", entry[0], exc)
                    commodities.append({"symbol": entry[0], "name": entry[1], "price": 0.0, "change_pct": 0.0})
    except Exception as e:
        logger.warning("commodities fetch failed: %s", e)
        return {"status": "degraded", "commodities": []}

    return {"status": "ok", "commodities": commodities}


@router.get("/api/treasury-rates", summary="US Treasury Rates")
def api_treasury_rates():
    """Fetch US 2Y, 5Y, 10Y, and 30Y treasury yields from yfinance."""
    if not _HAS_AUGUR_DATA:
        return {"status": "degraded", "rates": []}

    TREASURY_SYMBOLS = [
        ("^IRX", "2Y", "US 2-Year"),
        ("^FVX", "5Y", "US 5-Year"),
        ("^TNX", "10Y", "US 10-Year"),
        ("^TYX", "30Y", "US 30-Year"),
    ]

    try:
        yf = __import__("yfinance")
    except ImportError:
        return {"status": "degraded", "rates": []}

    def _fetch_rate(entry):
        symbol, maturity, name = entry
        yield_pct = 0.0
        try:
            tk = yf.Ticker(symbol)
            fi = getattr(tk, "fast_info", None)
            if fi is not None:
                yield_pct = _safe_float(getattr(fi, "last_price", 0))
            if yield_pct <= 0:
                hist = tk.history(period="5d")
                if hist is not None and not hist.empty:
                    closes = [c for c in hist["Close"].tolist() if c and c == c]
                    if closes:
                        yield_pct = float(closes[-1])
        except Exception as exc:
            logger.debug("treasury rate fetch failed for %s: %s", symbol, exc)
        return {"maturity": maturity, "symbol": symbol, "name": name, "yield_pct": round(yield_pct, 3)}

    rates = []
    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(_fetch_rate, entry): entry for entry in TREASURY_SYMBOLS}
            for future in futures:
                try:
                    rates.append(future.result(timeout=10))
                except (FuturesTimeoutError, Exception) as exc:
                    entry = futures[future]
                    logger.debug("treasury rate timeout for %s: %s", entry[0], exc)
                    rates.append({"maturity": entry[1], "symbol": entry[0], "name": entry[2], "yield_pct": 0.0})
    except Exception as e:
        logger.warning("treasury rates fetch failed: %s", e)
        return {"status": "degraded", "rates": []}

    return {"status": "ok", "rates": rates}


@router.get("/api/fear-greed", summary="Fear & Greed Index")
def api_fear_greed():
    """Calculate the Fear & Greed Index (0-100) based on the VIX.

    Formula: index = max(0, min(100, 100 - ((VIX - 12) / 38) * 100))
    0-25: Extreme Fear, 25-45: Fear, 45-55: Neutral, 55-75: Greed, 75-100: Extreme Greed

    Synchronous def: fetch_market_overview will synchronously call yfinance if the cache is missed,
    declaring it as async def will block the event loop during that I/O operation.
    """
    if not _HAS_AUGUR_DATA:
        return {
            "status": "degraded",
            "index": 50,
            "label": "Neutral",
            "vix_value": 0.0,
            "description": "yfinance is not installed, unable to calculate the real-time Fear & Greed Index",
        }
    try:
        from augur.data import fetch_market_overview
        overview = fetch_market_overview(force_refresh=False)
        items = overview.get("items", [])
        vix_item = next((it for it in items if it.get("key") == "vix"), None)
        if not vix_item or not vix_item.get("price"):
            return {"status": "degraded", "index": 50, "label": "Neutral", "vix_value": 0.0, "description": "VIX data temporarily unavailable"}
        vix_val = float(vix_item["price"])
        index = max(0, min(100, int(100 - ((vix_val - 12) / 38) * 100)))
        if index >= 75:
            label, desc = "Extreme Greed", f"VIX={vix_val:.2f}, the market is in extreme greed, volatility is very low"
        elif index >= 55:
            label, desc = "Greed", f"VIX={vix_val:.2f}, the market is leaning towards greed, investor sentiment is optimistic"
        elif index >= 45:
            label, desc = "Neutral", f"VIX={vix_val:.2f}, the market sentiment is neutral, investors are cautious"
        elif index >= 25:
            label, desc = "Fear", f"VIX={vix_val:.2f}, the market is leaning towards fear, investors are cautious"
        else:
            label, desc = "Extreme Fear", f"VIX={vix_val:.2f}, the market is in extreme fear, volatility is very high"
        return {"status": "ok", "index": index, "label": label, "vix_value": vix_val, "description": desc}
    except Exception as e:
        logger.warning("fear-greed calc failed: %s", e)
        return {"status": "degraded", "index": 50, "label": "Neutral", "vix_value": 0.0, "description": f"Fear & Greed Index calculation failed: {e}"}


@router.get("/api/datasources", summary="Data source status")
async def api_datasources():
    """Return the currently available data source chains (for UI display of data source coverage)."""
    try:
        from augur.datasources import available_sources
        sources = available_sources()
    except Exception:
        sources = ["yfinance", "stooq"]
    catalog = {
        "yfinance": {"label": "Yahoo Finance", "needs_key": False, "coverage": "Market data + Fundamentals + Technical indicators", "active": "yfinance" in sources},
        "finnhub": {"label": "Finnhub", "needs_key": True, "coverage": "Fundamentals + Analyst ratings", "active": "finnhub" in sources, "env": "FINNHUB_API_KEY"},
        "alphavantage": {"label": "Alpha Vantage", "needs_key": True, "coverage": "Fundamentals OVERVIEW", "active": "alphavantage" in sources, "env": "ALPHAVANTAGE_API_KEY"},
        "stooq": {"label": "Stooq", "needs_key": False, "coverage": "Market data fallback (CSV)", "active": "stooq" in sources},
    }
    return {"status": "ok", "active_chain": sources, "catalog": catalog}


@router.get("/api/sector-performance", summary="Sector performance for major ETFs")
def api_sector_performance(request: Request, refresh: bool = False):
    """Sector ETF performance: XLK, XLV, XLF, XLE, XLY, XLP, XLI, XLU.

    Used for the "Sector Performance" panel on the homepage. Gracefully degrades to an empty list if yfinance is not available.

    Synchronous def (not async def): Starlette will automatically run it in a thread pool,
    so it won't block the event loop. Internally uses ThreadPoolExecutor to fetch 11 ETFs in parallel,
    each with a maximum wait time of 10 seconds to avoid a single ETF slowing down the overall response.
    """
    if not _HAS_AUGUR_DATA:
        return {"status": "degraded", "sectors": [], "note": "yfinance is not installed, sector performance is unavailable."}

    sector_etfs = [
        ("XLK", "科技", "Technology"),
        ("XLV", "医疗", "Healthcare"),
        ("XLF", "金融", "Financials"),
        ("XLE", "能源", "Energy"),
        ("XLY", "可选消费", "Consumer Disc."),
        ("XLP", "必需消费", "Consumer Staples"),
        ("XLI", "工业", "Industrials"),
        ("XLU", "公用事业", "Utilities"),
        ("XLRE", "房地产", "Real Estate"),
        ("XLB", "材料", "Materials"),
        ("XLC", "通信", "Communication"),
    ]

    try:
        import yfinance as yf

        def _fetch_sector(entry):
            symbol, cn_name, en_name = entry
            price = prev = 0.0
            try:
                tk = yf.Ticker(symbol)
                fi = getattr(tk, "fast_info", None)
                if fi is not None:
                    price = float(getattr(fi, "last_price", 0) or 0)
                    prev = float(getattr(fi, "previous_close", 0) or 0)
                if price <= 0 or prev <= 0:
                    hist = tk.history(period="5d")
                    if hist is not None and not hist.empty:
                        closes = [c for c in hist["Close"].tolist() if c and c == c]
                        if closes:
                            price = price or float(closes[-1])
                            prev = prev or (float(closes[-2]) if len(closes) >= 2 else float(closes[-1]))
            except Exception as exc:
                logger.debug("sector fetch failed for %s: %s", symbol, exc)
            change_pct = ((price - prev) / prev) if prev else 0.0
            return {
                "symbol": symbol,
                "name": cn_name,
                "en_name": en_name,
                "price": round(price, 2),
                "change_pct": round(change_pct, 4),
            }

        sectors = []
        with ThreadPoolExecutor(max_workers=len(sector_etfs)) as executor:
            futures = {executor.submit(_fetch_sector, entry): entry for entry in sector_etfs}
            for future in futures:
                try:
                    sectors.append(future.result(timeout=10))
                except (FuturesTimeoutError, Exception) as exc:
                    symbol, cn_name, en_name = futures[future]
                    logger.debug("sector timeout for %s: %s", symbol, exc)
                    sectors.append({"symbol": symbol, "name": cn_name, "en_name": en_name, "price": 0, "change_pct": 0})

        data = {
            "status": "ok",
            "sectors": sectors,
            "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        data_json = json.dumps(data, sort_keys=True, default=str)
        etag = hashlib.md5(data_json.encode()).hexdigest()
        if_none_match = request.headers.get("if-none-match")
        if if_none_match and if_none_match.strip('"') == etag:
            return JSONResponse(status_code=304, content=None, headers={"ETag": f'"{etag}"'})
        return JSONResponse(content=data, headers={"ETag": f'"{etag}"'})
    except ImportError:
        return {"status": "degraded", "sectors": [], "note": "yfinance is not installed; sector market data is unavailable."}
    except Exception as e:
        logger.warning("sector performance failed: %s", e)
        return {"status": "degraded", "sectors": [], "note": f"Failed to fetch sector market data: {e}"}
