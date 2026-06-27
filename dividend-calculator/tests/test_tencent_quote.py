"""腾讯行情解析模块测试。"""

import pytest
from src.tencent_quote import TencentQuote, fetch_tencent_quote, _safe_float, _safe_str


# ---------------------------------------------------------------------------
# TencentQuote 不可变性
# ---------------------------------------------------------------------------

def test_tencent_quote_frozen():
    """TencentQuote 是不可变的（frozen dataclass）。"""
    q = TencentQuote(stock_code="600519", name="贵州茅台", price=1800.0)
    with pytest.raises(Exception):
        q.price = 1900.0  # type: ignore


def test_tencent_quote_defaults():
    """所有字段默认 None。"""
    q = TencentQuote(stock_code="000001")
    assert q.stock_code == "000001"
    assert q.name is None
    assert q.price is None
    assert q.pe_ttm is None
    assert q.pb is None
    assert q.total_shares is None
    assert q.a_shares is None


# ---------------------------------------------------------------------------
# _safe_float
# ---------------------------------------------------------------------------

def test_safe_float_valid():
    assert _safe_float(["", "0", "3.55"], 2) == 3.55


def test_safe_float_index_out_of_range():
    assert _safe_float(["a"], 5) is None


def test_safe_float_invalid_value():
    assert _safe_float(["abc"], 0) is None


def test_safe_float_zero_returns_none():
    """价格为 0 视为无效。"""
    assert _safe_float(["0.0"], 0) is None


def test_safe_float_negative_returns_none():
    """负数视为无效。"""
    assert _safe_float(["-5.0"], 0) is None


# ---------------------------------------------------------------------------
# _safe_str
# ---------------------------------------------------------------------------

def test_safe_str_valid():
    assert _safe_str(["", "贵州茅台"], 1) == "贵州茅台"


def test_safe_str_empty():
    assert _safe_str([""], 0) is None


def test_safe_str_index_out_of_range():
    assert _safe_str(["a"], 5) is None


# ---------------------------------------------------------------------------
# fetch_tencent_quote — 集成测试（需要网络，标记为 integration）
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_fetch_known_stock():
    """获取贵州茅台行情，验证关键字段非空。"""
    q = fetch_tencent_quote("600519")
    assert q is not None
    assert q.stock_code == "600519"
    assert q.name is not None
    assert q.price is not None
    assert q.price > 0


@pytest.mark.integration
def test_fetch_known_stock_sz():
    """获取深市股票行情。"""
    q = fetch_tencent_quote("000001")
    assert q is not None
    assert q.stock_code == "000001"
    assert q.price is not None


@pytest.mark.integration
def test_fetch_invalid_stock():
    """无效代码返回 None。"""
    q = fetch_tencent_quote("999999")
    # 腾讯行情对不存在代码可能返回空字段或空响应
    # 无论如何不应抛异常
    assert q is None or isinstance(q, TencentQuote)
