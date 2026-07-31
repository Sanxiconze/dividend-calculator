"""
股息率计算逻辑 - 核心计算模块
完全使用真实数据，不虚构任何数据
"""
import datetime
import logging
from dataclasses import dataclass
from typing import Callable, Optional, Tuple, List

from .datasource.base import StockInfo, DividendDetail
from .api import get_stock_info
from .tencent_quote import fetch_tencent_quote
from .datasource import get_data_source_manager
from .utils import get_stock_list_cache, extract_dividend_per_10, parse_dividend_df
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class DividendResult:
    """股息率计算结果"""
    stock_code: str
    stock_name: Optional[str]
    current_price: float
    total_shares: float
    total_market_cap: float
    total_dividend: float
    dividend_yield_before_tax: float
    dividend_yield_after_tax: float       # 持股1月~1年，扣税10%
    dividend_yield_after_tax_20: float    # 持股不足1月，扣税20%
    latest_year: Optional[str]
    dividend_details: List[DividendDetail]
    explanation: str


def calculate_dividend_yield(
    total_dividend: float,
    total_market_cap: float
) -> Tuple[float, float, float]:
    """
    核心计算逻辑：计算股息率

    Args:
        total_dividend: 近一年现金分红总额（元）
        total_market_cap: 当前总市值（元）

    Returns:
        (含税/持股1年以上免税%, 持股1月~1年扣税10%后%, 持股不足1月扣税20%后%)
    """
    if total_market_cap <= 0:
        return 0.0, 0.0, 0.0

    dividend_yield_before_tax = (total_dividend / total_market_cap) * 100
    dividend_yield_after_tax = dividend_yield_before_tax * 0.9
    dividend_yield_after_tax_20 = dividend_yield_before_tax * 0.8

    return dividend_yield_before_tax, dividend_yield_after_tax, dividend_yield_after_tax_20


def get_latest_full_year_dividend(
    stock_code: str, stock_info: StockInfo
) -> Tuple[float, Optional[str], List[DividendDetail], str]:
    """
    获取近12个月(TTM)已除权现金分红总额和明细
    多数据源自动降级：mootdx → akshare fhps_detail_em（含预案）→ akshare cninfo
    """
    # 方式1: 数据源管理器（mootdx）
    try:
        manager = get_data_source_manager()
        total_div, year, details, expl = manager.get_latest_dividend(stock_code, stock_info)
        if total_div > 0:
            logger.info("通过数据源管理器获取分红数据成功: %s %s年", stock_code, year)
            return total_div, year, details, expl
    except Exception as e:
        logger.debug("数据源管理器（mootdx）获取分红失败: %s", e)

    # 方式2: akshare fhps_detail_em（含预案，数据最全）
    try:
        import akshare as ak
        fhps_df = ak.stock_fhps_detail_em(symbol=stock_code)
        if not fhps_df.empty:
            total_div, year, details, expl = _parse_fhps_detail(fhps_df, stock_info)
            if total_div > 0:
                logger.info("通过akshare fhps_detail_em获取分红数据成功: %s %s年", stock_code, year)
                return total_div, year, details, expl
    except Exception as e:
        logger.debug("akshare fhps_detail_em 获取分红失败: %s", e)

    # 方式3: akshare cninfo 分红数据（兜底）
    try:
        import akshare as ak
        dividend_df = ak.stock_dividend_cninfo(symbol=stock_code)
        if not dividend_df.empty:
            total_div, year, details, expl = parse_dividend_df(
                dividend_df, stock_info,
                report_col="报告时间",
                scheme_col="实施方案分红说明",
                payout_col="派息比例",
                ex_date_col="除权日",
            )
            if total_div > 0:
                logger.info("通过akshare cninfo获取分红数据成功: %s %s年", stock_code, year)
                return total_div, year, details, expl
    except Exception as e:
        logger.debug("akshare cninfo 获取分红失败: %s", e)

    return 0.0, None, [], "所有数据源都无法获取分红数据"


def _report_label(report_date) -> str:
    """报告期 → 展示标签：12→年报，6→半年报，3→一季报，9→三季报，其余→YYYY-MM"""
    import datetime

    if isinstance(report_date, datetime.datetime):
        y, m = report_date.year, report_date.month
    elif isinstance(report_date, datetime.date):
        y, m = report_date.year, report_date.month
    elif isinstance(report_date, str):
        parts = str(report_date).split("-")
        try:
            y, m = int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            return str(report_date)[:10]
    else:
        return str(report_date)[:10]

    if m == 12:
        return f"{y}年报"
    if m == 6:
        return f"{y}半年报"
    if m == 3:
        return f"{y}一季报"
    if m == 9:
        return f"{y}三季报"
    return f"{y:04d}-{m:02d}"


def _to_date(v):
    """任意日期值 → datetime.date；无法解析返回 None"""
    import datetime

    if v is None or pd.isna(v):
        return None
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    try:
        return datetime.date.fromisoformat(str(v).strip()[:10])
    except ValueError:
        return None


def _ttm_window(ref_date) -> Tuple[datetime.date, str]:
    """TTM 窗口：(cutoff, ref_date]，返回 (cutoff, 'start至end' 字符串)"""
    import datetime

    cutoff = ref_date - datetime.timedelta(days=365)
    window_start = cutoff + datetime.timedelta(days=1)
    window = f"{window_start.isoformat()}至{ref_date.isoformat()}"
    return cutoff, window


def _parse_fhps_detail(
    fhps_df: pd.DataFrame, stock_info: StockInfo, ref_date=None
) -> Tuple[float, Optional[str], List[DividendDetail], str]:
    """
    解析 akshare stock_fhps_detail_em — 近12个月(TTM)已除权现金分红

    过滤掉「预披露」（数据不全），只统计除权除息日落在
    (ref_date-365天, ref_date] 窗口内的记录（已实施分配）。

    Returns:
        (总分红金额, 最近分红标签, 分红明细, 说明)
    """
    import datetime

    ref_date = ref_date or datetime.date.today()
    cutoff, window = _ttm_window(ref_date)

    # 只保留有实际分红金额的记录，排除预披露
    valid = fhps_df[
        fhps_df['现金分红-现金分红比例'].notna()
        & (fhps_df['现金分红-现金分红比例'] > 0)
        & (fhps_df['方案进度'] != '预披露')
    ].copy()

    records = []
    for _, row in valid.iterrows():
        dp10 = float(row['现金分红-现金分红比例'])
        if dp10 != dp10 or dp10 <= 0:  # NaN check (NaN != NaN is True)
            continue

        # 只统计已除权（有除权除息日）且在 TTM 窗口内的分红
        ex_date = _to_date(row.get('除权除息日'))
        if ex_date is None:
            continue
        if not (cutoff < ex_date <= ref_date):
            continue

        records.append({
            'ex': ex_date,
            'dp10': dp10,
            'label': _report_label(row['报告期']),
        })

    if not records:
        return 0.0, None, [], f"近12个月({window})无已除权分红"

    records.sort(key=lambda r: r['ex'])
    total_per_10 = sum(r['dp10'] for r in records)
    dps = total_per_10 / 10.0
    total_shares = stock_info.total_shares
    total_dividend = dps * total_shares

    details = [
        DividendDetail(r['label'], r['dp10'], ex_dividend_date=r['ex'].isoformat())
        for r in records
    ]
    latest_label = records[-1]['label']

    dividend_list = [
        f"{d.report_time}: 10派{d.dividend_per_10}元"
        for d in details
    ]
    explanation = (
        f"近12个月({window})除权分红：{'，'.join(dividend_list)}，"
        f"合计10派{total_per_10:.3f}元(每股{dps:.4f}元)，"
        f"总股本{total_shares / 1e8:.2f}亿股，"
        f"总分红{total_dividend / 1e8:.2f}亿元"
    )

    return total_dividend, latest_label, details, explanation


def _get_stock_name(stock_code: str) -> Optional[str]:
    """获取股票名称（优先使用腾讯行情，快速）"""
    # 方式1: 腾讯行情（快速，不依赖东方财富）
    quote = fetch_tencent_quote(stock_code, timeout=5)
    if quote is not None and quote.name is not None:
        return quote.name

    # 方式2: akshare 缓存（较慢）
    try:
        cache = get_stock_list_cache()
        if cache is not None:
            match = cache[cache["code"] == stock_code]
            if not match.empty:
                return str(match.iloc[0]["name"])
    except Exception as e:
        logger.debug("akshare缓存获取股票名称失败 %s: %s", stock_code, e)
    return None


def calculate_true_dividend_yield(
    stock_input: str,
    *,
    stock_info_provider: Optional[Callable[[str], Optional[StockInfo]]] = None,
    dividend_provider: Optional[
        Callable[[str, StockInfo], Tuple[float, Optional[str], List[DividendDetail], str]]
    ] = None,
) -> Optional[DividendResult]:
    """
    计算真实股息率。

    Args:
        stock_input: 股票代码或名称
        stock_info_provider: 股票信息获取函数（不传则使用默认 get_stock_info）
        dividend_provider: 分红数据获取函数（不传则使用默认 DataSourceManager）
            签名为 (stock_code, stock_info) → (total_div, year, details, explanation)
    """
    _stock_info = stock_info_provider or get_stock_info
    _dividend = dividend_provider or get_latest_full_year_dividend

    try:
        stock_info = _stock_info(stock_input)
        if stock_info is None:
            logger.error("无法获取股票信息: %s", stock_input)
            return None

        stock_code = stock_info.stock_code
        total_market_cap = stock_info.current_price * stock_info.total_shares

        total_dividend, latest_year, dividend_details, dividend_explanation = (
            _dividend(stock_code, stock_info)
        )

        if total_dividend <= 0:
            return DividendResult(
                stock_code=stock_code,
                stock_name=None,
                current_price=stock_info.current_price,
                total_shares=stock_info.total_shares,
                total_market_cap=total_market_cap,
                total_dividend=0.0,
                dividend_yield_before_tax=0.0,
                dividend_yield_after_tax=0.0,
                dividend_yield_after_tax_20=0.0,
                latest_year=None,
                dividend_details=[],
                explanation=f"无有效分红: {dividend_explanation}",
            )

        dividend_yield_before_tax, dividend_yield_after_tax, dividend_yield_after_tax_20 = calculate_dividend_yield(
            total_dividend, total_market_cap
        )

        stock_name = _get_stock_name(stock_code)

        explanation = (
            f"核心公式: 近一年现金分红总额({total_dividend / 1e8:.2f}亿元) "
            f"/ 当前总市值({total_market_cap / 1e8:.2f}亿元) "
            f"= {dividend_yield_before_tax:.2f}%(持股1年以上免税) | "
            f"{dividend_yield_after_tax:.2f}%(持股1月~1年扣税10%) | "
            f"{dividend_yield_after_tax_20:.2f}%(持股不足1月扣税20%). "
            f"{dividend_explanation}. "
            f"当前股价{stock_info.current_price:.2f}元, 总股本{stock_info.total_shares / 1e8:.2f}亿股."
        )

        return DividendResult(
            stock_code=stock_code,
            stock_name=stock_name,
            current_price=stock_info.current_price,
            total_shares=stock_info.total_shares,
            total_market_cap=total_market_cap,
            total_dividend=total_dividend,
            dividend_yield_before_tax=dividend_yield_before_tax,
            dividend_yield_after_tax=dividend_yield_after_tax,
            dividend_yield_after_tax_20=dividend_yield_after_tax_20,
            latest_year=latest_year,
            dividend_details=dividend_details,
            explanation=explanation,
        )

    except Exception as e:
        logger.error("计算真实股息率异常 %s: %s", stock_input, e)
        return None
