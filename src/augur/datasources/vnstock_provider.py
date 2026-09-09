# -*- coding: utf-8 -*-
"""
augur.datasources.vnstock_provider - 越南市场数据源 (HOSE / HNX / UPCoM)

越南没有 SEC EDGAR 的对应物，基本面只能来自本地数据源。``vnstock`` 是目前
覆盖最好的免费方案（封装 VCI / TCBS 接口，无需 API key），因此作为越南市场
provider 链的**首选**，yfinance ``.VN`` 作为兜底。

设计要点:

  - **可选依赖。** ``vnstock`` 通过延迟导入引入，未安装时 ``is_configured()``
    返回 False，该 provider 根本不会进入链中（``augur.datasources.default_providers``
    负责这一判断），越南 ticker 依然经由 yfinance ``.VN`` 正常工作。

  - **任何失败都降级，绝不崩溃。** 导入失败、网络异常、字段缺失、上游改列名——
    全部收敛为 ``DataProviderError``，触发链上的下一个 provider。vnstock 是
    非官方封装，上游变更是常态而非例外，因此字段抽取全部走 ``_pick()``
    的多候选名匹配，而不是硬编码单一列名。

  - **金额单位是「十亿 VND」，不是 USD。** ``market_cap`` / ``revenue`` /
    ``fcf`` 等字段沿用「十亿」量纲，但计价货币为 VND，并通过 ``currency="VND"``
    显式标注。这里**不做汇率换算**（需要实时汇率源，超出范围）。下游任何跨市场
    排序、筛选阈值或图表坐标轴都必须读 ``currency`` 后再比较——同一家公司的
    VND 市值约为 USD 数字的 25000 倍，忽略 ``currency`` 会得到完全错误的结论。

  - **±7% 涨跌幅限制会压缩波动率。** HOSE 的日内价格带截断了 ``volatility_60d``
    与回撤类评分所假设的尾部。这是已知的评分口径偏差，此处**不做**静默重标定。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from augur.datasources.base import DataProvider, DataProviderError, clamp, safe_num
from augur.markets import strip_market_suffix

logger = logging.getLogger(__name__)

#: vnstock 数据后端。VCI 覆盖面比 TCBS 略好，二者都不需要 key。
_SOURCE = "VCI"

#: 拉取多少天历史用于技术指标（与 yfinance provider 的 3mo 口径对齐）。
_HISTORY_DAYS = 95


def _vnstock_available() -> bool:
    """vnstock 是否可导入（不实例化、不触网）。"""
    try:
        import vnstock  # noqa: F401
    except Exception:
        return False
    return True


def _rows(frame: Any) -> List[Dict[str, Any]]:
    """把 vnstock 返回的对象归一为 ``list[dict]``。

    vnstock 各接口返回 pandas DataFrame，但版本之间存在 dict / list 的差异，
    且部分接口返回 MultiIndex 列。这里统一拍平为普通字典列表，列名转为
    小写字符串，供 ``_pick`` 做多候选匹配。
    """
    if frame is None:
        return []
    # pandas DataFrame
    if hasattr(frame, "to_dict") and hasattr(frame, "columns"):
        try:
            columns = list(frame.columns)
            flat = {}
            for col in columns:
                # MultiIndex 列 -> 取最后一段（真正的字段名）
                key = col[-1] if isinstance(col, tuple) else col
                flat[col] = str(key).strip().lower()
            records = frame.to_dict(orient="records")
            return [{flat.get(k, str(k).strip().lower()): v for k, v in rec.items()}
                    for rec in records]
        except Exception:
            return []
    if isinstance(frame, dict):
        return [{str(k).strip().lower(): v for k, v in frame.items()}]
    if isinstance(frame, list):
        out = []
        for item in frame:
            if isinstance(item, dict):
                out.append({str(k).strip().lower(): v for k, v in item.items()})
        return out
    return []


def _pick(row: Dict[str, Any], *names: str) -> Any:
    """按候选名依次取值，全部缺失时返回 None。

    上游列名在 vnstock 版本之间会漂移（``market_cap`` / ``marketcap`` /
    ``issue_share``…），逐一尝试比硬编码单一列名稳健得多。
    """
    for name in names:
        key = name.strip().lower()
        if key in row and row[key] is not None:
            return row[key]
    return None


class VNStockProvider(DataProvider):
    """基于 ``vnstock`` 的越南市场数据源。

    构造函数不触网也不导入 vnstock；所有外部交互都发生在 ``fetch()`` 内，
    以便测试完整 mock，也避免未安装 vnstock 时的 import 期副作用。
    """

    name = "vnstock"

    def __init__(self, client_factory: Optional[Any] = None, source: str = _SOURCE) -> None:
        #: 注入点：测试传入工厂函数即可完全绕开真实 vnstock。
        self._client_factory = client_factory
        self._source = source

    @staticmethod
    def is_configured() -> bool:
        """vnstock 是否可用。无需 API key，因此等价于「是否已安装」。"""
        return _vnstock_available()

    def _client(self, symbol: str) -> Any:
        if self._client_factory is not None:
            try:
                return self._client_factory(symbol)
            except Exception as exc:
                raise DataProviderError(f"vnstock client factory failed for {symbol}: {exc}") from exc
        try:
            from vnstock import Vnstock
        except Exception as exc:
            raise DataProviderError(f"vnstock not installed: {exc}") from exc
        try:
            return Vnstock().stock(symbol=symbol, source=self._source)
        except Exception as exc:
            raise DataProviderError(f"vnstock client init failed for {symbol}: {exc}") from exc

    # ---- 各接口的取数，单个失败不影响其余 ----

    @staticmethod
    def _safe_call(fn: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            logger.debug("vnstock call %s failed: %s", getattr(fn, "__name__", fn), exc)
            return None

    def _price_row(self, client: Any, symbol: str) -> Dict[str, Any]:
        trading = getattr(client, "trading", None)
        if trading is None:
            return {}
        board = self._safe_call(getattr(trading, "price_board", None), [symbol])
        rows = _rows(board)
        return rows[0] if rows else {}

    def _history_closes(self, client: Any) -> List[float]:
        quote = getattr(client, "quote", None)
        if quote is None:
            return []
        end = datetime.now()
        start = end - timedelta(days=_HISTORY_DAYS)
        hist = self._safe_call(
            getattr(quote, "history", None),
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval="1D",
        )
        closes = []
        for row in _rows(hist):
            close = safe_num(_pick(row, "close", "close_price", "c"))
            if close > 0:
                closes.append(close)
        return closes

    def _ratio_row(self, client: Any) -> Dict[str, Any]:
        finance = getattr(client, "finance", None)
        if finance is None:
            return {}
        ratios = self._safe_call(getattr(finance, "ratio", None), period="quarter", lang="en")
        rows = _rows(ratios)
        return rows[0] if rows else {}

    def _overview_row(self, client: Any) -> Dict[str, Any]:
        company = getattr(client, "company", None)
        if company is None:
            return {}
        overview = self._safe_call(getattr(company, "overview", None))
        rows = _rows(overview)
        return rows[0] if rows else {}

    def fetch(self, ticker: str) -> Dict[str, Any]:
        """拉取并标准化越南个股数据。

        Raises:
            DataProviderError: 任何一步失败，或拿不到有效价格——交由链上的
                yfinance ``.VN`` 兜底。
        """
        symbol = strip_market_suffix(ticker)
        if not symbol:
            raise DataProviderError(f"vnstock: empty symbol from {ticker!r}")

        client = self._client(symbol)

        price_row = self._price_row(client, symbol)
        ratio_row = self._ratio_row(client)
        overview_row = self._overview_row(client)
        closes = self._history_closes(client)

        # ---- 价格：优先实时盘口，回落到历史最后一根收盘 ----
        price = safe_num(_pick(price_row, "match_price", "close_price", "last_price", "close"))
        if price <= 0 and closes:
            price = closes[-1]
        if price <= 0:
            # 没有价格的 context 对下游毫无价值，直接触发 fallback。
            raise DataProviderError(f"vnstock returned no usable price for {symbol}")

        ref_price = safe_num(_pick(price_row, "ref_price", "reference_price", "prior_close_price"))
        if ref_price <= 0 and len(closes) >= 2:
            ref_price = closes[-2]
        change_pct = ((price / ref_price) - 1) * 100 if ref_price > 0 else 0.0

        # ---- 估值 / 盈利（vnstock ratio 已是比率，保持原口径）----
        pe = safe_num(_pick(ratio_row, "pe", "p/e", "price_to_earning"))
        pb = safe_num(_pick(ratio_row, "pb", "p/b", "price_to_book"))
        ps = safe_num(_pick(ratio_row, "ps", "p/s", "price_to_sale"))
        eps = safe_num(_pick(ratio_row, "eps", "earning_per_share"))
        roe = safe_num(_pick(ratio_row, "roe", "return_on_equity"))
        roa = safe_num(_pick(ratio_row, "roa", "return_on_asset"))
        gross_margins = safe_num(_pick(ratio_row, "gross_profit_margin", "gross_margin"))
        operating_margins = safe_num(_pick(ratio_row, "operating_profit_margin", "operating_margin"))
        profit_margins = safe_num(_pick(ratio_row, "post_tax_margin", "net_profit_margin", "profit_margin"))
        revenue_growth = safe_num(_pick(ratio_row, "revenue_growth", "revenue_yoy"))
        earnings_growth = safe_num(_pick(ratio_row, "earning_growth", "post_tax_profit_growth"))
        current_ratio = safe_num(_pick(ratio_row, "current_payment", "current_ratio"))
        quick_ratio = safe_num(_pick(ratio_row, "quick_payment", "quick_ratio"))
        dividend_yield = clamp(safe_num(_pick(ratio_row, "dividend_yield")), 0.0, 1.0)

        # ---- 负债率：vnstock 给的是 D/E，转成 D/A 与 yfinance provider 对齐 ----
        debt_to_equity = safe_num(_pick(ratio_row, "debt_on_equity", "debt_to_equity", "de"))
        if debt_to_equity > 0:
            debt_ratio = debt_to_equity / (1.0 + debt_to_equity)
        else:
            debt_ratio = 0.0

        # ---- 规模：单位为「十亿 VND」，绝非 USD（见模块 docstring）----
        market_cap = safe_num(_pick(ratio_row, "market_cap", "marketcap")) / 1e9
        revenue = safe_num(_pick(ratio_row, "revenue", "net_revenue")) / 1e9

        # ---- 元信息 ----
        company_name = (
            _pick(overview_row, "company_name", "short_name", "organ_name")
            or _pick(price_row, "organ_name")
            or ""
        )
        industry = _pick(overview_row, "industry", "icb_name3", "icb_name2") or ""
        sector = _pick(overview_row, "icb_name2", "sector", "industry") or ""
        business_summary = _pick(overview_row, "company_profile", "history", "business_summary") or ""
        exchange = _pick(overview_row, "exchange", "floor") or _pick(price_row, "exchange") or ""

        volume = safe_num(_pick(price_row, "accumulated_volume", "total_volume", "volume"))
        day_open = safe_num(_pick(price_row, "open_price", "open"))
        day_high = safe_num(_pick(price_row, "highest_price", "high_price", "high"))
        day_low = safe_num(_pick(price_row, "lowest_price", "low_price", "low"))

        # 外资持股上限（room）是越南特有的真实信号，装入 mcp_metrics 而非硬塞已有字段。
        foreign_room = safe_num(_pick(price_row, "foreign_room", "current_room", "remain_foreign_room"))

        # ---- 52 周高低点：用历史区间，vnstock 盘口不提供 ----
        fifty_two_week_high = max(closes) if closes else 0.0
        fifty_two_week_low = min(closes) if closes else 0.0
        price_vs_52w_high = ((price / fifty_two_week_high) - 1) * 100 if fifty_two_week_high else 0.0
        price_vs_52w_low = ((price / fifty_two_week_low) - 1) * 100 if fifty_two_week_low else 0.0

        # ---- 技术指标：复用既有实现，口径与其他 provider 完全一致 ----
        technicals: Dict[str, Any] = {}
        if closes:
            try:
                from augur import data as _data
                technicals = _data._calculate_technicals_from_prices(closes) or {}
            except Exception:
                logger.debug("vnstock technicals failed for %s", symbol, exc_info=True)

        result: Dict[str, Any] = {
            "data_source": self.name,
            "price": price,
            "change_pct": change_pct,
            "currency": "VND",
            "exchange": str(exchange),
            "company_name": str(company_name),
            "sector": str(sector),
            "industry": str(industry),
            "business_summary": str(business_summary),
            "market_cap": market_cap,
            "revenue": revenue,
            "pe": pe,
            "pb": pb,
            "ps": ps,
            "eps": eps,
            "roe": roe,
            "roa": roa,
            "gross_margins": gross_margins,
            "operating_margins": operating_margins,
            "profit_margins": profit_margins,
            "revenue_growth": revenue_growth,
            "earnings_growth": earnings_growth,
            "debt_ratio": debt_ratio,
            "current_ratio": current_ratio,
            "quick_ratio": quick_ratio,
            "dividend_yield": dividend_yield,
            "volume": volume,
            "day_open": day_open,
            "day_high": day_high,
            "day_low": day_low,
            "fifty_two_week_high": fifty_two_week_high,
            "fifty_two_week_low": fifty_two_week_low,
            "price_vs_52w_high": price_vs_52w_high,
            "price_vs_52w_low": price_vs_52w_low,
            "mcp_metrics": {"foreign_room": foreign_room} if foreign_room else {},
        }
        result.update(technicals)
        return result
