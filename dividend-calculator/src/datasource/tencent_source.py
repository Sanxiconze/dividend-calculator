"""
腾讯行情数据源适配器

一次 HTTP 请求获取：价格 + 总股本 + PE_TTM + PB。
不提供分红数据（由 MootdxSource 提供）。
"""
import logging
from typing import Optional, List, Tuple

from ..tencent_quote import fetch_tencent_quote
from ..utils import ensure_6digit
from .base import StockInfo, DividendDetail, DataSource

logger = logging.getLogger(__name__)


class TencentSource:
    """腾讯行情数据源

    通过 qt.gtimg.cn 获取实时价格和总股本，一次请求完成。
    PE_TTM/PB 可从同一请求获取，但当前 StockInfo 协议未包含这两个字段。
    """

    @property
    def name(self) -> str:
        return "tencent"

    @property
    def priority(self) -> int:
        return 3  # 高于 mootdx(5)，优先尝试

    def get_stock_info(self, stock_input: str) -> Optional[StockInfo]:
        """获取股票基本信息：当前价格 + 总股本"""
        stock_code = ensure_6digit(stock_input)
        if not stock_code:
            return None

        quote = fetch_tencent_quote(stock_code)
        if quote is None:
            logger.debug("tencent 无法获取 %s 行情", stock_code)
            return None

        price = quote.price
        if price is None or price <= 0:
            logger.debug("tencent %s 价格无效: %s", stock_code, price)
            return None

        total_shares = quote.total_shares or quote.a_shares
        if total_shares is None or total_shares <= 0:
            logger.debug("tencent %s 总股本无效", stock_code)
            return None

        return StockInfo(
            stock_code=stock_code,
            current_price=price,
            total_shares=total_shares,
        )

    def get_latest_dividend(
        self, stock_code: str, stock_info: StockInfo
    ) -> Tuple[float, Optional[str], List[DividendDetail], str]:
        """腾讯行情不提供分红数据，由 MootdxSource 负责"""
        return 0.0, None, [], "tencent_source不提供分红数据"


