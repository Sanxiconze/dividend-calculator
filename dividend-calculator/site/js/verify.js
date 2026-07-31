#!/usr/bin/env node
/* JS 实现验证脚本 — 对指定股票跑完整 JS 管线，输出 JSON 结果。
 * 用法: node site/js/verify.js <代码1> <代码2> ...
 * 输出与 src/main.py / calc_pr.py 的字段对齐，供 verify_js_vs_python.py 对比。 */
'use strict';
var path = require('path');
var App = require(path.join(__dirname, 'app.js'));

var codes = process.argv.slice(2);
if (!codes.length) {
  console.error('用法: node site/js/verify.js <股票代码>...');
  process.exit(1);
}

function fmtPr(v) { return v == null ? null : Math.round(v * 100) / 100; }
function fmtYield(v) { return v == null ? null : Math.round(v * 10000) / 10000; }

Promise.all(codes.map(function (code) {
  return App.analyzeStock(code).then(function (r) {
    return {
      stock_code: r.stock_info.stock_code,
      stock_name: r.stock_info.stock_name,
      current_price: r.stock_info.current_price,
      total_shares: r.stock_info.total_shares,
      pe_ttm: r.stock_info.pe_ttm,
      pb: r.stock_info.pb,
      dividend_year: r.dividend.dividend_year,
      total_dividend: Math.round(r.dividend.total_dividend * 100) / 100,
      dividend_yield_before_tax: fmtYield(r.dividend.dividend_yield_before_tax),
      dividend_yield_after_tax_10: fmtYield(r.dividend.dividend_yield_after_tax_10),
      dividend_yield_after_tax_20: fmtYield(r.dividend.dividend_yield_after_tax_20),
      explanation: r.dividend.explanation,
      pr_basic: fmtPr(r.pr.pr_basic),
      pr_corrected: fmtPr(r.pr.pr_corrected),
      pr_pb: fmtPr(r.pr.pr_pb),
      valuation_zone: r.pr.valuation_zone,
      pr_warning: r.pr.pr_warning,
      payout_ratio: r.pr.payout_ratio == null ? null : Math.round(r.pr.payout_ratio * 10000) / 10000,
      n_factor: fmtPr(r.pr.n_factor),
      roe_latest: r.pr.roe_latest,
      roe_5y_median: r.pr.roe_5y_median,
      net_profit_ttm: Math.round(r.pr.net_profit_ttm * 100) / 100,
      net_profit_annual: Math.round(r.pr.net_profit_annual * 100) / 100,
      industry: r.pr.industry,
      is_loss_stock: r.pr.is_loss_stock,
    };
  }).catch(function (err) {
    return { stock_code: code, error: String(err.message || err) };
  });
})).then(function (results) {
  console.log(JSON.stringify(results, null, 2));
}).catch(function (err) {
  console.error('FATAL:', err);
  process.exit(1);
});
