# -*- coding: utf-8 -*-
"""
Tests for the market registry (augur.markets).

覆盖:
  - resolve_market: 后缀解析 / 大小写 / 空值 / 未知后缀回落 US
  - 裸代码**绝不**解析到非 US 市场（保证既有 ticker 路由零变化）
  - strip_market_suffix: 交易所本地代码还原
  - suggest_vn_ticker: 仅对已知越南裸代码给出 .VN 建议
  - MARKETS 表自身的一致性（后缀不重叠、货币/时区必填）
"""

import pytest

from augur.markets import (
    DEFAULT_MARKET,
    MARKETS,
    VN_SYMBOLS,
    Market,
    get_market,
    resolve_market,
    strip_market_suffix,
    suggest_vn_ticker,
)


class TestResolveMarket:
    @pytest.mark.parametrize("ticker,code", [
        ("VNM.VN", "VN"),
        ("FPT.VN", "VN"),
        ("600519.SS", "CN"),
        ("000001.SZ", "CN"),
        ("0700.HK", "HK"),
        ("AAPL", "US"),
        ("BRK-B", "US"),
    ])
    def test_suffix_resolution(self, ticker, code):
        assert resolve_market(ticker).code == code

    @pytest.mark.parametrize("ticker", ["vnm.vn", "VnM.Vn", "  VNM.VN  "])
    def test_case_and_whitespace_insensitive(self, ticker):
        assert resolve_market(ticker).code == "VN"

    @pytest.mark.parametrize("ticker", ["", None])
    def test_empty_falls_back_to_default(self, ticker):
        assert resolve_market(ticker) is DEFAULT_MARKET

    def test_unknown_suffix_falls_back_to_us(self):
        assert resolve_market("FOO.XYZ").code == "US"

    def test_vn_market_metadata(self):
        vn = resolve_market("VNM.VN")
        assert vn.currency == "VND"
        assert vn.timezone == "Asia/Ho_Chi_Minh"
        assert vn.lot_size == 100
        assert vn.settlement == "T+2"
        assert vn.price_band_pct == 7.0
        assert vn.has_edgar is False

    def test_us_keeps_edgar(self):
        assert resolve_market("AAPL").has_edgar is True

    def test_only_us_has_edgar(self):
        assert [m.code for m in MARKETS.values() if m.has_edgar] == ["US"]


class TestBareSymbolsNeverLeaveUS:
    """裸代码路由必须与本模块引入前完全一致 —— 这是零回归的核心保证。

    Several VN symbols are live US listings (VNM is the Vanguard FTSE Vietnam
    ETF, PLX is a US listing), so inferring VN from a bare symbol would
    silently reroute tickers users already analyze.
    """

    @pytest.mark.parametrize("ticker", sorted(VN_SYMBOLS))
    def test_every_curated_vn_symbol_resolves_us_when_bare(self, ticker):
        assert resolve_market(ticker).code == "US"

    def test_vnm_bare_is_the_us_etf(self):
        assert resolve_market("VNM").currency == "USD"


class TestStripMarketSuffix:
    @pytest.mark.parametrize("ticker,bare", [
        ("VNM.VN", "VNM"),
        ("vnm.vn", "VNM"),
        ("600519.SS", "600519"),
        ("0700.HK", "0700"),
        ("AAPL", "AAPL"),
        ("", ""),
    ])
    def test_strip(self, ticker, bare):
        assert strip_market_suffix(ticker) == bare


class TestSuggestVnTicker:
    def test_known_bare_symbol_gets_suggestion(self):
        assert suggest_vn_ticker("VNM") == "VNM.VN"
        assert suggest_vn_ticker("fpt") == "FPT.VN"

    def test_unknown_symbol_gets_nothing(self):
        assert suggest_vn_ticker("AAPL") is None

    def test_already_suffixed_gets_nothing(self):
        assert suggest_vn_ticker("VNM.VN") is None

    def test_empty_gets_nothing(self):
        assert suggest_vn_ticker("") is None


class TestRegistryConsistency:
    def test_codes_match_keys(self):
        assert all(code == market.code for code, market in MARKETS.items())

    def test_every_market_has_currency_and_timezone(self):
        for market in MARKETS.values():
            assert market.currency, market.code
            assert market.timezone, market.code

    def test_suffixes_are_unique_across_markets(self):
        suffixes = [s for m in MARKETS.values() for s in m.yf_suffixes]
        assert len(suffixes) == len(set(suffixes))

    def test_us_is_the_unsuffixed_market(self):
        assert DEFAULT_MARKET.code == "US"
        assert DEFAULT_MARKET.yf_suffixes == ()

    def test_get_market_by_code(self):
        assert get_market("vn").code == "VN"
        assert get_market("nope") is DEFAULT_MARKET

    def test_market_is_frozen(self):
        with pytest.raises(Exception):
            resolve_market("AAPL").currency = "EUR"
