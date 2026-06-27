"""股票综合分析流水线模块。

封装 get_stock_info → get_latest_full_year_dividend → calculate_pr
三步编排，CLI 和 Web 各自成为薄适配器。
"""

import logging
from dataclasses import dataclass
from typing import Optional

from .api import get_stock_info
from .datasource.base import StockInfo
from .dividend import get_latest_full_year_dividend
from .pr import calculate_pr, PRResult

logger = logging.getLogger(__name__)


@dataclass
class StockAnalysisResult:
    """股票综合分析的完整结果。"""
    stock_info: StockInfo
    dividend_total: float
    pr_result: PRResult


def run_stock_analysis(stock_input: str) -> Optional[StockAnalysisResult]:
    """执行股票综合分析流水线。

    依次获取股票基本信息、分红数据、市赚率，
    三步中任一步失败即返回 None。

    CLI 和 Web 路径共用一个编排入口，
    将来加第三个入口（定时任务/通知）零成本。
    """
    stock_info = get_stock_info(stock_input)
    if stock_info is None:
        logger.error("无法获取股票信息: %s", stock_input)
        return None

    stock_code = stock_info.stock_code
    dividend_total, _, _, _ = get_latest_full_year_dividend(stock_code, stock_info)

    pr_result = calculate_pr(
        stock_code=stock_code,
        dividend_total=dividend_total if dividend_total > 0 else None,
        stock_info=stock_info,
    )

    return StockAnalysisResult(
        stock_info=stock_info,
        dividend_total=dividend_total,
        pr_result=pr_result,
    )
