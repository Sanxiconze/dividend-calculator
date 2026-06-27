import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.datasource.base import MonthlyPrice, DividendRecord, HistoricalData


def test_monthly_price_creation():
    mp = MonthlyPrice(date="2024-06-30", close=25.50)
    assert mp.date == "2024-06-30"
    assert mp.close == 25.50


def test_dividend_record_creation():
    dr = DividendRecord(
        ex_dividend_date="2024-07-11",
        dividend_per_10=19.72,
        report_time="2023年度",
    )
    assert dr.ex_dividend_date == "2024-07-11"
    assert dr.dividend_per_10 == 19.72


def test_historical_data_creation():
    prices = [
        MonthlyPrice(date="2024-01-31", close=22.00),
        MonthlyPrice(date="2024-02-29", close=23.50),
    ]
    dividends = [
        DividendRecord(
            ex_dividend_date="2024-01-15",
            dividend_per_10=5.0,
            report_time="2023年度",
        ),
    ]
    hd = HistoricalData(
        stock_code="600900",
        stock_name="长江电力",
        monthly_prices=prices,
        dividend_records=dividends,
    )
    assert hd.stock_code == "600900"
    assert hd.stock_name == "长江电力"
    assert len(hd.monthly_prices) == 2
    assert len(hd.dividend_records) == 1


def test_historical_data_name_none():
    """stock_name can be None when lookup fails"""
    hd = HistoricalData(
        stock_code="000000",
        stock_name=None,
        monthly_prices=[],
        dividend_records=[],
    )
    assert hd.stock_name is None
