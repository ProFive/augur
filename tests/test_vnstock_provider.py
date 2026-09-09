# -*- coding: utf-8 -*-
"""
Tests for VNStockProvider (越南市场数据源).

网络与 vnstock 完全 mock —— 这些用例在未安装 vnstock 的机器上也必须通过，
因为 vnstock 是可选依赖。

覆盖:
  - 正常路径：字段映射、单位、currency="VND"
  - 列名漂移：多候选名匹配（vnstock 上游改列名是常态）
  - 各类失败：未安装 / 客户端初始化失败 / 无价格 / 单接口异常
  - 失败一律抛 DataProviderError 以触发 yfinance 兜底，绝不崩溃
"""

import pytest

from augur.datasources.base import DataProviderError
from augur.datasources.vnstock_provider import VNStockProvider, _pick, _rows


class _Frame:
    """最小的 DataFrame 替身：有 columns 和 to_dict(orient=...)。"""

    def __init__(self, records, columns=None):
        self._records = records
        self.columns = columns if columns is not None else list(records[0].keys()) if records else []

    def to_dict(self, orient="records"):
        return list(self._records)


class _Trading:
    def __init__(self, board):
        self._board = board

    def price_board(self, symbols):
        return self._board


class _Quote:
    def __init__(self, hist):
        self._hist = hist

    def history(self, start=None, end=None, interval=None):
        return self._hist


class _Finance:
    def __init__(self, ratios):
        self._ratios = ratios

    def ratio(self, period=None, lang=None):
        return self._ratios


class _Company:
    def __init__(self, overview):
        self._overview = overview

    def overview(self):
        return self._overview


class _Client:
    def __init__(self, board=None, hist=None, ratios=None, overview=None):
        self.trading = _Trading(board)
        self.quote = _Quote(hist)
        self.finance = _Finance(ratios)
        self.company = _Company(overview)


def _closes(values):
    return _Frame([{"close": v} for v in values])


def _provider(client):
    return VNStockProvider(client_factory=lambda symbol: client)


@pytest.fixture
def full_client():
    board = _Frame([{
        "match_price": 62000.0,
        "ref_price": 60000.0,
        "open_price": 60500.0,
        "highest_price": 62500.0,
        "lowest_price": 60200.0,
        "accumulated_volume": 1_500_000,
        "foreign_room": 41.5,
    }])
    ratios = _Frame([{
        "pe": 15.2,
        "pb": 2.4,
        "roe": 0.21,
        "roa": 0.11,
        "eps": 4100.0,
        "gross_profit_margin": 0.40,
        "post_tax_margin": 0.17,
        "revenue_growth": 0.08,
        "debt_on_equity": 0.5,
        "market_cap": 130_000_000_000_000.0,   # 130,000 tỷ VND
        "revenue": 60_000_000_000_000.0,
        "dividend_yield": 0.04,
    }])
    overview = _Frame([{
        "company_name": "Vietnam Dairy Products JSC",
        "icb_name2": "Food & Beverage",
        "icb_name3": "Food Producers",
        "exchange": "HOSE",
        "company_profile": "Vinamilk is Vietnam's largest dairy producer.",
    }])
    return _Client(board=board, hist=_closes([58000, 59000, 60000, 61000, 62000]),
                   ratios=ratios, overview=overview)


class TestHappyPath:
    def test_currency_is_vnd(self, full_client):
        assert _provider(full_client).fetch("VNM.VN")["currency"] == "VND"

    def test_data_source_tagged(self, full_client):
        assert _provider(full_client).fetch("VNM.VN")["data_source"] == "vnstock"

    def test_price_and_change(self, full_client):
        out = _provider(full_client).fetch("VNM.VN")
        assert out["price"] == 62000.0
        assert out["change_pct"] == pytest.approx((62000 / 60000 - 1) * 100)

    def test_fundamentals_mapped(self, full_client):
        out = _provider(full_client).fetch("VNM.VN")
        assert out["pe"] == 15.2
        assert out["pb"] == 2.4
        assert out["roe"] == 0.21
        assert out["eps"] == 4100.0

    def test_debt_to_equity_converted_to_debt_ratio(self, full_client):
        # D/E 0.5 -> D/A = 0.5 / 1.5
        assert _provider(full_client).fetch("VNM.VN")["debt_ratio"] == pytest.approx(1 / 3)

    def test_scale_fields_are_billions_of_vnd(self, full_client):
        out = _provider(full_client).fetch("VNM.VN")
        assert out["market_cap"] == pytest.approx(130_000.0)
        assert out["revenue"] == pytest.approx(60_000.0)

    def test_metadata_mapped(self, full_client):
        out = _provider(full_client).fetch("VNM.VN")
        assert out["company_name"] == "Vietnam Dairy Products JSC"
        assert out["exchange"] == "HOSE"
        assert out["sector"] == "Food & Beverage"
        assert out["industry"] == "Food Producers"

    def test_52_week_range_from_history(self, full_client):
        out = _provider(full_client).fetch("VNM.VN")
        assert out["fifty_two_week_high"] == 62000.0
        assert out["fifty_two_week_low"] == 58000.0

    def test_foreign_room_captured(self, full_client):
        assert _provider(full_client).fetch("VNM.VN")["mcp_metrics"]["foreign_room"] == 41.5

    def test_suffix_stripped_before_query(self, full_client):
        seen = []

        def factory(symbol):
            seen.append(symbol)
            return full_client

        VNStockProvider(client_factory=factory).fetch("VNM.VN")
        assert seen == ["VNM"]

    def test_bare_symbol_also_works(self, full_client):
        assert _provider(full_client).fetch("VNM")["price"] == 62000.0

    def test_returned_keys_are_all_market_context_fields(self, full_client):
        from dataclasses import fields
        from augur.personas.base import MarketContext

        valid = {f.name for f in fields(MarketContext)} | {"data_source"}
        out = _provider(full_client).fetch("VNM.VN")
        assert set(out) <= valid, set(out) - valid


class TestColumnNameDrift:
    """vnstock 上游改列名时，多候选匹配必须仍能取到值。"""

    def test_alternate_price_column(self):
        board = _Frame([{"close_price": 33000.0, "reference_price": 32000.0}])
        out = _provider(_Client(board=board)).fetch("FPT.VN")
        assert out["price"] == 33000.0
        assert out["change_pct"] == pytest.approx((33000 / 32000 - 1) * 100)

    def test_alternate_ratio_columns(self):
        board = _Frame([{"match_price": 100.0}])
        ratios = _Frame([{"price_to_earning": 9.9, "price_to_book": 1.1, "debt_to_equity": 1.0}])
        out = _provider(_Client(board=board, ratios=ratios)).fetch("HPG.VN")
        assert out["pe"] == 9.9
        assert out["pb"] == 1.1
        assert out["debt_ratio"] == pytest.approx(0.5)

    def test_price_falls_back_to_last_close(self):
        out = _provider(_Client(board=_Frame([]), hist=_closes([10.0, 12.0]))).fetch("SSI.VN")
        assert out["price"] == 12.0
        assert out["change_pct"] == pytest.approx((12 / 10 - 1) * 100)


class TestFailureModes:
    def test_no_price_anywhere_raises(self):
        with pytest.raises(DataProviderError, match="no usable price"):
            _provider(_Client()).fetch("VNM.VN")

    def test_empty_symbol_raises(self):
        with pytest.raises(DataProviderError, match="empty symbol"):
            _provider(_Client()).fetch("")

    def test_client_init_failure_raises_provider_error(self):
        def boom(symbol):
            raise RuntimeError("network down")

        with pytest.raises(DataProviderError):
            VNStockProvider(client_factory=boom).fetch("VNM.VN")

    def test_one_endpoint_failing_does_not_sink_the_fetch(self):
        client = _Client(board=_Frame([{"match_price": 50.0}]))

        def explode(*a, **kw):
            raise RuntimeError("ratio endpoint 500")

        client.finance.ratio = explode
        out = _provider(client).fetch("VNM.VN")
        assert out["price"] == 50.0
        assert out["pe"] == 0.0  # 缺失 -> safe_num 默认值，而不是 NaN

    def test_missing_subclients_are_tolerated(self):
        class Bare:
            pass

        bare = Bare()
        bare.quote = _Quote(_closes([7.0]))
        out = _provider(bare).fetch("VNM.VN")
        assert out["price"] == 7.0

    def test_nan_values_are_scrubbed(self):
        board = _Frame([{"match_price": 100.0}])
        ratios = _Frame([{"pe": float("nan"), "pb": float("inf"), "roe": None}])
        out = _provider(_Client(board=board, ratios=ratios)).fetch("VNM.VN")
        assert out["pe"] == 0.0 and out["pb"] == 0.0 and out["roe"] == 0.0


class TestIsConfigured:
    def test_is_configured_is_a_bool_and_never_raises(self):
        assert isinstance(VNStockProvider.is_configured(), bool)

    def test_missing_vnstock_raises_provider_error_not_import_error(self, monkeypatch):
        import builtins

        real_import = builtins.__import__

        def no_vnstock(name, *args, **kwargs):
            if name == "vnstock":
                raise ImportError("no module named vnstock")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", no_vnstock)
        with pytest.raises(DataProviderError, match="vnstock not installed"):
            VNStockProvider().fetch("VNM.VN")


class TestHelpers:
    def test_rows_handles_none_and_junk(self):
        assert _rows(None) == []
        assert _rows(42) == []

    def test_rows_lowercases_keys(self):
        assert _rows({"MatchPrice": 1})[0] == {"matchprice": 1}

    def test_rows_flattens_multiindex_columns(self):
        frame = _Frame([{("a", "PE"): 12.0}], columns=[("a", "PE")])
        assert _rows(frame) == [{"pe": 12.0}]

    def test_pick_tries_candidates_in_order(self):
        assert _pick({"b": 2}, "a", "b") == 2
        assert _pick({"a": None, "b": 2}, "a", "b") == 2
        assert _pick({}, "a", "b") is None
