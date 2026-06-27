"""财年推断逻辑单元测试"""
import pytest
from src.utils import FiscalYear, infer_fiscal_year


class TestInferFiscalYear:
    """infer_fiscal_year 函数测试"""

    def test_january_returns_last_year_interim(self):
        result = infer_fiscal_year(2025, 1)
        assert result == FiscalYear(year=2024, is_annual=False)
        assert result.report_time == "2024中报"

    def test_february_returns_last_year_interim(self):
        result = infer_fiscal_year(2025, 2)
        assert result == FiscalYear(year=2024, is_annual=False)
        assert result.report_time == "2024中报"

    def test_march_returns_last_year_annual(self):
        result = infer_fiscal_year(2025, 3)
        assert result == FiscalYear(year=2024, is_annual=True)
        assert result.report_time == "2024年报"

    def test_april_returns_last_year_annual(self):
        result = infer_fiscal_year(2025, 4)
        assert result == FiscalYear(year=2024, is_annual=True)

    def test_may_returns_last_year_annual(self):
        result = infer_fiscal_year(2025, 5)
        assert result == FiscalYear(year=2024, is_annual=True)

    def test_june_returns_last_year_annual(self):
        result = infer_fiscal_year(2025, 6)
        assert result == FiscalYear(year=2024, is_annual=True)

    def test_september_returns_current_year_interim(self):
        result = infer_fiscal_year(2025, 9)
        assert result == FiscalYear(year=2025, is_annual=False)
        assert result.report_time == "2025中报"

    def test_december_returns_current_year_interim(self):
        result = infer_fiscal_year(2025, 12)
        assert result == FiscalYear(year=2025, is_annual=False)

    def test_august_returns_last_year_annual(self):
        """8月是边界：3-8月都是年报"""
        result = infer_fiscal_year(2025, 8)
        assert result == FiscalYear(year=2024, is_annual=True)

    def test_fiscal_year_is_frozen(self):
        """FiscalYear 应为不可变对象"""
        fy = infer_fiscal_year(2025, 4)
        with pytest.raises(AttributeError):
            fy.year = 2020
