import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.dividend import (
    calculate_dividend_yield,
    calculate_true_dividend_yield,
    _parse_fhps_detail,
)
from src.datasource.base import StockInfo, DividendDetail
import datetime
import pandas as pd


def test_calculate_dividend_yield():
    before_tax, after_tax, after_tax_20 = calculate_dividend_yield(214.46e8, 6040.24e8)

    assert before_tax == pytest.approx(3.55, abs=0.01)
    assert after_tax == pytest.approx(3.20, abs=0.01)
    assert after_tax_20 == pytest.approx(2.84, abs=0.01)


def test_calculate_dividend_yield_with_zero_market_cap():
    assert calculate_dividend_yield(100, 0) == (0.0, 0.0, 0.0)


def test_dividend_result_with_sample_data():
    """测试股息率计算使用样本数据"""
    # 使用长江电力的样本数据进行测试
    total_shares = 22741859116.0
    current_price = 26.56
    total_market_cap = current_price * total_shares
    total_dividend = 21445553126.388

    before_tax, after_tax, after_tax_20 = calculate_dividend_yield(total_dividend, total_market_cap)

    assert before_tax == pytest.approx(3.55, abs=0.01)
    assert after_tax == pytest.approx(3.20, abs=0.01)
    assert after_tax_20 == pytest.approx(2.84, abs=0.01)


# ---------------------------------------------------------------------------
# 依赖注入接缝测试 — 无需网络即可验证完整编排路径
# ---------------------------------------------------------------------------

def _fake_stock_info(code: str) -> StockInfo:
    """Fake 股票信息提供器。"""
    return StockInfo(
        stock_code="600900",
        current_price=25.0,
        total_shares=10_000_000.0,  # 1000万股
    )


def _fake_dividend(code: str, info: StockInfo):
    """Fake 分红数据提供器：10派1.25元 × 1000万股 = 125万分红。"""
    details = [DividendDetail(report_time="20251231", dividend_per_10=1.25)]
    return 1_250_000.0, "2025", details, "2025年度10派1.25元"


def test_di_seam_full_pipeline():
    """通过注入 fake provider，无需网络即可验证完整计算流水线。"""
    result = calculate_true_dividend_yield(
        "600900",
        stock_info_provider=_fake_stock_info,
        dividend_provider=_fake_dividend,
    )

    assert result is not None
    assert result.stock_code == "600900"
    assert result.current_price == 25.0
    assert result.total_shares == 10_000_000.0
    # 总市值 = 25.0 × 1000万股 = 2.5亿
    assert result.total_market_cap == 250_000_000.0
    # 总分红 = 125万
    assert result.total_dividend == 1_250_000.0
    # 股息率 = 125万 / 25000万 × 100 = 0.5%
    assert result.dividend_yield_before_tax == 0.5
    assert result.dividend_yield_after_tax == 0.45    # × 0.9
    assert result.dividend_yield_after_tax_20 == 0.4   # × 0.8
    assert result.latest_year == "2025"
    assert len(result.dividend_details) == 1
    assert "2025年度10派1.25元" in result.explanation


def test_di_seam_defaults_still_work():
    """不传 provider 时，函数正常执行（使用真实数据源）。"""
    result = calculate_true_dividend_yield("600900")
    # 可能返回 None（网络不可用），也可能返回结果——都不应抛异常
    if result is not None:
        assert result.stock_code == "600900"
        assert result.current_price > 0
        assert result.total_shares > 0
    # 无论网络通不通，函数不应崩溃
    assert True


def test_di_seam_invalid_stock():
    """注入返回 None 的 provider，模拟数据不可用。"""
    result = calculate_true_dividend_yield(
        "999999",
        stock_info_provider=lambda code: None,
        dividend_provider=_fake_dividend,
    )
    assert result is None


# ---------------------------------------------------------------------------
# _parse_fhps_detail TTM 解析 — 窗口 (ref-365天, ref] 内已除权分红
# ---------------------------------------------------------------------------

def _fhps_df(rows):
    return pd.DataFrame(rows, columns=[
        "报告期", "现金分红-现金分红比例", "方案进度", "除权除息日",
    ])


def test_parse_fhps_detail_ttm_window():
    """002555 真实数据形态：仅统计近12个月已除权分红，标签取最近除权的报告期。"""
    ref = datetime.date(2026, 7, 31)  # 窗口 (2025-07-31, 2026-07-31]
    df = _fhps_df([
        ("2026-03-31", 2.1, "实施分配", "2026-06-02"),
        ("2025-12-31", 4.0, "实施分配", "2026-05-22"),
        ("2025-09-30", 2.1, "实施分配", "2025-11-06"),
        ("2025-06-30", 2.1, "实施分配", "2025-09-04"),
        ("2025-03-31", 2.1, "实施分配", "2025-05-27"),  # 窗口外
    ])
    info = StockInfo(stock_code="002555", current_price=10.0, total_shares=10_000_000.0)

    total_div, year, details, expl = _parse_fhps_detail(df, info, ref_date=ref)

    assert year == "2026一季报"  # 最近除权(2026-06-02)对应 2026-03-31 报告期
    assert total_div == pytest.approx(10.3 / 10 * 10_000_000)
    assert len(details) == 4
    assert details[0].report_time == "2025半年报"   # 2025-09-04 除权
    assert details[-1].report_time == "2026一季报"
    assert [d.dividend_per_10 for d in details] == [2.1, 2.1, 4.0, 2.1]
    assert "近12个月(2025-08-01至2026-07-31)除权分红" in expl
    assert "合计10派10.300元" in expl


def test_parse_fhps_detail_excludes_pending():
    """预披露 + 无除权除息日(未实施) 的行不参与 TTM 统计。"""
    ref = datetime.date(2026, 7, 31)
    df = _fhps_df([
        ("2025-12-31", 5.0, "预披露", "2026-05-22"),      # 预披露排除
        ("2025-12-31", 4.0, "股东大会决议通过", ""),      # 无除权日排除
        ("2025-12-31", 3.0, "实施分配", "2025-05-23"),    # 窗口外排除
        ("2025-12-31", 3.0, "实施分配", "2026-05-22"),    # 有效
    ])
    info = StockInfo(stock_code="600000", current_price=10.0, total_shares=10_000_000.0)

    total_div, year, details, expl = _parse_fhps_detail(df, info, ref_date=ref)

    assert year == "2025年报"
    assert len(details) == 1
    assert total_div == pytest.approx(3.0 / 10 * 10_000_000)


def test_parse_fhps_detail_empty_window():
    """窗口内无分红 → total=0, latest=None。"""
    ref = datetime.date(2026, 7, 31)
    df = _fhps_df([
        ("2025-12-31", 3.0, "实施分配", "2025-05-23"),  # 窗口外
    ])
    info = StockInfo(stock_code="600000", current_price=10.0, total_shares=10_000_000.0)

    total_div, year, details, expl = _parse_fhps_detail(df, info, ref_date=ref)

    assert total_div == 0.0
    assert year is None
    assert details == []
    assert "无已除权分红" in expl
