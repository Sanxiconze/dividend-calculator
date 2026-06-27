"""
数据源管理器 - 管理多个数据源，支持自动降级

数据源架构（mootdx + 腾讯双引擎）：
  mootdx（通达信协议）→ 行情/K线/除权除息/财务快照/F10资料
  腾讯行情（HTTP）    → PE_TTM/PB/总股本（已验证准确）
"""
import logging
from typing import Optional, List, Tuple

from .base import StockInfo, DividendDetail, DataSource

logger = logging.getLogger(__name__)
from .mootdx_source import MootdxSource
from .sina_source import SinaSource
from .tencent_source import TencentSource


class DataSourceManager:
    """数据源管理器，按优先级尝试多个数据源"""

    def __init__(self, sources=None):
        if sources is not None:
            self._sources = sorted(sources, key=lambda s: s.priority)
        else:
            self._sources = []
            self._register_default_sources()

    def _register_default_sources(self):
        """注册默认数据源（tencent 行情 + sina 备用 + mootdx 分红）"""
        self.register_source(TencentSource())  # priority 3（价格+股本）
        self.register_source(SinaSource())     # priority 4（新浪价格+腾讯股本备用）
        self.register_source(MootdxSource())   # priority 5（分红+K线）

    def register_source(self, source: DataSource):
        """注册新的数据源，按优先级插入"""
        inserted = False
        for i, existing in enumerate(self._sources):
            if source.priority < existing.priority:
                self._sources.insert(i, source)
                inserted = True
                break
        if not inserted:
            self._sources.append(source)

    def get_stock_info(self, stock_input: str) -> Optional[StockInfo]:
        """按优先级尝试获取股票信息"""
        last_error = None
        for source in self._sources:
            try:
                info = source.get_stock_info(stock_input)
                if info is not None:
                    return info
            except Exception as e:
                last_error = e
                continue

        if last_error is not None:
            logger.warning("所有数据源获取 %s 失败，最后错误: %s", stock_input, last_error)
        return None

    def get_latest_dividend(
        self,
        stock_code: str,
        stock_info: StockInfo
    ) -> Tuple[float, Optional[str], List[DividendDetail], str]:
        """按优先级尝试获取分红数据"""
        last_error = None
        for source in self._sources:
            try:
                total_div, year, details, expl = source.get_latest_dividend(
                    stock_code, stock_info
                )
                if total_div > 0:
                    return total_div, year, details, expl
            except Exception as e:
                last_error = e
                continue

        if last_error is not None:
            logger.warning("所有数据源获取 %s 分红失败，最后错误: %s", stock_code, last_error)
        return 0.0, None, [], "所有数据源都无法获取分红数据"

    def get_source_names(self) -> List[str]:
        """获取所有已注册的数据源名称"""
        return [source.name for source in self._sources]


# 全局单例
_data_source_manager: Optional[DataSourceManager] = None


def get_data_source_manager() -> DataSourceManager:
    """获取数据源管理器单例"""
    global _data_source_manager
    if _data_source_manager is None:
        _data_source_manager = DataSourceManager()
    return _data_source_manager
