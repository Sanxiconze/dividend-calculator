#!/usr/bin/env node
/* JS fixture runner — 从 fixture JSON 读取原始数据，用 JS 纯计算逻辑出结果。
 * fixture 由 scripts/verify_js_vs_python.py 生成（与 Python 走相同 HTTP 接口）。
 * 用法: node site/js/verify_raw.js <fixture.json> */
'use strict';
var path = require('path');
var App = require(path.join(__dirname, 'app.js'));

var fixturePath = process.argv[2];
if (!fixturePath) {
  console.error('用法: node site/js/verify_raw.js <fixture.json>');
  process.exit(1);
}

var fixture = JSON.parse(require('fs').readFileSync(fixturePath, 'utf8'));
var out = {};

Object.keys(fixture.stocks || {}).forEach(function (code) {
  var raw = fixture.stocks[code];
  try {
    var r = App.computeFromRaw(raw);
    out[code] = {
      stock_code: r.stock_info.stock_code,
      stock_name: r.stock_info.stock_name,
      current_price: r.stock_info.current_price,
      total_shares: r.stock_info.total_shares,
      pe_ttm: r.stock_info.pe_ttm,
      pb: r.stock_info.pb,
      dividend_year: r.dividend.dividend_year,
      total_dividend: r.dividend.total_dividend,
      dividend_yield_before_tax: r.dividend.dividend_yield_before_tax,
      dividend_yield_after_tax_10: r.dividend.dividend_yield_after_tax_10,
      dividend_yield_after_tax_20: r.dividend.dividend_yield_after_tax_20,
      explanation: r.dividend.explanation,
      pr_basic: r.pr.pr_basic,
      pr_corrected: r.pr.pr_corrected,
      pr_pb: r.pr.pr_pb,
      valuation_zone: r.pr.valuation_zone,
      pr_warning: r.pr.pr_warning,
      payout_ratio: r.pr.payout_ratio,
      n_factor: r.pr.n_factor,
      roe_latest: r.pr.roe_latest,
      roe_5y_median: r.pr.roe_5y_median,
      net_profit_ttm: r.pr.net_profit_ttm,
      net_profit_annual: r.pr.net_profit_annual,
      industry: r.pr.industry,
      is_loss_stock: r.pr.is_loss_stock,
    };
  } catch (e) {
    out[code] = { stock_code: code, error: String(e.message || e) };
  }
});

console.log(JSON.stringify(out, null, 2));
