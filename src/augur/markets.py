# -*- coding: utf-8 -*-
"""
augur.markets - 市场注册表 / Market registry

Single source of truth for exchange-level metadata: which market a ticker
belongs to, and that market's currency, timezone, daily price band, lot size
and settlement cycle.

Why this module exists: the provider chain used to be market-blind, so a
Vietnamese ticker got exactly the US-shaped treatment AAPL gets -- same
provider order, same SEC EDGAR overlay, and a market cap denominated in VND
sitting in the same field as one denominated in USD. Every market-dependent
decision now routes through ``resolve_market`` instead of an ad-hoc
``if ticker in [...]`` at the call site.

Resolution is suffix-driven and deliberately conservative: a *bare* symbol
always resolves to US, exactly as it did before this module existed.
Vietnamese tickers are addressed in their Yahoo-compatible ``.VN`` form
(``VNM.VN``). That restraint is load-bearing -- several liquid VN symbols
collide with live US listings (``VNM`` is both Vinamilk on HOSE and the
Vanguard FTSE Vietnam ETF on NYSE Arca; ``PLX`` is a US listing too), so
inferring VN from a bare symbol would silently reroute tickers that users
already analyze today. ``VN_SYMBOLS`` is published so the UI can *suggest*
the ``.VN`` form, but it never drives resolution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class Market:
    """一个市场的机制性元数据（不含任何个股信息）。

    Mechanism only -- currency, session conventions, trading rules. Anything
    company-specific belongs in ``MarketContext``, not here.
    """

    code: str
    name: str
    currency: str
    timezone: str
    lot_size: int
    settlement: str
    #: Yahoo Finance ticker suffixes that identify this market. Empty for US
    #: (US symbols are unsuffixed, which is also why US is the fallback).
    yf_suffixes: Tuple[str, ...] = ()
    #: Daily price limit as a percentage. 0.0 means the market has no band.
    price_band_pct: float = 0.0
    #: Whether SEC EDGAR filings cover this market's issuers.
    has_edgar: bool = False
    notes: str = ""


US = Market(
    code="US",
    name="United States",
    currency="USD",
    timezone="America/New_York",
    lot_size=1,
    settlement="T+1",
    yf_suffixes=(),
    price_band_pct=0.0,
    has_edgar=True,
)

CN = Market(
    code="CN",
    name="China A-share",
    currency="CNY",
    timezone="Asia/Shanghai",
    lot_size=100,
    settlement="T+1",
    yf_suffixes=(".SS", ".SZ"),
    price_band_pct=10.0,
    has_edgar=False,
    notes="Main-board band is 10%; STAR/ChiNext are 20%.",
)

HK = Market(
    code="HK",
    name="Hong Kong",
    currency="HKD",
    timezone="Asia/Hong_Kong",
    lot_size=0,  # per-issuer board lot, not a market-wide constant
    settlement="T+2",
    yf_suffixes=(".HK",),
    price_band_pct=0.0,
    has_edgar=False,
)

VN = Market(
    code="VN",
    name="Vietnam",
    currency="VND",
    timezone="Asia/Ho_Chi_Minh",
    lot_size=100,
    settlement="T+2",
    yf_suffixes=(".VN",),
    price_band_pct=7.0,
    has_edgar=False,
    notes=(
        "Band is per board: HOSE 7%, HNX 10%, UPCoM 15%; 7% is carried here as "
        "the HOSE default. Sessions 09:00-11:30 and 13:00-14:45 ICT with ATO/ATC "
        "auctions. Foreign ownership room (default 49%, banks 30%) is a real "
        "per-ticker signal and is not modelled at market level."
    ),
)

MARKETS: Dict[str, Market] = {m.code: m for m in (US, CN, HK, VN)}

DEFAULT_MARKET = US

#: Suffix -> market, built from the table above so the two never drift apart.
_SUFFIX_TO_MARKET: Dict[str, Market] = {
    suffix: market
    for market in MARKETS.values()
    for suffix in market.yf_suffixes
}


#: Curated set of liquid HOSE/HNX symbols (VN30 plus frequently traded
#: mid-caps), in bare form. Used only to *suggest* the canonical ``.VN`` form
#: -- never to resolve a market. See the module docstring for why.
VN_SYMBOLS = frozenset({
    # VN30
    "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG",
    "MBB", "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSB", "SSI", "STB",
    "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE",
    # Other liquid names
    "BSR", "CTD", "DGC", "DIG", "DXG", "GEX", "HCM", "HSG", "KDH", "NKG",
    "NLG", "NVL", "PDR", "PNJ", "REE", "SBT", "VCG", "VCI", "VGC", "VND",
})


def resolve_market(ticker: str) -> Market:
    """把 ticker 解析到所属市场。

    Suffix wins; everything else is US. A bare symbol NEVER resolves to a
    non-US market, so this function cannot change how any ticker that works
    today is routed.

    >>> resolve_market("AAPL").code
    'US'
    >>> resolve_market("VNM.VN").currency
    'VND'
    >>> resolve_market("600519.SS").code
    'CN'
    """
    if not ticker:
        return DEFAULT_MARKET
    upper = ticker.strip().upper()
    for suffix, market in _SUFFIX_TO_MARKET.items():
        if upper.endswith(suffix):
            return market
    return DEFAULT_MARKET


def get_market(code: str) -> Market:
    """按市场代码取市场；未知代码回落到默认市场（US）。"""
    return MARKETS.get((code or "").strip().upper(), DEFAULT_MARKET)


def strip_market_suffix(ticker: str) -> str:
    """去掉 Yahoo 市场后缀，返回交易所本地代码。

    ``VNM.VN`` -> ``VNM``. Providers that speak the local exchange's own
    symbology (vnstock, TCBS) need the bare form; yfinance needs the suffix.
    """
    if not ticker:
        return ""
    upper = ticker.strip().upper()
    for suffix in _SUFFIX_TO_MARKET:
        if upper.endswith(suffix):
            return upper[: -len(suffix)]
    return upper


def suggest_vn_ticker(ticker: str) -> Optional[str]:
    """若 ticker 是已知越南代码的裸写法，返回规范的 ``.VN`` 形式，否则 None。

    For "did you mean VNM.VN?" prompts in search/UI. Returns None for a
    ticker that is already suffixed, so it is safe to call unconditionally.
    """
    if not ticker:
        return None
    upper = ticker.strip().upper()
    if "." in upper:
        return None
    return f"{upper}.VN" if upper in VN_SYMBOLS else None
