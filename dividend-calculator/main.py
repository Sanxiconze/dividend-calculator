"""
真实股息率计算工具 - 主入口
完全使用真实数据，不虚构任何数据
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.dividend import calculate_true_dividend_yield


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("="*60)
        print("真实股息率计算工具")
        print("="*60)
        print("用法: python -m src.main <股票代码或名称>")
        print("示例: python -m src.main 600919")
        print("      python -m src.main 江苏银行")
        print("\n注意: 完全使用真实数据，不虚构任何数据")
        print("="*60)
        return

    stock_input = sys.argv[1]

    print("="*60)
    print(f"真实股息率计算: {stock_input}")
    print("="*60)

    # 计算
    result = calculate_true_dividend_yield(stock_input)

    if result is None:
        print("\n计算失败，请检查股票代码或网络连接")
        return

    # 输出结果
    print("\n" + "="*60)
    print("计算结果")
    print("="*60)

    if result.stock_name:
        print(f"股票: {result.stock_name} ({result.stock_code})")
    else:
        print(f"股票代码: {result.stock_code}")

    print()

    if result.total_dividend <= 0:
        print(f"无有效分红数据: {result.explanation}")
        return

    print(f"最新分红年度: {result.latest_year}")
    print(f"近一年现金分红总额: {result.total_dividend/100000000:.2f} 亿元")
    print(f"当前总市值: {result.total_market_cap/100000000:.2f} 亿元")
    print()
    print(f"真实股息率(含税): {result.dividend_yield_before_tax:.2f}%")
    print(f"真实股息率(扣税10%后): {result.dividend_yield_after_tax:.2f}%")
    print()
    print("计算说明:")
    print(f"  {result.explanation}")
    print()
    print("="*60)


if __name__ == "__main__":
    main()
