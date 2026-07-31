#!/usr/bin/env node
/* JS fixture runner — 从 fixture JSON 读取原始数据，用 JS 纯计算逻辑出结果。
 * fixture 由 scripts/verify_js_vs_python.py 生成（与 Python 走相同 HTTP 接口）。
 * 用法: node site/js/verify_raw.js <fixture.json> */
'use strict';
var path = require('path');
var App = require(path.join(__dirname, 'app.js'));
var formatResult = require(path.join(__dirname, 'formatResult.js'));

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
    out[code] = formatResult(App.computeFromRaw(raw));
  } catch (e) {
    out[code] = { stock_code: code, error: String(e.message || e) };
  }
});

console.log(JSON.stringify(out, null, 2));
