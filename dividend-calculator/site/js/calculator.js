/* 计算逻辑 JS 移植 — 对齐 src/pr_calculator.py / src/utils.py / src/dividend.py
 * 纯函数，无网络依赖，浏览器与 Node(verify) 共用。 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.Calculator = factory();
  }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var CYCLICAL_INDUSTRIES = [
    '煤炭', '钢铁', '有色金属', '石油', '化工', '航运', '建材',
    '水泥', '玻璃', '造纸', '养殖', '房地产', '工程机械', '船舶',
    '化肥', '农药', '化纤', '橡胶', '塑料',
  ];

  var TECH_INDUSTRIES = [
    '半导体', '软件', '互联网', '计算机', '通信', '电子',
    '芯片', '人工智能', '云计算', '大数据',
  ];

  function inferFiscalYear(year, month) {
    /* 3-8月除权 → 上年度年报；9-12月 → 当年中报；1-2月 → 上年度中报 */
    if (month >= 3 && month <= 8) {
      return { year: year - 1, isAnnual: true };
    } else if (month >= 9) {
      return { year: year, isAnnual: false };
    } else {
      return { year: year - 1, isAnnual: false };
    }
  }

  function reportTime(year, isAnnual) {
    return year + (isAnnual ? '年报' : '中报');
  }

  /* 报告期 → 展示标签（对齐 _report_label）：12→年报，6→半年报，3→一季报，9→三季报 */
  function reportLabel(reportDate) {
    var m = /^(\d{4})-(\d{2})/.exec(reportDate || '');
    if (!m) return String(reportDate || '').slice(0, 10);
    var y = m[1];
    var mon = parseInt(m[2], 10);
    if (mon === 12) return y + '年报';
    if (mon === 6) return y + '半年报';
    if (mon === 3) return y + '一季报';
    if (mon === 9) return y + '三季报';
    return y + '-' + m[2];
  }

  function pad2(n) { return n < 10 ? '0' + n : String(n); }

  function fmtYMD(d) {
    return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate());
  }

  /* TTM 窗口: (ref-365天, ref]，返回 [startStr(窗口起点), refStr] */
  function ttmWindow(ref) {
    var cutoff = new Date(ref);
    cutoff.setDate(cutoff.getDate() - 365);
    var start = new Date(ref);
    start.setDate(start.getDate() - 364);
    return [fmtYMD(start), fmtYMD(ref)];
  }

  function calculateDividendYield(totalDividend, totalMarketCap) {
    if (totalMarketCap <= 0) return [0.0, 0.0, 0.0];
    var before = (totalDividend / totalMarketCap) * 100;
    return [before, before * 0.9, before * 0.8];
  }

  /* ── 分红解析（对齐 _parse_fhps_detail，输入为东财 RPT_SHAREBONUS_DET 行）──
   * 行字段: REPORT_DATE (YYYY-MM-DD ...), PRETAX_BONUS_RMB (每10股派息),
   *         EX_DIVIDEND_DATE (除权除息日)
   * TTM: 只统计除权除息日落在 (refDate-365天, refDate] 窗口内的已除权分红。
   * 返回: { totalDividend, year(最近分红标签), details:[{report_time, dividend_per_10}],
   *        explanation }
   */
  function parseDividendRecords(rows, totalShares, refDate) {
    var ref = refDate || new Date();
    var win = ttmWindow(ref);
    var startStr = win[0], refStr = win[1];

    var records = [];
    for (var i = 0; i < rows.length; i++) {
      var row = rows[i];
      if (row.ASSIGN_PROGRESS === '预披露') continue;
      var dp10 = Number(row.PRETAX_BONUS_RMB);
      if (!(dp10 > 0)) continue;
      var ex = String(row.EX_DIVIDEND_DATE || '').slice(0, 10);
      if (!/^\d{4}-\d{2}-\d{2}$/.test(ex)) continue;
      if (!(ex > startStr && ex <= refStr)) continue;
      records.push({ ex: ex, dp10: dp10, label: reportLabel(row.REPORT_DATE) });
    }

    if (!records.length) {
      return { totalDividend: 0, year: null, details: [], explanation: '近12个月(' + startStr + '至' + refStr + ')无已除权分红' };
    }

    records.sort(function (a, b) { return a.ex < b.ex ? -1 : 1; });

    var totalPer10 = 0;
    for (var j = 0; j < records.length; j++) totalPer10 += records[j].dp10;
    var dps = totalPer10 / 10.0;
    var totalDividend = dps * totalShares;

    var details = records.map(function (r) {
      return { report_time: r.label, dividend_per_10: r.dp10 };
    });
    var latest = records[records.length - 1];

    var list = details.map(function (d) {
      return d.report_time + ': 10派' + pyFloat(d.dividend_per_10) + '元';
    });
    var explanation = '近12个月(' + startStr + '至' + refStr + ')除权分红：' + list.join('，') +
      '，合计10派' + totalPer10.toFixed(3) + '元(每股' + dps.toFixed(4) + '元)，' +
      '总股本' + (totalShares / 1e8).toFixed(2) + '亿股，' +
      '总分红' + (totalDividend / 1e8).toFixed(2) + '亿元';

    return { totalDividend: totalDividend, year: latest.label, details: details, explanation: explanation };
  }

  /* ── 财务数据（对齐 pr.py _get_financial，输入为东财 RPT_F10_FINANCE_MAINFINADATA 行）
   * PARENTNETPROFIT 为累计值(YTD)，TTM 用最近报告期补齐上年同期。 */
  function parseFinancials(rows) {
    if (!rows.length) return { roeLatest: null, roe5yMedian: null, netProfitTtm: null, netProfitAnnual: null };

    /* 严格数值判断：空字符串/空白/null 视为缺失（Number('')===0 会污染中位数） */
    function toNum(v) {
      if (v == null || String(v).trim() === '') return NaN;
      return Number(v);
    }

    var annual = rows
      .filter(function (r) { return (r.REPORT_DATE || '').slice(5, 10) === '12-31'; })
      .filter(function (r) { return isFinite(toNum(r.ROEJQ)); })
      .map(function (r) {
        return { year: parseInt(r.REPORT_DATE.slice(0, 4), 10), roe: Number(r.ROEJQ) };
      })
      .sort(function (a, b) { return b.year - a.year; });

    var roeLatest = annual.length ? annual[0].roe : null;
    var roe5yMedian = null;
    if (annual.length) {
      var last5 = annual.slice(0, Math.min(5, annual.length)).map(function (a) { return a.roe; });
      var sorted = last5.slice().sort(function (a, b) { return a - b; });
      roe5yMedian = sorted[Math.floor(sorted.length / 2)];
    }

    var netProfitAnnual = null;
    if (annual.length) {
      var latestAnnual = annual[0];
      for (var i = 0; i < rows.length; i++) {
        var r = rows[i];
        if ((r.REPORT_DATE || '').slice(0, 10) === latestAnnual.year + '-12-31' && isFinite(toNum(r.PARENTNETPROFIT))) {
          netProfitAnnual = Number(r.PARENTNETPROFIT);
          break;
        }
      }
    }

    var netProfitTtm = null;
    var dated = rows
      .map(function (r) {
        var dt = (r.REPORT_DATE || '').slice(0, 10);
        return { date: dt, np: toNum(r.PARENTNETPROFIT) };
      })
      .filter(function (r) { return r.date.length === 10 && isFinite(r.np); })
      .sort(function (a, b) { return a.date < b.date ? -1 : 1; });

    if (dated.length) {
      var latest = dated[dated.length - 1];
      var latestYear = parseInt(latest.date.slice(0, 4), 10);
      var latestMonthDay = latest.date.slice(5);
      /* 上年完整财年 + 本年至今 − 上年同期 */
      var prevYear = null, prevSamePeriod = null;
      for (var k = dated.length - 1; k >= 0; k--) {
        var d = dated[k];
        if (d.date.slice(5) === '12-31' && d.date.slice(0, 4) !== String(latestYear)) { prevYear = d.np; break; }
      }
      if (latestMonthDay !== '12-31') {
        var targetPrev = (latestYear - 1) + '-' + latestMonthDay;
        for (var k2 = dated.length - 1; k2 >= 0; k2--) {
          if (dated[k2].date === targetPrev) { prevSamePeriod = dated[k2].np; break; }
        }
        if (prevYear != null && prevSamePeriod != null) {
          netProfitTtm = latest.np + prevYear - prevSamePeriod;
        }
      } else {
        netProfitTtm = latest.np;
      }
    }

    return { roeLatest: roeLatest, roe5yMedian: roe5yMedian, netProfitTtm: netProfitTtm, netProfitAnnual: netProfitAnnual };
  }

  /* ── 市赚率（对齐 pr_calculator.py）── */
  function computeBasicPR(peTtm, roe) {
    if (peTtm == null || roe == null || roe <= 0) return null;
    return round2(peTtm / roe);
  }

  function computeCorrectedPR(peTtm, roe, nFactor) {
    if (peTtm == null || roe == null || roe <= 0 || nFactor == null) return null;
    return round2(nFactor * peTtm / roe);
  }

  function computePbPR(pb, roe) {
    if (pb == null || roe == null || roe <= 0) return null;
    var roeDecimal = roe / 100.0;
    return round2(pb / (roeDecimal * roeDecimal) / 100.0);
  }

  function computeNFactor(payoutRatio) {
    if (payoutRatio == null) return null;
    if (payoutRatio <= 0) return 2.0;
    var raw = 0.50 / payoutRatio;
    return Math.max(1.0, Math.min(2.0, raw));
  }

  function classifyValuation(pr) {
    if (pr == null) return '无法判定';
    if (pr <= 0.5) return '低估';
    if (pr <= 0.7) return '合理偏低';
    if (pr <= 1.0) return '合理';
    return '高估';
  }

  function classifyIndustry(industry) {
    var isCyclical = false, isTech = false;
    for (var i = 0; i < CYCLICAL_INDUSTRIES.length; i++) {
      if (industry.indexOf(CYCLICAL_INDUSTRIES[i]) !== -1) { isCyclical = true; break; }
    }
    for (var j = 0; j < TECH_INDUSTRIES.length; j++) {
      if (industry.indexOf(TECH_INDUSTRIES[j]) !== -1) { isTech = true; break; }
    }
    var warning = '';
    if (isCyclical) {
      warning = '该股属于周期行业，修正市赚率仅供参考；建议优先参考PB-市赚率';
    } else if (isTech) {
      warning = '该股属于科技行业，修正市赚率可能不适用（科技股常以回购代替分红）';
    }
    return { isCyclical: isCyclical, isTech: isTech, warning: warning };
  }

  /* 综合市赚率（对齐 pr.py calculate_pr 的核心计算段） */
  function computePr(input) {
    var pe = input.pe_ttm, pb = input.pb, roe = input.roe_latest;
    var netProfitAnnual = input.net_profit_annual, dividendTotal = input.dividend_total;

    var isLossStock = netProfitAnnual != null && netProfitAnnual <= 0;

    var payoutRatio = null, nFactor = null;
    if (netProfitAnnual != null && netProfitAnnual > 0 && dividendTotal != null) {
      payoutRatio = dividendTotal / netProfitAnnual;
      nFactor = computeNFactor(payoutRatio);
    }

    var prBasic = null, prCorrected = null, prPb = null;
    var valuationZone = '无法判定';
    if (!isLossStock && pe != null && roe != null && roe > 0) {
      prBasic = computeBasicPR(pe, roe);
      prCorrected = computeCorrectedPR(pe, roe, nFactor);
      prPb = computePbPR(pb, roe);
      valuationZone = classifyValuation(prCorrected != null ? prCorrected : prBasic);
    }

    return {
      pr_basic: prBasic,
      pr_corrected: prCorrected,
      pr_pb: prPb,
      valuation_zone: valuationZone,
      payout_ratio: payoutRatio,
      n_factor: nFactor,
      is_loss_stock: isLossStock,
    };
  }

  function round2(v) { return Math.round(v * 100) / 100; }

  /* Python str(float) 风格: 1.0 → "1.0", 2.332 → "2.332", 7.9 → "7.9" */
  function pyFloat(v) {
    if (Number.isInteger(v)) return v.toFixed(1);
    return String(v);
  }

  return {
    inferFiscalYear: inferFiscalYear,
    reportTime: reportTime,
    reportLabel: reportLabel,
    fmtYMD: fmtYMD,
    calculateDividendYield: calculateDividendYield,
    parseDividendRecords: parseDividendRecords,
    parseFinancials: parseFinancials,
    computeBasicPR: computeBasicPR,
    computeCorrectedPR: computeCorrectedPR,
    computePbPR: computePbPR,
    computeNFactor: computeNFactor,
    classifyValuation: classifyValuation,
    classifyIndustry: classifyIndustry,
    computePr: computePr,
    round2: round2,
    CYCLICAL_INDUSTRIES: CYCLICAL_INDUSTRIES,
    TECH_INDUSTRIES: TECH_INDUSTRIES,
  };
}));
