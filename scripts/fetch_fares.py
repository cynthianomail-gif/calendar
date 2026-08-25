# -*- coding: utf-8 -*-
"""
抓各國「每日單程最低票價」，存成 data/fares/<國碼>.json。

資料來源是 Travelpayouts 的 month-matrix 端點。要知道兩件事：

* 它回的是**快取價**，不是即時報價——是別的使用者先前搜到的最低價，
  官方文件自己建議拿來產生靜態頁面。所以這份資料的用途是「哪天出發
  比較便宜」的趨勢，不是「現在買要多少錢」。每筆都帶 found_at，
  前端要把抓取日期顯示出來，不要讓它看起來像即時報價。
* 它回的是**單程**價（回應裡的 return_date 是空字串）。
  不要拿去當來回票價用。

每個國家一個檔案，前端選了目的地才去載那一國——首頁載入完全不受影響。

    TRAVELPAYOUTS_TOKEN=xxx python3 scripts/fetch_fares.py
    TRAVELPAYOUTS_TOKEN=xxx python3 scripts/fetch_fares.py --months 6 --origin TPE
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "fares"
API = "https://api.travelpayouts.com/v2/prices/month-matrix"

# 這個端點是快取查詢，不是即時搜尋，但還是別打太兇
THROTTLE_SEC = 0.35
TIMEOUT_SEC = 25


def month_starts(n):
    """從這個月開始，往後 n 個月的每月 1 號"""
    out = []
    y, m = date.today().year, date.today().month
    for _ in range(n):
        out.append(date(y, m, 1).isoformat())
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def fetch_month(token, origin, dest, month, currency):
    """回傳 {日期: {p, c, f}}；查不到就回空 dict。單一月份失敗不該中斷整批。"""
    url = (API + "?origin=" + origin + "&destination=" + dest +
           "&month=" + month + "&currency=" + currency +
           "&show_to_affiliates=true")
    req = urllib.request.Request(url, headers={
        "x-access-token": token,
        "Accept": "application/json",
        "User-Agent": "holiday-radar-fares/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as r:
            payload = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise SystemExit("token 無效或未授權（401）——先確認 TRAVELPAYOUTS_TOKEN")
        print("    " + month + " HTTP " + str(e.code), file=sys.stderr)
        return {}
    except Exception as e:                      # 逾時、連線中斷、JSON 壞掉
        print("    " + month + " 失敗：" + str(e), file=sys.stderr)
        return {}

    if not payload.get("success"):
        return {}

    days = {}
    for row in payload.get("data") or []:
        d, v = row.get("depart_date"), row.get("value")
        if not d or not v or v <= 0:
            continue
        # 同一天可能有多筆（不同轉機次數），留最便宜的
        prev = days.get(d)
        if prev and prev["p"] <= v:
            continue
        days[d] = {
            "p": int(v),
            "c": int(row.get("number_of_changes") or 0),
            "f": (row.get("found_at") or "")[:10],
        }
    return days


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--origin", default="TPE", help="出發機場 IATA（預設 TPE）")
    ap.add_argument("--months", type=int, default=6, help="往後抓幾個月（預設 6）")
    ap.add_argument("--currency", default="twd")
    ap.add_argument("--only", default="", help="只抓這幾個國碼，逗號分隔（除錯用）")
    args = ap.parse_args()

    token = os.environ.get("TRAVELPAYOUTS_TOKEN", "").strip()
    if not token:
        raise SystemExit("請設定環境變數 TRAVELPAYOUTS_TOKEN")

    countries = json.loads(
        (ROOT / "data" / "holidays.json").read_text(encoding="utf-8"))["countries"]
    if args.only:
        wanted = set(x.strip().upper() for x in args.only.split(","))
        countries = [c for c in countries if c["code"] in wanted]

    months = month_starts(args.months)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    index, empty = [], []
    for c in countries:
        dest = c.get("gateway")
        # 出發地自己不用抓；沒有門戶機場的也跳過
        if not dest or dest == args.origin:
            continue

        days = {}
        for m in months:
            days.update(fetch_month(token, args.origin, dest, m, args.currency))
            time.sleep(THROTTLE_SEC)

        if not days:
            # 冷門航線本來就可能沒有快取價。留著空檔案只會讓前端多一次
            # 404，所以不寫檔，也不列進索引。
            empty.append(c["code"])
            print(c["code"] + " " + dest + "  無資料")
            continue

        doc = {
            "country": c["code"],
            "origin": args.origin,
            "destination": dest,
            "currency": args.currency.upper(),
            "one_way": True,          # 提醒前端：這是單程價
            "fetched_at": now,
            "days": dict(sorted(days.items())),
        }
        (OUT_DIR / (c["code"] + ".json")).write_text(
            json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8")
        index.append(c["code"])
        prices = [d["p"] for d in days.values()]
        print(c["code"] + " " + dest + "  " + str(len(days)) + " 天  " +
              str(min(prices)) + "–" + str(max(prices)))

    (OUT_DIR / "index.json").write_text(
        json.dumps({
            "origin": args.origin,
            "currency": args.currency.upper(),
            "one_way": True,
            "fetched_at": now,
            "countries": sorted(index),
        }, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8")

    print("")
    print("有價格的國家 " + str(len(index)) + " 個，無資料 " + str(len(empty)) + " 個")
    if not index:
        raise SystemExit("一個國家都沒抓到——不要用空資料覆蓋，先檢查 token 與幣別")


if __name__ == "__main__":
    main()
