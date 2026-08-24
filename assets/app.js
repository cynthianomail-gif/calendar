/* 全球連假雷達 ------------------------------------------------------------
   資料來自 data/holidays.js（由 scripts/build_holidays.py 產生）。
   全部在瀏覽器端計算，沒有任何外部請求。
------------------------------------------------------------------------- */
(function () {
  "use strict";

  var DATA = window.HOLIDAY_DATA;
  var TRAVEL_W = { high: 1, mid: 0.55, low: 0.25 };
  var LEVEL_CUTS = [15, 35, 60, 80];
  var LEVELS = [
    { name: "人潮平穩", desc: "主要客源國這段時間都在上班，是相對好走的時機。" },
    { name: "稍微熱鬧", desc: "有少數國家放假，熱門景點會比平常多一些人。" },
    { name: "有點擁擠", desc: "有國家正在放連假，建議提早訂機票與住宿。" },
    { name: "相當擁擠", desc: "多個客源國同時連假，機票住宿會漲價、景點排隊變長。" },
    { name: "極度擁擠", desc: "全球級的旅遊高峰，能避開就避開；非去不可請盡早訂位。" }
  ];
  var WD = ["日", "一", "二", "三", "四", "五", "六"];

  /* -------------------------------------------------------- 日期小工具 */
  function ymd(dt) {
    var m = dt.getMonth() + 1, d = dt.getDate();
    return dt.getFullYear() + "-" + (m < 10 ? "0" : "") + m + "-" + (d < 10 ? "0" : "") + d;
  }
  function parse(s) {
    var p = s.split("-");
    return new Date(+p[0], +p[1] - 1, +p[2]);
  }
  function addDays(dt, n) {
    var x = new Date(dt.getTime());
    x.setDate(x.getDate() + n);
    return x;
  }
  function diffDays(a, b) {
    return Math.round((b - a) / 86400000);
  }
  function fmtShort(s) {
    var d = parse(s);
    return (d.getMonth() + 1) + "/" + d.getDate();
  }
  function fmtRange(a, b) {
    var da = parse(a), db = parse(b);
    var out = (da.getMonth() + 1) + "/" + da.getDate() + "（" + WD[da.getDay()] + "）";
    if (a !== b) out += " – " + (db.getMonth() + 1) + "/" + db.getDate() + "（" + WD[db.getDay()] + "）";
    return out;
  }
  function levelOf(score) {
    for (var i = 0; i < LEVEL_CUTS.length; i++) if (score < LEVEL_CUTS[i]) return i;
    return 4;
  }

  /* -------------------------------------------------------- 建立索引 */
  var META = {};
  DATA.countries.forEach(function (c) { META[c.code] = c; });

  var RANGE_START = parse(DATA.years[0] + "-01-01");
  var RANGE_END = parse(DATA.years[DATA.years.length - 1] + "-12-31");
  var TOTAL_DAYS = diffDays(RANGE_START, RANGE_END) + 1;

  var IDX = {};   // code -> { days: {iso: [entry]}, runLen: {iso: n}, run: {iso: {start,end,len}} }

  function hasStatutory(entries) {
    if (!entries) return false;
    for (var i = 0; i < entries.length; i++) if (entries[i].kind !== "season") return true;
    return false;
  }

  function isWeekend(country, dt) {
    var py = (dt.getDay() + 6) % 7;            // 0=週一 … 6=週日
    var wk = country.weekend || [5, 6];
    return wk.indexOf(py) !== -1;
  }

  DATA.countries.forEach(function (c) {
    var days = {}, i, dstr;
    (DATA.holidays[c.code] || []).forEach(function (e) {
      var s = parse(e.start), en = parse(e.end);
      for (var d = s; d <= en; d = addDays(d, 1)) {
        dstr = ymd(d);
        (days[dstr] || (days[dstr] = [])).push(e);
      }
    });

    // 連假偵測：把「假日 + 週末」連成一段
    var runLen = {}, run = {}, cur = null, runs = [];
    for (i = 0; i < TOTAL_DAYS; i++) {
      var dt = addDays(RANGE_START, i);
      dstr = ymd(dt);
      var off = hasStatutory(days[dstr]) || isWeekend(c, dt);
      if (off) {
        if (!cur) { cur = { start: dstr, end: dstr, len: 1, days: [dstr] }; runs.push(cur); }
        else { cur.end = dstr; cur.len++; cur.days.push(dstr); }
      } else cur = null;
    }
    runs.forEach(function (r) {
      r.days.forEach(function (ds) { runLen[ds] = r.len; run[ds] = r; });
    });

    IDX[c.code] = { days: days, runLen: runLen, run: run };
  });

  /* -------------------------------------------------------- 擁擠度計算 */
  var scoreCache = {};

  // 季節性旺季（暑假、盂蘭盆節…）是「整段期間都比較擠」，
  // 不像法定連假會造成單日尖峰，因此給固定的溫和權重。
  function entryImpact(code, entry, runLen) {
    var w = META[code].weight;
    if (entry.kind === "season") return w * 0.3;
    return w * TRAVEL_W[entry.travel] * (1 + Math.min(runLen, 10) * 0.08);
  }

  function contributions(dstr, codes) {
    var out = [];
    for (var i = 0; i < codes.length; i++) {
      var code = codes[i];
      var es = IDX[code].days[dstr];
      if (!es) continue;
      var len = IDX[code].runLen[dstr] || 1;
      var best = null, bestImpact = 0;
      for (var j = 0; j < es.length; j++) {
        var imp = entryImpact(code, es[j], len);
        if (imp > bestImpact) { bestImpact = imp; best = es[j]; }
      }
      if (!best) continue;
      out.push({
        code: code,
        entries: es,
        best: best,
        run: best.kind === "season" ? null : IDX[code].run[dstr],
        runLen: len,
        impact: bestImpact
      });
    }
    out.sort(function (a, b) { return b.impact - a.impact; });
    return out;
  }

  function dayScore(dstr, codes, key) {
    var ck = key + "|" + dstr;
    if (scoreCache[ck] !== undefined) return scoreCache[ck];
    var parts = contributions(dstr, codes), raw = 0;
    for (var i = 0; i < parts.length; i++) raw += parts[i].impact;
    var s = Math.round(100 * (1 - Math.exp(-raw / 250)));
    scoreCache[ck] = s;
    return s;
  }

  function tripScore(startStr, len, codes, key) {
    var sum = 0, max = 0, d = parse(startStr);
    for (var i = 0; i < len; i++) {
      var s = dayScore(ymd(d), codes, key);
      sum += s;
      if (s > max) max = s;
      d = addDays(d, 1);
    }
    return Math.round(0.6 * (sum / len) + 0.4 * max);
  }

  /* -------------------------------------------------------- 狀態 */
  var REGIONS = [];
  DATA.countries.forEach(function (c) {
    if (REGIONS.indexOf(c.region) === -1) REGIONS.push(c.region);
  });

  var state = {
    start: null,
    end: null,
    selected: null,           // Set 形式（用物件模擬以求相容性）
    month: null,
    countryYear: DATA.years[0],
    search: ""
  };

  function loadSelection() {
    var all = {};
    DATA.countries.forEach(function (c) { all[c.code] = true; });
    try {
      var raw = localStorage.getItem("hr.selected");
      if (raw) {
        var arr = JSON.parse(raw), sel = {}, any = false;
        arr.forEach(function (code) { if (META[code]) { sel[code] = true; any = true; } });
        if (any) return sel;
      }
    } catch (e) { /* 隱私模式或被封鎖，忽略 */ }
    return all;
  }
  function saveSelection() {
    try {
      localStorage.setItem("hr.selected", JSON.stringify(activeCodes()));
    } catch (e) { /* 忽略 */ }
  }
  function activeCodes() {
    return DATA.countries.filter(function (c) { return state.selected[c.code]; })
      .map(function (c) { return c.code; });
  }
  function filterKey() { return activeCodes().join(","); }

  /* -------------------------------------------------------- DOM 工具 */
  function $(id) { return document.getElementById(id); }
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }
  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

  function travelTag(entry) {
    if (entry.kind === "season") return { cls: "tag season", text: "旅遊旺季" };
    if (entry.travel === "high") return { cls: "tag hot", text: "重量級連假" };
    if (entry.travel === "mid") return { cls: "tag warm", text: "一般假日" };
    return null;
  }

  function entryRow(code, part) {
    var c = META[code];
    var row = el("div", "row");
    row.appendChild(el("span", "flag", c.flag));
    var body = el("div", "body");
    var names = part.entries.map(function (e) { return e.name; }).join("、");
    body.appendChild(el("b", null, c.name + "・" + names));

    var p = el("p");
    if (part.best.kind === "season") {
      var slen = Math.round((parse(part.best.end) - parse(part.best.start)) / 86400000) + 1;
      p.textContent = fmtRange(part.best.start, part.best.end) + "，整段共 " + slen + " 天";
    } else if (part.run && part.run.len >= 3) {
      p.textContent = "連假 " + fmtRange(part.run.start, part.run.end) + "，共 " + part.run.len + " 天";
    } else {
      p.textContent = fmtRange(part.best.start, part.best.end);
    }
    body.appendChild(p);

    var tags = el("div", "tagline");
    var t = travelTag(part.best);
    if (t) { var tg = el("span", t.cls, t.text); tags.appendChild(tg); }
    if (part.run && part.run.len >= 3) tags.appendChild(el("span", "tag", part.run.len + " 天連假"));
    if (part.entries.some(function (e) { return e.approx; })) {
      tags.appendChild(el("span", "tag", "推估日期"));
    }
    if (tags.childNodes.length) body.appendChild(tags);

    var noted = part.entries.filter(function (e) { return e.note; })[0];
    if (noted) body.appendChild(el("div", "note", noted.note));

    row.appendChild(body);
    return row;
  }

  /* -------------------------------------------------------- 篩選器 UI */
  function regionCountries(region) {
    return DATA.countries.filter(function (c) { return c.region === region; });
  }

  function renderFilters() {
    var wrap = $("region-chips");
    clear(wrap);
    REGIONS.forEach(function (region) {
      var list = regionCountries(region);
      var on = list.filter(function (c) { return state.selected[c.code]; }).length;
      var b = el("button", "chip" + (on === list.length ? " is-on" : ""),
        region + " " + on + "/" + list.length);
      b.addEventListener("click", function () {
        var turnOn = on !== list.length;
        list.forEach(function (c) {
          if (turnOn) state.selected[c.code] = true; else delete state.selected[c.code];
        });
        afterFilterChange();
      });
      wrap.appendChild(b);
    });
    var n = activeCodes().length;
    $("filter-count").textContent = "（已選 " + n + " / " + DATA.countries.length + " 國）";
  }

  function afterFilterChange() {
    if (!activeCodes().length) {
      DATA.countries.forEach(function (c) { state.selected[c.code] = true; });
    }
    scoreCache = {};
    saveSelection();
    renderFilters();
    renderTrip();
    renderCalendar();
  }

  /* -------------------------------------------------------- 行程檢查 */
  function clampToRange(dt) {
    if (dt < RANGE_START) return new Date(RANGE_START.getTime());
    if (dt > RANGE_END) return new Date(RANGE_END.getTime());
    return dt;
  }

  function readDates() {
    var s = $("start-date").value, e = $("end-date").value;
    if (!s) return;
    var sd = clampToRange(parse(s));
    var ed = e ? clampToRange(parse(e)) : sd;
    if (ed < sd) ed = sd;
    if (diffDays(sd, ed) > 120) ed = addDays(sd, 120);
    state.start = ymd(sd);
    state.end = ymd(ed);
    $("start-date").value = state.start;
    $("end-date").value = state.end;
  }

  function renderTrip() {
    if (!state.start) return;
    var codes = activeCodes(), key = filterKey();
    var len = diffDays(parse(state.start), parse(state.end)) + 1;
    var score = tripScore(state.start, len, codes, key);
    var lv = levelOf(score);

    // 指數卡
    var gauge = $("gauge");
    gauge.style.setProperty("--gauge-deg", (score * 3.6) + "deg");
    gauge.style.setProperty("--gauge-color", "var(--lv" + lv + ")");
    $("score-value").textContent = score;
    $("score-label").textContent = LEVELS[lv].name + "・" + len + " 天行程";

    // 每日格
    var grid = $("trip-days");
    clear(grid);
    var d = parse(state.start), topAll = {};
    var lead = (d.getDay() + 6) % 7;
    for (var k = 0; k < lead; k++) grid.appendChild(el("div", "day pad"));
    for (var i = 0; i < len; i++) {
      (function (dt) {
        var ds = ymd(dt);
        var s = dayScore(ds, codes, key);
        var cell = el("button", "day" + (dt.getDay() === 0 || dt.getDay() === 6 ? " wknd" : ""));
        cell.appendChild(el("b", null, String(dt.getDate())));
        cell.appendChild(el("em", null, WD[dt.getDay()]));
        cell.appendChild(el("span", "bar lv" + levelOf(s)));
        cell.title = fmtShort(ds) + "：擁擠指數 " + s;
        cell.addEventListener("click", function () { openSheet(ds); });
        grid.appendChild(cell);
        contributions(ds, codes).forEach(function (p) {
          if (!topAll[p.code] || topAll[p.code].impact < p.impact) topAll[p.code] = p;
        });
      })(d);
      d = addDays(d, 1);
    }

    // 說明文字
    var ranked = Object.keys(topAll).map(function (k) { return topAll[k]; })
      .sort(function (a, b) { return b.impact - a.impact; });
    var desc = LEVELS[lv].desc;
    if (ranked.length) {
      desc += "主要來自 " + ranked.slice(0, 3).map(function (p) {
        return META[p.code].name + p.best.name;
      }).join("、") + "。";
    }
    $("score-desc").textContent = desc;

    // 重疊清單
    var list = $("overlap-list");
    clear(list);
    if (!ranked.length) {
      list.appendChild(el("p", "empty", "太好了，你選的日期沒有任何國家在放國定假日。"));
    } else {
      ranked.forEach(function (p) { list.appendChild(entryRow(p.code, p)); });
    }

    renderSuggestions(len, score, codes, key);
  }

  function renderSuggestions(len, currentScore, codes, key) {
    var box = $("suggestions");
    clear(box);
    var base = parse(state.start), cands = [];
    for (var off = -45; off <= 45; off++) {
      if (off === 0) continue;
      var s = addDays(base, off);
      if (s < RANGE_START || addDays(s, len - 1) > RANGE_END) continue;
      cands.push({ start: ymd(s), off: off, score: tripScore(ymd(s), len, codes, key) });
    }
    cands.sort(function (a, b) {
      return a.score - b.score || Math.abs(a.off) - Math.abs(b.off);
    });

    var picked = [];
    for (var i = 0; i < cands.length && picked.length < 3; i++) {
      var ok = picked.every(function (p) { return Math.abs(p.off - cands[i].off) >= len; });
      if (ok && cands[i].score < currentScore) picked.push(cands[i]);
    }

    if (!picked.length) {
      box.appendChild(el("p", "empty",
        currentScore <= LEVEL_CUTS[0]
          ? "你選的日期已經是附近最順的時段了。"
          : "前後 45 天內找不到更清閒的時段，這段期間各國假期都很密集。"));
      return;
    }

    picked.forEach(function (p) {
      var endStr = ymd(addDays(parse(p.start), len - 1));
      var b = el("button", "sugg");
      var left = el("div");
      left.appendChild(el("b", null, fmtRange(p.start, endStr)));
      var delta = p.off > 0 ? "往後 " + p.off + " 天" : "提早 " + (-p.off) + " 天";
      left.appendChild(el("small", null, delta + "・指數少 " + (currentScore - p.score) + " 分"));
      b.appendChild(left);
      var pill = el("span", "pill lv" + levelOf(p.score), String(p.score));
      b.appendChild(pill);
      b.addEventListener("click", function () {
        $("start-date").value = p.start;
        $("end-date").value = endStr;
        readDates();
        renderTrip();
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
      box.appendChild(b);
    });
  }

  /* -------------------------------------------------------- 月曆 */
  function renderCalendar() {
    if (!state.month) return;
    var codes = activeCodes(), key = filterKey();
    var y = state.month.getFullYear(), m = state.month.getMonth();
    $("month-title").textContent = y + " 年 " + (m + 1) + " 月";
    $("prev-month").disabled = new Date(y, m, 1) <= RANGE_START;
    $("next-month").disabled = new Date(y, m + 1, 1) > RANGE_END;

    var grid = $("month-grid");
    clear(grid);
    var first = new Date(y, m, 1);
    var pad = (first.getDay() + 6) % 7;               // 週一為一週之始
    var daysInMonth = new Date(y, m + 1, 0).getDate();
    var todayStr = ymd(new Date());
    var i;

    for (i = 0; i < pad; i++) grid.appendChild(el("div", "mday pad"));

    for (i = 1; i <= daysInMonth; i++) {
      (function (day) {
        var dt = new Date(y, m, day), ds = ymd(dt);
        var s = dayScore(ds, codes, key);
        var parts = contributions(ds, codes);
        var lv = levelOf(s);
        var cell = el("button", "mday tint lv-bg" + lv + (ds === todayStr ? " today" : ""));
        cell.appendChild(el("span", "n", String(day)));
        var major = parts.filter(function (p) { return p.impact >= 24; });
        var flags = major.slice(0, 2).map(function (p) { return META[p.code].flag; }).join("");
        if (major.length > 2) flags += "+" + (major.length - 2);
        cell.appendChild(el("span", "fl", flags || " "));
        cell.appendChild(el("span", "dot lv" + lv));
        cell.setAttribute("aria-label", (m + 1) + "月" + day + "日，擁擠指數 " + s);
        cell.addEventListener("click", function () { openSheet(ds); });
        grid.appendChild(cell);
      })(i);
    }

    // 本月重點連假
    var hi = $("month-highlights");
    clear(hi);
    var seen = {}, items = [];
    codes.forEach(function (code) {
      (DATA.holidays[code] || []).forEach(function (e) {
        var es = parse(e.start), ee = parse(e.end);
        if (ee < new Date(y, m, 1) || es > new Date(y, m, daysInMonth)) return;
        var season = e.kind === "season";
        var run = season ? null : IDX[code].run[e.start];
        var len = run ? run.len : diffDays(es, ee) + 1;
        if (!season && len < 3 && e.travel !== "high") return;
        var k = code + "|" + (run ? run.start : e.start);
        if (seen[k]) return;
        seen[k] = true;
        items.push({
          code: code,
          impact: entryImpact(code, e, len),
          part: { entries: [e], best: e, run: run, runLen: len }
        });
      });
    });
    items.sort(function (a, b) { return b.impact - a.impact; });
    if (!items.length) {
      hi.appendChild(el("p", "empty", "這個月沒有明顯的跨國連假，是相對清閒的月份。"));
    } else {
      items.slice(0, 12).forEach(function (it) { hi.appendChild(entryRow(it.code, it.part)); });
    }
  }

  /* -------------------------------------------------------- 日期詳情 */
  function openSheet(ds) {
    var codes = activeCodes(), key = filterKey();
    var s = dayScore(ds, codes, key), lv = levelOf(s);
    var dt = parse(ds);
    $("sheet-title").textContent =
      dt.getFullYear() + "/" + (dt.getMonth() + 1) + "/" + dt.getDate() +
      "（週" + WD[dt.getDay()] + "）・" + LEVELS[lv].name + " " + s;
    var body = $("sheet-body");
    clear(body);
    var parts = contributions(ds, codes);
    if (!parts.length) {
      body.appendChild(el("p", "empty", "這一天沒有國家放國定假日。"));
    } else {
      parts.forEach(function (p) { body.appendChild(entryRow(p.code, p)); });
    }
    $("sheet-backdrop").hidden = false;
    $("day-sheet").hidden = false;
    document.body.style.overflow = "hidden";
  }
  function closeSheet() {
    $("sheet-backdrop").hidden = true;
    $("day-sheet").hidden = true;
    document.body.style.overflow = "";
  }

  /* -------------------------------------------------------- 各國假期 */
  function renderCountries() {
    var wrap = $("country-list");
    clear(wrap);
    var q = state.search.trim().toLowerCase();
    var y = state.countryYear;
    var found = 0;

    DATA.countries.slice().sort(function (a, b) { return b.weight - a.weight; })
      .forEach(function (c) {
        if (q && c.name.toLowerCase().indexOf(q) === -1 &&
            c.en.toLowerCase().indexOf(q) === -1 &&
            c.code.toLowerCase().indexOf(q) === -1) return;
        found++;

        var entries = (DATA.holidays[c.code] || []).filter(function (e) {
          return e.start.slice(0, 4) === String(y) || e.end.slice(0, 4) === String(y);
        });
        var longRuns = {}, runList = [];
        entries.forEach(function (e) {
          if (e.kind === "season") return;
          var run = IDX[c.code].run[e.start];
          if (run && run.len >= 3 && !longRuns[run.start]) {
            longRuns[run.start] = true;
            runList.push(run);
          }
        });

        var det = el("details", "card country-card");
        var sum = el("summary");
        sum.appendChild(el("span", "flag", c.flag));
        var grow = el("div", "grow");
        grow.appendChild(el("b", null, c.name));
        grow.appendChild(el("small", null,
          y + " 年 " + entries.length + " 個假期・" + runList.length + " 段 3 天以上連假"));
        sum.appendChild(grow);
        sum.appendChild(el("span", "chev", "▸"));
        det.appendChild(sum);

        var bodyBox = el("div", "country-body");
        if (!entries.length) {
          bodyBox.appendChild(el("p", "empty", "沒有資料。"));
        } else {
          entries.forEach(function (e) {
            var run = e.kind === "season" ? null : IDX[c.code].run[e.start];
            bodyBox.appendChild(entryRow(c.code, {
              entries: [e], best: e, run: run,
              runLen: run ? run.len : 1
            }));
          });
        }
        det.appendChild(bodyBox);
        wrap.appendChild(det);
      });

    if (!found) {
      var card = el("div", "card");
      card.appendChild(el("p", "empty", "找不到符合的國家。"));
      wrap.appendChild(card);
    }
  }

  /* -------------------------------------------------------- 初始化 */
  function initTabs() {
    var tabs = document.querySelectorAll(".tab");
    Array.prototype.forEach.call(tabs, function (t) {
      t.addEventListener("click", function () {
        Array.prototype.forEach.call(tabs, function (x) {
          x.classList.remove("is-active");
          x.setAttribute("aria-selected", "false");
        });
        t.classList.add("is-active");
        t.setAttribute("aria-selected", "true");
        ["trip", "calendar", "countries"].forEach(function (p) {
          $("panel-" + p).hidden = (p !== t.dataset.panel);
        });
        window.scrollTo({ top: 0 });
      });
    });
  }

  function initTripControls() {
    var today = new Date();
    var start = clampToRange(addDays(today, 30));
    var end = clampToRange(addDays(start, 6));
    var sd = $("start-date"), ed = $("end-date");
    sd.min = ed.min = ymd(RANGE_START);
    sd.max = ed.max = ymd(RANGE_END);
    sd.value = ymd(start);
    ed.value = ymd(end);
    readDates();

    sd.addEventListener("change", function () {
      var oldLen = diffDays(parse(state.start), parse(state.end));
      var ns = clampToRange(parse(sd.value || state.start));
      ed.value = ymd(clampToRange(addDays(ns, oldLen)));
      readDates();
      renderTrip();
    });
    ed.addEventListener("change", function () { readDates(); renderTrip(); });

    Array.prototype.forEach.call($("quick-ranges").children, function (b) {
      b.addEventListener("click", function () {
        var s = parse(state.start);
        ed.value = ymd(clampToRange(addDays(s, +b.dataset.len - 1)));
        readDates();
        renderTrip();
        markQuick();
      });
    });

    document.querySelectorAll("[data-preset]").forEach(function (b) {
      b.addEventListener("click", function () {
        state.selected = {};
        DATA.countries.forEach(function (c) {
          if (b.dataset.preset === "all") state.selected[c.code] = true;
          else if (b.dataset.preset === "asia" && (c.region === "亞洲" || c.region === "大洋洲")) state.selected[c.code] = true;
          else if (b.dataset.preset === "major" && c.weight >= 50) state.selected[c.code] = true;
        });
        afterFilterChange();
      });
    });
  }

  function markQuick() {
    var len = diffDays(parse(state.start), parse(state.end)) + 1;
    Array.prototype.forEach.call($("quick-ranges").children, function (b) {
      b.classList.toggle("is-on", +b.dataset.len === len);
    });
  }

  function initCalendar() {
    var today = new Date();
    state.month = new Date(today.getFullYear(), today.getMonth(), 1);
    if (state.month < RANGE_START) state.month = new Date(RANGE_START.getFullYear(), RANGE_START.getMonth(), 1);
    if (state.month > RANGE_END) state.month = new Date(RANGE_END.getFullYear(), RANGE_END.getMonth(), 1);
    $("prev-month").addEventListener("click", function () {
      state.month = new Date(state.month.getFullYear(), state.month.getMonth() - 1, 1);
      renderCalendar();
    });
    $("next-month").addEventListener("click", function () {
      state.month = new Date(state.month.getFullYear(), state.month.getMonth() + 1, 1);
      renderCalendar();
    });
  }

  function initCountries() {
    var chips = $("year-chips");
    DATA.years.forEach(function (y) {
      var b = el("button", "chip" + (y === state.countryYear ? " is-on" : ""), y + " 年");
      b.addEventListener("click", function () {
        state.countryYear = y;
        Array.prototype.forEach.call(chips.children, function (x) { x.classList.remove("is-on"); });
        b.classList.add("is-on");
        renderCountries();
      });
      chips.appendChild(b);
    });
    var box = $("country-search"), timer;
    box.addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(function () {
        state.search = box.value;
        renderCountries();
      }, 120);
    });
  }

  function initSheet() {
    $("sheet-close").addEventListener("click", closeSheet);
    $("sheet-backdrop").addEventListener("click", closeSheet);
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeSheet();
    });
  }

  function initFooter() {
    $("stat-countries").textContent = DATA.countries.length;
    $("stat-years").textContent = DATA.years.join("、");
    $("stat-generated").textContent = DATA.generated;
  }

  state.selected = loadSelection();
  initTabs();
  initTripControls();
  initCalendar();
  initCountries();
  initSheet();
  initFooter();
  renderFilters();
  renderTrip();
  markQuick();
  renderCalendar();
  renderCountries();
})();
