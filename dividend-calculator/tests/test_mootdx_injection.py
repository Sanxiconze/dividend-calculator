"""测试 MootdxSource 依赖注入（消除全局单例泄漏）"""
from unittest.mock import MagicMock, patch

from src.datasource.mootdx_source import MootdxSource


def _make_mock_client(closed=False):
    """创建一个 mock mootdx client"""
    client = MagicMock()
    client.closed = closed
    return client


class TestMootdxClientInjection:
    """测试 client 注入与 _get_client 逻辑"""

    def test_injected_client_used_when_not_closed(self):
        """注入的 client 未关闭时，应优先使用它"""
        mock_client = _make_mock_client()
        source = MootdxSource(client=mock_client)
        assert source._get_client() is mock_client

    def test_fallback_to_singleton_when_injected_closed(self):
        """注入的 client 已关闭时，应回退到全局单例"""
        closed_client = _make_mock_client(closed=True)
        source = MootdxSource(client=closed_client)
        with patch("src.datasource.mootdx_source.get_quotes_client") as mock_singleton:
            mock_singleton.return_value = _make_mock_client()
            result = source._get_client()
            mock_singleton.assert_called_once()
            assert result is mock_singleton.return_value

    def test_fallback_to_singleton_when_no_injection(self):
        """未注入 client 时，应使用全局单例"""
        source = MootdxSource()
        with patch("src.datasource.mootdx_source.get_quotes_client") as mock_singleton:
            mock_singleton.return_value = _make_mock_client()
            result = source._get_client()
            mock_singleton.assert_called_once()
            assert result is mock_singleton.return_value

    def test_get_stock_info_uses_injected_client(self):
        """get_stock_info 应通过注入的 client 获取数据"""
        mock_client = _make_mock_client()
        source = MootdxSource(client=mock_client)

        # Mock quotes 返回价格
        import pandas as pd
        quotes_df = pd.DataFrame({"price": [15.0]})
        mock_client.quotes.return_value = quotes_df

        # Mock finance 返回总股本
        finance_df = pd.DataFrame({"zongguben": [100_0000_0000]})
        mock_client.finance.return_value = finance_df

        result = source.get_stock_info("600000")
        assert result is not None
        assert result.current_price == 15.0
        assert result.total_shares == 100_0000_0000
        mock_client.quotes.assert_called_once_with(symbol="600000")
        mock_client.finance.assert_called_once_with(symbol="600000")
