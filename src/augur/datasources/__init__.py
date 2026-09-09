# -*- coding: utf-8 -*-
"""
augur.datasources - 多数据源抽象层

提供统一的 ``DataProvider`` 接口与多个具体实现。data.py 通过 provider 链按优先级
依次尝试，实现多数据源 fallback，消除单点故障，并让不同来源互为参考/补充。

provider 链（按优先级）:
    1. yfinance      - 主数据源（基本面 + 行情 + 技术指标，无需 key）
    2. finnhub       - 可选，需 FINNHUB_API_KEY（基本面 + 分析师评级）
    3. alphavantage  - 可选，需 ALPHAVANTAGE_API_KEY（基本面 OVERVIEW）
    4. stooq         - 行情兜底（免费 CSV，无需 key，保证至少有 price）

公开接口:
    DataProvider          - 抽象基类
    DataProviderError     - 失败异常（触发 fallback）
    safe_num / clamp      - 数值清洗工具
    YFinanceProvider      - 主数据源
    FinnhubProvider       - 可选数据源（分析师评级）
    AlphaVantageProvider  - 可选数据源
    StooqProvider         - 行情兜底
    default_providers     - 返回默认 provider 链（按已配置 key 动态组装）
    available_sources     - 返回当前可用数据源标识列表（用于 UI 展示）
"""

from augur.datasources.base import (
    DataProvider,
    DataProviderError,
    clamp,
    safe_num,
)
from augur.datasources.alphavantage_provider import (
    AlphaVantageProvider,
    is_configured as _av_configured,
)
from augur.datasources.finnhub_provider import (
    FinnhubProvider,
    is_configured as _finnhub_configured,
)
from augur.datasources.stooq_provider import StooqProvider
from augur.datasources.vnstock_provider import VNStockProvider
from augur.datasources.yfinance_provider import YFinanceProvider

__all__ = [
    "DataProvider",
    "DataProviderError",
    "clamp",
    "safe_num",
    "YFinanceProvider",
    "FinnhubProvider",
    "AlphaVantageProvider",
    "StooqProvider",
    "VNStockProvider",
    "default_providers",
    "available_sources",
]


def default_providers(market: str = "US"):
    """返回指定市场的 provider 链。

    默认（US / CN / HK 等）顺序不变:
        yfinance -> finnhub(若配置) -> alphavantage(若配置) -> stooq。
    可选数据源仅在配置了对应环境变量 API key 时才加入链中，避免无 key 时产生无谓请求。

    越南（``market="VN"``）在链首插入 vnstock：

        vnstock(若已安装) -> yfinance -> finnhub(若配置) -> ... -> stooq

    为什么必须插在**最前面**：这条链是「首个返回非空结果者胜出，并提供整个
    context」。yfinance 的 ``.VN`` 后缀能拿到越南行情，但基本面几乎为空——
    若把 vnstock 追加在尾部，yfinance 会先胜出，vnstock 永远不会被调用，
    等于没接。反过来，vnstock 未安装或抓取失败时抛 ``DataProviderError``，
    链会自然回落到 yfinance ``.VN``，行为与接入前完全一致。

    Args:
        market: 市场代码（``augur.markets`` 中的 ``Market.code``）。未知代码
            按默认链处理。

    Returns:
        provider 实例列表，按尝试顺序排列。
    """
    chain = []
    if str(market).upper() == "VN" and VNStockProvider.is_configured():
        chain.append(VNStockProvider())
    chain.append(YFinanceProvider())
    if _finnhub_configured():
        chain.append(FinnhubProvider())
    if _av_configured():
        chain.append(AlphaVantageProvider())
    chain.append(StooqProvider())
    return chain


def available_sources():
    """返回当前可用的数据源标识列表（供 Dashboard/UI 展示数据来源覆盖情况）。"""
    sources = []
    if VNStockProvider.is_configured():
        sources.append("vnstock")
    sources.append("yfinance")
    if _finnhub_configured():
        sources.append("finnhub")
    if _av_configured():
        sources.append("alphavantage")
    sources.append("stooq")
    return sources
