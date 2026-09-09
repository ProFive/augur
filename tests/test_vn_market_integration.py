# -*- coding: utf-8 -*-
"""
End-to-end wiring tests for Vietnam market support.

不触网：provider 链全部注入桩件。验证的是**接线**而非某个数据源的字段映射——
后者由 tests/test_vnstock_provider.py 覆盖。

核心保证:
  - 越南 ticker 走越南链，US/CN 链一字未改
  - currency 一路传到 MarketContext
  - EDGAR overlay 对非美国市场不执行
  - 未安装 vnstock 时越南 ticker 依然可用（回落 yfinance .VN）
"""

import pytest

from augur import data as data_mod
from augur.datasources import default_providers
from augur.datasources.base import DataProvider


@pytest.fixture(autouse=True)
def _clean_caches():
    data_mod.clear_cache()
    data_mod.reset_providers_cache()
    yield
    data_mod.clear_cache()
    data_mod.reset_providers_cache()


class _StubProvider(DataProvider):
    def __init__(self, name, payload):
        self.name = name
        self._payload = payload
        self.seen = []

    def fetch(self, ticker):
        self.seen.append(ticker)
        return dict(self._payload)


class TestChainSelection:
    def test_vn_and_default_chains_are_cached_separately(self, monkeypatch):
        us = _StubProvider("us-stub", {"price": 1.0})
        vn = _StubProvider("vn-stub", {"price": 2.0, "currency": "VND"})
        monkeypatch.setattr(data_mod, "_providers_cache", [us])
        monkeypatch.setitem(data_mod._market_providers_cache, "VN", [vn])

        assert data_mod._get_providers("US") == [us]
        assert data_mod._get_providers("VN") == [vn]

    def test_unknown_market_uses_default_chain(self, monkeypatch):
        us = _StubProvider("us-stub", {"price": 1.0})
        monkeypatch.setattr(data_mod, "_providers_cache", [us])
        assert data_mod._get_providers("ZZ") == [us]
        assert data_mod._get_providers() == [us]

    def test_reset_clears_both_caches(self):
        data_mod._market_providers_cache["VN"] = ["x"]
        data_mod._providers_cache = ["y"]
        data_mod.reset_providers_cache()
        assert data_mod._providers_cache is None
        assert data_mod._market_providers_cache == {}

    def test_vn_chain_puts_vnstock_first_when_installed(self, monkeypatch):
        from augur.datasources import vnstock_provider

        monkeypatch.setattr(vnstock_provider.VNStockProvider, "is_configured",
                            staticmethod(lambda: True))
        assert [p.name for p in default_providers("VN")][0] == "vnstock"

    def test_vn_chain_degrades_to_yfinance_without_vnstock(self, monkeypatch):
        from augur.datasources import vnstock_provider

        monkeypatch.setattr(vnstock_provider.VNStockProvider, "is_configured",
                            staticmethod(lambda: False))
        names = [p.name for p in default_providers("VN")]
        assert "vnstock" not in names
        assert names == [p.name for p in default_providers("US")]

    def test_non_vn_markets_never_get_vnstock(self, monkeypatch):
        from augur.datasources import vnstock_provider

        monkeypatch.setattr(vnstock_provider.VNStockProvider, "is_configured",
                            staticmethod(lambda: True))
        for market in ("US", "CN", "HK"):
            assert "vnstock" not in [p.name for p in default_providers(market)]


class TestContextBuilding:
    def test_vn_ticker_uses_vn_chain(self, monkeypatch):
        us = _StubProvider("us-stub", {"price": 1.0})
        vn = _StubProvider("vn-stub", {"price": 62000.0, "currency": "VND"})
        monkeypatch.setattr(data_mod, "_providers_cache", [us])
        monkeypatch.setitem(data_mod._market_providers_cache, "VN", [vn])

        ctx = data_mod._build_context_from_providers("VNM.VN")
        assert vn.seen == ["VNM.VN"]
        assert us.seen == []
        assert ctx.price == 62000.0
        assert ctx.currency == "VND"

    def test_us_ticker_still_uses_default_chain(self, monkeypatch):
        us = _StubProvider("us-stub", {"price": 1.0})
        vn = _StubProvider("vn-stub", {"price": 2.0})
        monkeypatch.setattr(data_mod, "_providers_cache", [us])
        monkeypatch.setitem(data_mod._market_providers_cache, "VN", [vn])

        ctx = data_mod._build_context_from_providers("AAPL")
        assert us.seen == ["AAPL"] and vn.seen == []
        assert ctx.price == 1.0

    def test_currency_backfilled_from_registry_when_provider_omits_it(self, monkeypatch):
        # yfinance .VN 偶尔不返回 currency —— 留空比补齐更危险。
        monkeypatch.setitem(data_mod._market_providers_cache, "VN",
                            [_StubProvider("thin", {"price": 100.0})])
        assert data_mod._build_context_from_providers("VNM.VN").currency == "VND"

    def test_provider_currency_wins_over_registry(self, monkeypatch):
        monkeypatch.setitem(data_mod._market_providers_cache, "VN",
                            [_StubProvider("odd", {"price": 1.0, "currency": "USD"})])
        assert data_mod._build_context_from_providers("VNM.VN").currency == "USD"

    def test_total_failure_still_carries_currency(self, monkeypatch):
        class _Dead(DataProvider):
            name = "dead"

            def fetch(self, ticker):
                raise RuntimeError("down")

        monkeypatch.setitem(data_mod._market_providers_cache, "VN", [_Dead()])
        ctx = data_mod._build_context_from_providers("VNM.VN")
        assert getattr(ctx, "data_source") == "none"
        assert ctx.currency == "VND"

    def test_us_context_currency_unchanged_when_provider_supplies_it(self, monkeypatch):
        monkeypatch.setattr(data_mod, "_providers_cache",
                            [_StubProvider("s", {"price": 1.0, "currency": "USD"})])
        assert data_mod._build_context_from_providers("AAPL").currency == "USD"


class TestEdgarSkipping:
    def _ctx(self, ticker):
        from augur.personas.base import MarketContext

        ctx = MarketContext(ticker=ticker)
        ctx.price = 100.0
        return ctx

    def test_edgar_skipped_for_vn(self, monkeypatch):
        called = []
        monkeypatch.setattr(
            "augur.consensus.edgar_fundamentals.fetch_edgar_fundamentals",
            lambda *a, **kw: called.append(a) or {},
        )
        data_mod._overlay_edgar_fundamentals(self._ctx("VNM.VN"))
        assert called == []

    @pytest.mark.parametrize("ticker", ["600519.SS", "0700.HK"])
    def test_edgar_skipped_for_other_non_us_markets(self, monkeypatch, ticker):
        called = []
        monkeypatch.setattr(
            "augur.consensus.edgar_fundamentals.fetch_edgar_fundamentals",
            lambda *a, **kw: called.append(a) or {},
        )
        data_mod._overlay_edgar_fundamentals(self._ctx(ticker))
        assert called == []

    def test_edgar_still_runs_for_us(self, monkeypatch):
        called = []
        monkeypatch.setattr(
            "augur.consensus.edgar_fundamentals.fetch_edgar_fundamentals",
            lambda *a, **kw: (called.append(a), {"insufficient": True})[1],
        )
        data_mod._overlay_edgar_fundamentals(self._ctx("AAPL"))
        assert len(called) == 1


class TestMarketOverview:
    def test_vn_index_is_listed(self):
        import inspect

        src = inspect.getsource(data_mod.fetch_market_overview)
        assert '"vnindex"' in src and "^VNINDEX" in src
