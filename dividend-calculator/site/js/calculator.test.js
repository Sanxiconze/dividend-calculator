#!/usr/bin/env node
/* calculator.js 纯函数单元测试 — 对齐 tests/test_pr_calculator.py + test_fiscal_year.py
 * 运行: node --test site/js/calculator.test.js  （Node 18+ 内置 test runner） */
'use strict';
const { test } = require('node:test');
const assert = require('node:assert');
const path = require('path');
const Calc = require(path.join(__dirname, 'calculator.js'));

function round2(v) { return Math.round(v * 100) / 100; }

// ---- computeBasicPR ----
test('computeBasicPR 正常', () => assert.equal(Calc.computeBasicPR(10, 15.0), round2(10 / 15.0)));
test('computeBasicPR pe为null', () => assert.equal(Calc.computeBasicPR(null, 15.0), null));
test('computeBasicPR roe为null', () => assert.equal(Calc.computeBasicPR(10, null), null));
test('computeBasicPR roe为0', () => assert.equal(Calc.computeBasicPR(10, 0.0), null));
test('computeBasicPR roe为负', () => assert.equal(Calc.computeBasicPR(10, -5.0), null));

// ---- computeCorrectedPR ----
test('computeCorrectedPR 正常', () => assert.equal(Calc.computeCorrectedPR(10, 15.0, 1.5), round2(1.5 * 10 / 15.0)));
test('computeCorrectedPR nFactor为null', () => assert.equal(Calc.computeCorrectedPR(10, 15.0, null), null));
test('computeCorrectedPR pe为null', () => assert.equal(Calc.computeCorrectedPR(null, 15.0, 1.0), null));
test('computeCorrectedPR roe为0', () => assert.equal(Calc.computeCorrectedPR(10, 0.0, 1.0), null));

// ---- computePbPR ----
test('computePbPR 正常', () => assert.equal(Calc.computePbPR(2.0, 15.0), round2(2 / (0.15 ** 2) / 100)));
test('computePbPR pb为null', () => assert.equal(Calc.computePbPR(null, 15.0), null));
test('computePbPR roe为null', () => assert.equal(Calc.computePbPR(2.0, null), null));
test('computePbPR roe为0', () => assert.equal(Calc.computePbPR(2.0, 0.0), null));

// ---- computeNFactor ----
test('computeNFactor null', () => assert.equal(Calc.computeNFactor(null), null));
test('computeNFactor 0 → 2.0', () => assert.equal(Calc.computeNFactor(0.0), 2.0));
test('computeNFactor 负 → 2.0', () => assert.equal(Calc.computeNFactor(-0.1), 2.0));
test('computeNFactor 高支付率→1.0', () => assert.equal(Calc.computeNFactor(0.60), 1.0));
test('computeNFactor 低支付率→2.0', () => assert.equal(Calc.computeNFactor(0.20), 2.0));
test('computeNFactor 中支付率 0.40→1.25', () => assert.equal(Calc.computeNFactor(0.40), 1.25));
test('computeNFactor 边界0.50→1.0', () => assert.equal(Calc.computeNFactor(0.50), 1.0));
test('computeNFactor 边界0.25→2.0', () => assert.equal(Calc.computeNFactor(0.25), 2.0));

// ---- classifyValuation ----
test('classifyValuation 低估', () => assert.equal(Calc.classifyValuation(0.3), '低估'));
test('classifyValuation 合理偏低', () => assert.equal(Calc.classifyValuation(0.6), '合理偏低'));
test('classifyValuation 合理', () => assert.equal(Calc.classifyValuation(0.85), '合理'));
test('classifyValuation 高估', () => assert.equal(Calc.classifyValuation(1.5), '高估'));
test('classifyValuation null', () => assert.equal(Calc.classifyValuation(null), '无法判定'));
test('classifyValuation 边界0.5', () => assert.equal(Calc.classifyValuation(0.5), '低估'));
test('classifyValuation 边界0.7', () => assert.equal(Calc.classifyValuation(0.7), '合理偏低'));
test('classifyValuation 边界1.0', () => assert.equal(Calc.classifyValuation(1.0), '合理'));

// ---- classifyIndustry ----
test('classifyIndustry 周期行业', () => {
  const r = Calc.classifyIndustry('煤炭开采');
  assert.equal(r.isCyclical, true);
  assert.equal(r.isTech, false);
  assert.ok(r.warning.includes('周期行业'));
});
test('classifyIndustry 科技行业', () => {
  const r = Calc.classifyIndustry('半导体设备');
  assert.equal(r.isCyclical, false);
  assert.equal(r.isTech, true);
  assert.ok(r.warning.includes('科技行业'));
});
test('classifyIndustry 普通行业', () => {
  const r = Calc.classifyIndustry('食品饮料');
  assert.equal(r.isCyclical, false);
  assert.equal(r.isTech, false);
  assert.equal(r.warning, '');
});
test('classifyIndustry 空字符串', () => {
  const r = Calc.classifyIndustry('');
  assert.equal(r.isCyclical, false);
  assert.equal(r.isTech, false);
});

// ---- inferFiscalYear（对齐 tests/test_fiscal_year.py）----
test('inferFiscalYear 3-8月除权→上年度年报', () => {
  assert.deepEqual(Calc.inferFiscalYear(2024, 3), { year: 2023, isAnnual: true });
  assert.deepEqual(Calc.inferFiscalYear(2024, 8), { year: 2023, isAnnual: true });
});
test('inferFiscalYear 9-12月除权→当年度中报', () => {
  assert.deepEqual(Calc.inferFiscalYear(2024, 9), { year: 2024, isAnnual: false });
  assert.deepEqual(Calc.inferFiscalYear(2024, 12), { year: 2024, isAnnual: false });
});
test('inferFiscalYear 1-2月除权→上年度中报', () => {
  assert.deepEqual(Calc.inferFiscalYear(2024, 1), { year: 2023, isAnnual: false });
  assert.deepEqual(Calc.inferFiscalYear(2024, 2), { year: 2023, isAnnual: false });
});

// ---- calculateDividendYield ----
test('calculateDividendYield 三档税率', () => {
  const [a, b, c] = Calc.calculateDividendYield(100, 1000);
  assert.equal(a, 10);
  assert.equal(b, 9);
  assert.equal(c, 8);
});
test('calculateDividendYield 零市值', () => {
  assert.deepEqual(Calc.calculateDividendYield(100, 0), [0, 0, 0]);
});

// ---- parseDividendRecords ----
test('parseDividendRecords 半年报+年报合并同财年', () => {
  const rows = [
    { REPORT_DATE: '2025-12-31 00:00:00', PRETAX_BONUS_RMB: 7.9, ASSIGN_PROGRESS: '实施分配' },
    { REPORT_DATE: '2025-06-30 00:00:00', PRETAX_BONUS_RMB: 2.1, ASSIGN_PROGRESS: '实施分配' },
    { REPORT_DATE: '2024-12-31 00:00:00', PRETAX_BONUS_RMB: 8.2, ASSIGN_PROGRESS: '实施分配' },
  ];
  const r = Calc.parseDividendRecords(rows, 1000);
  assert.equal(r.year, '2025');
  assert.equal(r.totalDividend, (7.9 + 2.1) / 10 * 1000);
  assert.equal(r.details.length, 2);
});
test('parseDividendRecords 排除预披露', () => {
  const rows = [
    { REPORT_DATE: '2025-12-31 00:00:00', PRETAX_BONUS_RMB: 5, ASSIGN_PROGRESS: '预披露' },
    { REPORT_DATE: '2024-12-31 00:00:00', PRETAX_BONUS_RMB: 3, ASSIGN_PROGRESS: '实施分配' },
  ];
  const r = Calc.parseDividendRecords(rows, 1000);
  assert.equal(r.year, '2024');
  assert.equal(r.totalDividend, 3 / 10 * 1000);
});
test('parseDividendRecords 无分红', () => {
  const r = Calc.parseDividendRecords([], 1000);
  assert.equal(r.totalDividend, 0);
  assert.equal(r.year, null);
});

// ---- parseFinancials（TTM = 最新累计 + 上年全年 - 上年同期）----
test('parseFinancials ROE中位数与TTM', () => {
  const rows = [
    { REPORT_DATE: '2026-03-31 00:00:00', ROEJQ: '9.0', PARENTNETPROFIT: '67.61' },
    { REPORT_DATE: '2025-12-31 00:00:00', ROEJQ: '15.9', PARENTNETPROFIT: '345.03' },
    { REPORT_DATE: '2025-03-31 00:00:00', ROEJQ: '4.0', PARENTNETPROFIT: '51.81' },
    { REPORT_DATE: '2024-12-31 00:00:00', ROEJQ: '13.5', PARENTNETPROFIT: '324.96' },
    { REPORT_DATE: '2023-12-31 00:00:00', ROEJQ: '13.0', PARENTNETPROFIT: '272.39' },
    { REPORT_DATE: '2022-12-31 00:00:00', ROEJQ: '12.0', PARENTNETPROFIT: '213.59' },
  ];
  const r = Calc.parseFinancials(rows);
  assert.equal(r.roeLatest, 15.9);
  assert.equal(r.roe5yMedian, 13.5);  // 4个年报 [12,13,13.5,15.9] 取中间位 → 13.5
  assert.ok(Math.abs(r.netProfitTtm - (67.61 + 345.03 - 51.81)) < 1e-6);
});
