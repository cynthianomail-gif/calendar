# -*- coding: utf-8 -*-
"""
產生「全球連假雷達」使用的假期資料 (data/holidays.json)。

設計原則
--------
* 能用規則算的就用規則算（復活節、第 n 個星期幾、補假），避免手key出錯。
* 農曆 / 伊斯蘭曆節日以「錨點日期」表驅動，集中管理、方便逐年更新。
* 政府調休（中國、越南、台灣春節等）以「區間」表示，並標記 approx。
* travel 欄位代表「這個假期帶動跨國旅遊的程度」，是擁擠指數的權重來源。

更新方式：改下方 LUNAR / ISLAMIC 錨點與 YEARS，再執行
    python3 scripts/build_holidays.py
"""

import json
import datetime as dt
from pathlib import Path

YEARS = [2026, 2027]
ROOT = Path(__file__).resolve().parents[1]

D = dt.date
def d(s):
    return dt.date.fromisoformat(s)

# ---------------------------------------------------------------- 日期工具

def easter(year):
    """Anonymous Gregorian algorithm -> 復活節主日"""
    a = year % 19
    b, c = divmod(year, 100)
    e, f = divmod(b, 4)
    g = (8 * b + 13) // 25
    h = (19 * a + b - e - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * f + 2 * i - h - k) % 7
    m = (a + 11 * h + 19 * l) // 433
    month = (h + l - 7 * m + 90) // 25
    day = (h + l - 7 * m + 33 * month + 19) % 32
    return D(year, month, day)


def nth_weekday(year, month, weekday, n):
    """weekday: 0=週一 .. 6=週日；n 為第幾個，-1 表示最後一個"""
    if n > 0:
        first = D(year, month, 1)
        offset = (weekday - first.weekday()) % 7
        return first + dt.timedelta(days=offset + 7 * (n - 1))
    last_day = (D(year, month, 28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
    offset = (last_day.weekday() - weekday) % 7
    return last_day - dt.timedelta(days=offset)


def observe(day, rule):
    """把落在週末的假日移到補假日。rule 決定各國作法。"""
    wd = day.weekday()  # 5=週六 6=週日
    if rule == "tw":              # 逢週六補前一日、逢週日補次日
        if wd == 5:
            return day - dt.timedelta(days=1)
        if wd == 6:
            return day + dt.timedelta(days=1)
    elif rule == "sun_to_mon":    # 逢週日補週一（香港、新加坡、澳洲…）
        if wd == 6:
            return day + dt.timedelta(days=1)
    elif rule == "us":            # 週六補週五、週日補週一
        if wd == 5:
            return day - dt.timedelta(days=1)
        if wd == 6:
            return day + dt.timedelta(days=1)
    elif rule == "next_weekday":  # 週末一律往後推到下一個平日（英國）
        while day.weekday() >= 5:
            day += dt.timedelta(days=1)
    return day


# ------------------------------------------------- 農曆 / 伊斯蘭曆錨點日期
# 農曆節日換算後的西曆日期。伊斯蘭曆節日依實際觀月可能±1~2天，標記為 approx。
LUNAR = {
    2026: {
        "cny": d("2026-02-17"),      # 正月初一
        "nye": d("2026-02-16"),      # 除夕
        "qingming": d("2026-04-05"),
        "dragon": d("2026-06-19"),   # 端午
        "midautumn": d("2026-09-25"),
        "chongyang": d("2026-10-18"),
        "buddha": d("2026-05-24"),   # 四月初八 佛誕
        "vesak": d("2026-05-31"),    # 四月十五 衛塞節
        "seollal": d("2026-02-17"),
        "chuseok": d("2026-09-25"),
        "deepavali": d("2026-11-08"),
        "holi": d("2026-03-04"),
    },
    2027: {
        "cny": d("2027-02-06"),
        "nye": d("2027-02-05"),
        "qingming": d("2027-04-05"),
        "dragon": d("2027-06-09"),
        "midautumn": d("2027-09-15"),
        "chongyang": d("2027-10-08"),
        "buddha": d("2027-05-13"),
        "vesak": d("2027-05-20"),
        "seollal": d("2027-02-06"),
        "chuseok": d("2027-09-15"),
        "deepavali": d("2027-10-29"),
        "holi": d("2027-03-22"),
    },
}

ISLAMIC = {
    2026: {"fitr": d("2026-03-20"), "adha": d("2026-05-27")},
    2027: {"fitr": d("2027-03-09"), "adha": d("2027-05-16")},
}


# ---------------------------------------------------------------- 國家清單
# weight = 出境旅遊「人潮影響力」(0-100)，用來加權擁擠指數：
# 人口規模 × 出國旅遊傾向 × 對熱門目的地的實際影響。
COUNTRIES = [
    ("CN", "中國",       "China",        "🇨🇳", "亞洲", 100),
    ("JP", "日本",       "Japan",        "🇯🇵", "亞洲",  82),
    ("KR", "韓國",       "South Korea",  "🇰🇷", "亞洲",  76),
    ("TW", "台灣",       "Taiwan",       "🇹🇼", "亞洲",  62),
    ("HK", "香港",       "Hong Kong",    "🇭🇰", "亞洲",  56),
    ("MO", "澳門",       "Macau",        "🇲🇴", "亞洲",  20),
    ("SG", "新加坡",     "Singapore",    "🇸🇬", "亞洲",  52),
    ("MY", "馬來西亞",   "Malaysia",     "🇲🇾", "亞洲",  46),
    ("TH", "泰國",       "Thailand",     "🇹🇭", "亞洲",  46),
    ("VN", "越南",       "Vietnam",      "🇻🇳", "亞洲",  42),
    ("ID", "印尼",       "Indonesia",    "🇮🇩", "亞洲",  46),
    ("PH", "菲律賓",     "Philippines",  "🇵🇭", "亞洲",  36),
    ("IN", "印度",       "India",        "🇮🇳", "亞洲",  60),
    ("AU", "澳洲",       "Australia",    "🇦🇺", "大洋洲", 50),
    ("NZ", "紐西蘭",     "New Zealand",  "🇳🇿", "大洋洲", 24),
    ("GB", "英國",       "United Kingdom", "🇬🇧", "歐洲", 66),
    ("DE", "德國",       "Germany",      "🇩🇪", "歐洲",  70),
    ("FR", "法國",       "France",       "🇫🇷", "歐洲",  66),
    ("IT", "義大利",     "Italy",        "🇮🇹", "歐洲",  56),
    ("ES", "西班牙",     "Spain",        "🇪🇸", "歐洲",  50),
    ("NL", "荷蘭",       "Netherlands",  "🇳🇱", "歐洲",  40),
    ("CH", "瑞士",       "Switzerland",  "🇨🇭", "歐洲",  30),
    ("AT", "奧地利",     "Austria",      "🇦🇹", "歐洲",  28),
    ("PL", "波蘭",       "Poland",       "🇵🇱", "歐洲",  32),
    ("SE", "瑞典",       "Sweden",       "🇸🇪", "歐洲",  26),
    ("NO", "挪威",       "Norway",       "🇳🇴", "歐洲",  24),
    ("DK", "丹麥",       "Denmark",      "🇩🇰", "歐洲",  22),
    ("FI", "芬蘭",       "Finland",      "🇫🇮", "歐洲",  20),
    ("RU", "俄羅斯",     "Russia",       "🇷🇺", "歐洲",  44),
    ("US", "美國",       "United States", "🇺🇸", "美洲", 86),
    ("CA", "加拿大",     "Canada",       "🇨🇦", "美洲",  46),
    ("MX", "墨西哥",     "Mexico",       "🇲🇽", "美洲",  36),
    ("BR", "巴西",       "Brazil",       "🇧🇷", "美洲",  36),
    ("AR", "阿根廷",     "Argentina",    "🇦🇷", "美洲",  20),
    ("TR", "土耳其",     "Türkiye",      "🇹🇷", "中東非洲", 36),
    ("AE", "阿聯",       "UAE",          "🇦🇪", "中東非洲", 36),
    ("SA", "沙烏地阿拉伯", "Saudi Arabia", "🇸🇦", "中東非洲", 36),
    ("IL", "以色列",     "Israel",       "🇮🇱", "中東非洲", 20),
    ("ZA", "南非",       "South Africa", "🇿🇦", "中東非洲", 20),
    ("EG", "埃及",       "Egypt",        "🇪🇬", "中東非洲", 16),
]

# 週末不是週六日的國家（0=週一 … 6=週日）
WEEKENDS = {"SA": [4, 5], "IL": [4, 5], "EG": [4, 5]}

# 補假規則
OBSERVE_RULE = {
    "TW": "tw", "HK": "sun_to_mon", "SG": "sun_to_mon", "MY": "sun_to_mon",
    "MO": "sun_to_mon", "US": "us", "GB": "next_weekday", "AU": "sun_to_mon",
    "NZ": "sun_to_mon", "PH": "none", "TH": "sun_to_mon", "ZA": "sun_to_mon",
}


def H(name, start, end=None, travel="low", approx=False, kind="public", note=None):
    e = {
        "name": name,
        "start": start.isoformat(),
        "end": (end or start).isoformat(),
        "travel": travel,
    }
    if approx:
        e["approx"] = True
    if kind != "public":
        e["kind"] = kind
    if note:
        e["note"] = note
    return e


def days(base, n):
    return base + dt.timedelta(days=n)


# --------------------------------------------------- 其他需要逐年查表的節日
JP_EQUINOX = {2026: (d("2026-03-20"), d("2026-09-23")),
              2027: (d("2027-03-21"), d("2027-09-23"))}
TH_LUNAR = {2026: {"makha": d("2026-03-03"), "asalha": d("2026-07-29")},
            2027: {"makha": d("2027-02-21"), "asalha": d("2027-07-18")}}
ID_NYEPI = {2026: d("2026-03-19"), 2027: d("2027-03-08")}
NZ_MATARIKI = {2026: d("2026-07-10"), 2027: d("2027-06-25")}
IN_DUSSEHRA = {2026: d("2026-10-20"), 2027: d("2027-10-09")}
VN_HUNG = {2026: d("2026-04-26"), 2027: d("2027-04-16")}
EG_SHAM = {2026: d("2026-04-13"), 2027: d("2027-05-03")}
IL_TABLE = {
    2026: {"purim": d("2026-03-03"), "pesach": (d("2026-04-02"), d("2026-04-08")),
           "shavuot": d("2026-05-22"), "rosh": (d("2026-09-12"), d("2026-09-13")),
           "kippur": d("2026-09-21"), "sukkot": (d("2026-09-26"), d("2026-10-03"))},
    2027: {"purim": d("2027-03-23"), "pesach": (d("2027-04-22"), d("2027-04-28")),
           "shavuot": d("2027-06-11"), "rosh": (d("2027-10-02"), d("2027-10-03")),
           "kippur": d("2027-10-11"), "sukkot": (d("2027-10-16"), d("2027-10-23"))},
}

BUILDERS = {}
def country(code):
    def deco(fn):
        BUILDERS[code] = fn
        return fn
    return deco


# ------------------------------------------------------------------ 亞洲

@country("CN")
def cn(y):
    L, e = LUNAR[y], easter(y)
    return [
        H("元旦", D(y, 1, 1), D(y, 1, 3), "mid", approx=True),
        H("春節", days(L["nye"], -2), days(L["cny"], 5), "high", approx=True,
          note="全球最大規模的人口移動，熱門目的地機票與住宿最貴"),
        H("清明節", days(L["qingming"], -1), days(L["qingming"], 1), "mid", approx=True),
        H("勞動節", D(y, 5, 1), D(y, 5, 5), "high", approx=True, note="五一黃金週，出境旅遊高峰"),
        H("端午節", days(L["dragon"], -1), days(L["dragon"], 1), "mid", approx=True),
        H("中秋節", days(L["midautumn"], -1), days(L["midautumn"], 1), "mid", approx=True),
        H("國慶日", D(y, 10, 1), D(y, 10, 7), "high", approx=True, note="十一黃金週，出境旅遊高峰"),
    ]


@country("JP")
def jp(y):
    spring, autumn = JP_EQUINOX[y]
    fixed = [
        ("元日", D(y, 1, 1), "mid"),
        ("成人之日", nth_weekday(y, 1, 0, 2), "low"),
        ("建國紀念之日", D(y, 2, 11), "low"),
        ("天皇誕生日", D(y, 2, 23), "low"),
        ("春分之日", spring, "mid"),
        ("昭和之日", D(y, 4, 29), "high"),
        ("憲法紀念日", D(y, 5, 3), "high"),
        ("綠之日", D(y, 5, 4), "high"),
        ("兒童節", D(y, 5, 5), "high"),
        ("海之日", nth_weekday(y, 7, 0, 3), "mid"),
        ("山之日", D(y, 8, 11), "mid"),
        ("敬老之日", nth_weekday(y, 9, 0, 3), "mid"),
        ("秋分之日", autumn, "mid"),
        ("運動之日", nth_weekday(y, 10, 0, 2), "mid"),
        ("文化之日", D(y, 11, 3), "low"),
        ("勤勞感謝之日", D(y, 11, 23), "low"),
    ]
    dates = {x[1] for x in fixed}
    out = [H(n, dd, travel=t) for n, dd, t in fixed]

    # 振替休日：假日逢週日順延至次一非假日
    for n, dd, t in fixed:
        if dd.weekday() == 6:
            nxt = days(dd, 1)
            while nxt in dates:
                nxt = days(nxt, 1)
            dates.add(nxt)
            out.append(H(f"{n}（補假）", nxt, travel=t))

    # 國民之休日：夾在兩個假日之間的平日
    aged, aut = nth_weekday(y, 9, 0, 3), autumn
    if (aut - aged).days == 2:
        out.append(H("國民之休日", days(aged, 1), travel="high"))

    gw_end = D(y, 5, 5)
    while gw_end in dates or gw_end.weekday() >= 5:
        gw_end = days(gw_end, 1)
    out += [
        H("黃金週", D(y, 4, 29), days(gw_end, -1), "high", kind="season",
          note="日本全國最大連假，國內外機票住宿全面漲價"),
        H("盂蘭盆節（お盆）", D(y, 8, 13), D(y, 8, 16), "high", kind="season",
          note="非法定假日，但企業普遍放假、返鄉與出國高峰"),
        H("年末年始", D(y, 12, 29), D(y, 12, 31), "high", kind="season"),
    ]
    return out


@country("KR")
def kr(y):
    L = LUNAR[y]
    base = [
        ("新正（元旦）", D(y, 1, 1), "mid", False),
        ("三一節", D(y, 3, 1), "low", True),
        ("兒童節", D(y, 5, 5), "mid", True),
        ("釋迦誕辰日", L["buddha"], "mid", True),
        ("顯忠日", D(y, 6, 6), "low", False),
        ("光復節", D(y, 8, 15), "mid", True),
        ("開天節", D(y, 10, 3), "low", True),
        ("韓文日", D(y, 10, 9), "low", True),
        ("聖誕節", D(y, 12, 25), "mid", False),
    ]
    out = [H(n, dd, travel=t) for n, dd, t, _ in base]
    for n, dd, t, sub in base:
        if sub and dd.weekday() >= 5:
            nxt = days(dd, 1)
            while nxt.weekday() >= 5:
                nxt = days(nxt, 1)
            out.append(H(f"{n}（代替公休日）", nxt, travel=t))
    out += [
        H("春節（설날）", days(L["seollal"], -1), days(L["seollal"], 1), "high",
          note="韓國最大連假，出國旅遊需求暴增"),
        H("中秋節（추석）", days(L["chuseok"], -1), days(L["chuseok"], 1), "high",
          note="韓國第二大連假，鄰近國家旅遊人潮明顯增加"),
    ]
    return out


@country("TW")
def tw(y):
    L = LUNAR[y]
    o = lambda x: observe(x, "tw")
    # 春節：除夕前一日至初三，逢週末往後補假
    start, end = days(L["nye"], -1), days(L["cny"], 2)
    weekend_in = sum(1 for i in range((end - start).days + 1)
                     if (start + dt.timedelta(days=i)).weekday() >= 5)
    cur = end
    for _ in range(weekend_in):
        cur = days(cur, 1)
        while cur.weekday() >= 5:
            cur = days(cur, 1)
    out = [
        H("開國紀念日", o(D(y, 1, 1)), travel="mid"),
        H("農曆春節", start, cur, "high", note="台灣最長連假，出國機位一位難求"),
        H("和平紀念日", o(D(y, 2, 28)), travel="mid"),
        H("兒童節", o(D(y, 4, 4)), travel="mid"),
        H("清明節", o(L["qingming"]), travel="mid"),
        H("勞動節", o(D(y, 5, 1)), travel="mid"),
        H("端午節", o(L["dragon"]), travel="mid"),
        H("中秋節", o(L["midautumn"]), travel="mid"),
        H("教師節", o(D(y, 9, 28)), travel="mid"),
        H("國慶日", o(D(y, 10, 10)), travel="mid"),
        H("台灣光復節", o(D(y, 10, 25)), travel="mid"),
        H("行憲紀念日", o(D(y, 12, 25)), travel="mid"),
    ]
    return out


@country("HK")
def hk(y):
    L, e = LUNAR[y], easter(y)
    o = lambda x: observe(x, "sun_to_mon")
    cny_end = days(L["cny"], 2)
    if any((days(L["cny"], i)).weekday() == 6 for i in range(3)):
        cny_end = days(cny_end, 1)
    return [
        H("元旦", o(D(y, 1, 1)), travel="mid"),
        H("農曆年初一至初三", L["cny"], cny_end, "high", note="港人出遊高峰"),
        H("清明節", o(L["qingming"]), travel="mid"),
        H("復活節", days(e, -2), days(e, 1), "high"),
        H("勞動節", o(D(y, 5, 1)), travel="mid"),
        H("佛誕", o(L["buddha"]), travel="low"),
        H("端午節", o(L["dragon"]), travel="mid"),
        H("香港特別行政區成立紀念日", o(D(y, 7, 1)), travel="mid"),
        H("中秋節翌日", o(days(L["midautumn"], 1)), travel="mid"),
        H("國慶日", o(D(y, 10, 1)), travel="mid"),
        H("重陽節", o(L["chongyang"]), travel="low"),
        H("聖誕節", D(y, 12, 25), D(y, 12, 26), "high"),
    ]


@country("MO")
def mo(y):
    L = LUNAR[y]
    o = lambda x: observe(x, "sun_to_mon")
    return [
        H("元旦", o(D(y, 1, 1)), travel="mid"),
        H("農曆新年", L["cny"], days(L["cny"], 2), "high"),
        H("清明節", o(L["qingming"]), travel="low"),
        H("勞動節", o(D(y, 5, 1)), travel="mid"),
        H("佛誕", o(L["buddha"]), travel="low"),
        H("端午節", o(L["dragon"]), travel="low"),
        H("中秋節翌日", o(days(L["midautumn"], 1)), travel="mid"),
        H("國慶日", D(y, 10, 1), D(y, 10, 2), "mid"),
        H("重陽節", o(L["chongyang"]), travel="low"),
        H("追思節", D(y, 11, 2), travel="low"),
        H("聖誕節", D(y, 12, 24), D(y, 12, 25), "mid"),
    ]


@country("SG")
def sg(y):
    L, I, e = LUNAR[y], ISLAMIC[y], easter(y)
    o = lambda x: observe(x, "sun_to_mon")
    return [
        H("元旦", o(D(y, 1, 1)), travel="mid"),
        H("農曆新年", L["cny"], days(L["cny"], 1), "high"),
        H("開齋節", o(I["fitr"]), travel="mid", approx=True),
        H("耶穌受難日", days(e, -2), travel="mid"),
        H("勞動節", o(D(y, 5, 1)), travel="mid"),
        H("衛塞節", o(L["vesak"]), travel="low"),
        H("哈芝節", o(I["adha"]), travel="low", approx=True),
        H("國慶日", o(D(y, 8, 9)), travel="mid"),
        H("屠妖節", o(L["deepavali"]), travel="low"),
        H("聖誕節", o(D(y, 12, 25)), travel="mid"),
    ]


@country("MY")
def my(y):
    L, I = LUNAR[y], ISLAMIC[y]
    o = lambda x: observe(x, "sun_to_mon")
    return [
        H("元旦", o(D(y, 1, 1)), travel="mid"),
        H("農曆新年", L["cny"], days(L["cny"], 1), "high"),
        H("開齋節（Hari Raya Aidilfitri）", days(I["fitr"], -1), days(I["fitr"], 2),
          "high", approx=True, note="馬來西亞最大返鄉與旅遊潮"),
        H("勞動節", o(D(y, 5, 1)), travel="mid"),
        H("衛塞節", o(L["vesak"]), travel="low"),
        H("最高元首誕辰", nth_weekday(y, 6, 0, 1), travel="low"),
        H("哈芝節（Hari Raya Haji）", I["adha"], days(I["adha"], 1), "mid", approx=True),
        H("國慶日", o(D(y, 8, 31)), travel="mid"),
        H("馬來西亞日", o(D(y, 9, 16)), travel="mid"),
        H("屠妖節", o(L["deepavali"]), travel="low"),
        H("聖誕節", o(D(y, 12, 25)), travel="mid"),
    ]


@country("TH")
def th(y):
    L, T = LUNAR[y], TH_LUNAR[y]
    o = lambda x: observe(x, "sun_to_mon")
    return [
        H("元旦", D(y, 1, 1), o(D(y, 1, 1)), "mid"),
        H("萬佛節", o(T["makha"]), travel="low"),
        H("卻克里王朝紀念日", o(D(y, 4, 6)), travel="low"),
        H("宋干節（潑水節）", D(y, 4, 13), D(y, 4, 15), "high",
          note="泰國新年，全國移動、班機與飯店最滿"),
        H("勞動節", o(D(y, 5, 1)), travel="mid"),
        H("加冕紀念日", o(D(y, 5, 4)), travel="low"),
        H("衛塞節", o(L["vesak"]), travel="low"),
        H("三寶佛節與守夏節", T["asalha"], days(T["asalha"], 1), "mid"),
        H("王太后誕辰（母親節）", o(D(y, 8, 12)), travel="mid"),
        H("九世王逝世紀念日", o(D(y, 10, 13)), travel="low"),
        H("五世王紀念日", o(D(y, 10, 23)), travel="low"),
        H("國王誕辰（父親節）", o(D(y, 12, 5)), travel="mid"),
        H("行憲紀念日", o(D(y, 12, 10)), travel="low"),
        H("跨年", D(y, 12, 31), travel="high"),
    ]


@country("VN")
def vn(y):
    L = LUNAR[y]
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("春節（Tết）", days(L["nye"], -2), days(L["cny"], 4), "high", approx=True,
          note="越南最大長假，全國停擺、返鄉與出國潮"),
        H("雄王紀念日", VN_HUNG[y], travel="low"),
        H("南方解放日與勞動節", D(y, 4, 30), D(y, 5, 1), "high", approx=True,
          note="常與週末串成 4~5 天連假"),
        H("國慶日", D(y, 9, 2), days(D(y, 9, 2), 1), "mid", approx=True),
    ]


@country("ID")
def idn(y):
    I, L, e = ISLAMIC[y], LUNAR[y], easter(y)
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("農曆新年", L["cny"], travel="mid"),
        H("靜居日（Nyepi）", ID_NYEPI[y], travel="mid",
          note="峇里島全島停擺，機場關閉一天"),
        H("開齋節與共同假期", days(I["fitr"], -3), days(I["fitr"], 4), "high", approx=True,
          note="Mudik 返鄉潮，東南亞航線最擁擠的期間之一"),
        H("耶穌受難日", days(e, -2), travel="low"),
        H("勞動節", D(y, 5, 1), travel="mid"),
        H("衛塞節", L["vesak"], travel="low"),
        H("耶穌升天日", days(e, 39), travel="low"),
        H("潘查希拉日", D(y, 6, 1), travel="low"),
        H("宰牲節", I["adha"], days(I["adha"], 1), "mid", approx=True),
        H("獨立紀念日", D(y, 8, 17), travel="mid"),
        H("聖誕節", D(y, 12, 25), D(y, 12, 26), "mid"),
    ]


@country("PH")
def ph(y):
    I, L, e = ISLAMIC[y], LUNAR[y], easter(y)
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("農曆新年", L["cny"], travel="low"),
        H("聖週（Holy Week）", days(e, -3), days(e, -1), "high",
          note="菲律賓最大出遊潮，長灘島等度假島嶼爆滿"),
        H("勇士日", D(y, 4, 9), travel="low"),
        H("勞動節", D(y, 5, 1), travel="mid"),
        H("獨立紀念日", D(y, 6, 12), travel="mid"),
        H("開齋節", I["fitr"], travel="low", approx=True),
        H("國家英雄日", nth_weekday(y, 8, 0, -1), travel="mid"),
        H("諸聖節", D(y, 11, 1), D(y, 11, 2), "mid"),
        H("博尼法秀日", D(y, 11, 30), travel="low"),
        H("聖誕節", D(y, 12, 24), D(y, 12, 26), "high"),
        H("黎剎日與跨年", D(y, 12, 30), D(y, 12, 31), "high"),
    ]


@country("IN")
def ind(y):
    I, L, e = ISLAMIC[y], LUNAR[y], easter(y)
    return [
        H("共和國日", D(y, 1, 26), travel="mid"),
        H("荷麗節（Holi）", L["holi"], days(L["holi"], 1), "mid"),
        H("耶穌受難日", days(e, -2), travel="low"),
        H("開齋節", I["fitr"], travel="mid", approx=True),
        H("宰牲節", I["adha"], travel="low", approx=True),
        H("獨立紀念日", D(y, 8, 15), travel="mid"),
        H("甘地誕辰", D(y, 10, 2), travel="mid"),
        H("十勝節（Dussehra）", IN_DUSSEHRA[y], travel="mid"),
        H("排燈節（Diwali）", days(L["deepavali"], -1), days(L["deepavali"], 2), "high",
          note="印度最大節慶假期，出境與國內旅遊高峰"),
        H("聖誕節", D(y, 12, 25), travel="low"),
    ]


# ---------------------------------------------------------------- 大洋洲

@country("AU")
def au(y):
    e = easter(y)
    o = lambda x: observe(x, "sun_to_mon")
    return [
        H("元旦", o(D(y, 1, 1)), travel="mid"),
        H("澳洲國慶日", o(D(y, 1, 26)), travel="mid"),
        H("復活節連假", days(e, -2), days(e, 1), "high"),
        H("澳紐軍團日", D(y, 4, 25), travel="mid"),
        H("國王誕辰", nth_weekday(y, 6, 0, 2), travel="mid"),
        H("聖誕節與節禮日", D(y, 12, 25), D(y, 12, 28), "high"),
        H("暑假旺季", D(y, 12, 20), D(y, 12, 31), "high", kind="season",
          note="南半球暑假，澳洲人大量北上東南亞與日本"),
        H("暑假旺季", D(y, 1, 1), D(y, 1, 26), "high", kind="season"),
    ]


@country("NZ")
def nz(y):
    e = easter(y)
    o = lambda x: observe(x, "sun_to_mon")
    return [
        H("元旦假期", D(y, 1, 1), D(y, 1, 2), "mid"),
        H("懷唐伊日", o(D(y, 2, 6)), travel="low"),
        H("復活節連假", days(e, -2), days(e, 1), "high"),
        H("澳紐軍團日", o(D(y, 4, 25)), travel="mid"),
        H("國王誕辰", nth_weekday(y, 6, 0, 1), travel="mid"),
        H("馬塔里基", NZ_MATARIKI[y], travel="mid"),
        H("勞動節", nth_weekday(y, 10, 0, 4), travel="mid"),
        H("聖誕節與節禮日", D(y, 12, 25), D(y, 12, 28), "high"),
        H("暑假旺季", D(y, 12, 20), D(y, 12, 31), "high", kind="season"),
        H("暑假旺季", D(y, 1, 1), D(y, 1, 26), "high", kind="season"),
    ]


# ------------------------------------------------------------------ 歐洲

@country("GB")
def gb(y):
    e = easter(y)
    o = lambda x: observe(x, "next_weekday")
    xmas, boxing = o(D(y, 12, 25)), o(D(y, 12, 26))
    if boxing <= xmas:
        boxing = o(days(xmas, 1))
    return [
        H("元旦", o(D(y, 1, 1)), travel="mid"),
        H("復活節連假", days(e, -2), days(e, 1), "high"),
        H("五月初銀行假日", nth_weekday(y, 5, 0, 1), travel="mid"),
        H("春季銀行假日", nth_weekday(y, 5, 0, -1), travel="high",
          note="與學校 half term 相連，出國旅遊高峰"),
        H("夏季銀行假日", nth_weekday(y, 8, 0, -1), travel="high"),
        H("聖誕節與節禮日", xmas, boxing, "high"),
        H("學校暑假", D(y, 7, 20), D(y, 8, 31), "high", kind="season",
          note="英國家庭出遊旺季，歐洲與地中海線最貴"),
    ]


def _euro_core(y, names):
    """歐陸多國共用的復活節／升天節／聖靈降臨節骨架"""
    e = easter(y)
    return {
        "good_friday": days(e, -2),
        "easter_monday": days(e, 1),
        "ascension": days(e, 39),
        "whit_monday": days(e, 50),
        "corpus": days(e, 60),
    }


@country("DE")
def de(y):
    c = _euro_core(y, None)
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("耶穌受難日與復活節", c["good_friday"], c["easter_monday"], "high"),
        H("勞動節", D(y, 5, 1), travel="mid"),
        H("耶穌升天節", c["ascension"], travel="high", note="常與週五串成 4 天連假"),
        H("聖靈降臨節", c["whit_monday"], travel="high"),
        H("德國統一日", D(y, 10, 3), travel="mid"),
        H("聖誕節", D(y, 12, 25), D(y, 12, 26), "high"),
        H("學校暑假", D(y, 7, 15), D(y, 8, 31), "high", kind="season",
          note="各邦分批放假，歐洲熱門城市與海灘全面客滿"),
    ]


@country("FR")
def fr(y):
    c = _euro_core(y, None)
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("復活節星期一", c["easter_monday"], travel="high"),
        H("勞動節", D(y, 5, 1), travel="mid"),
        H("二戰勝利日", D(y, 5, 8), travel="mid"),
        H("耶穌升天節", c["ascension"], travel="high", note="法國人習慣「搭橋」放到週日"),
        H("聖靈降臨節", c["whit_monday"], travel="mid"),
        H("國慶日", D(y, 7, 14), travel="mid"),
        H("聖母升天日", D(y, 8, 15), travel="high"),
        H("諸聖節", D(y, 11, 1), travel="mid"),
        H("停戰紀念日", D(y, 11, 11), travel="low"),
        H("聖誕節", D(y, 12, 25), travel="high"),
        H("八月休假潮", D(y, 8, 1), D(y, 8, 20), "high", kind="season",
          note="法國全民休假月，南法與地中海一帶最擠"),
    ]


@country("IT")
def it(y):
    c = _euro_core(y, None)
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("主顯節", D(y, 1, 6), travel="mid"),
        H("復活節星期一", c["easter_monday"], travel="high"),
        H("解放日", D(y, 4, 25), travel="mid"),
        H("勞動節", D(y, 5, 1), travel="mid"),
        H("共和國日", D(y, 6, 2), travel="mid"),
        H("八月節（Ferragosto）", D(y, 8, 15), travel="high"),
        H("諸聖節", D(y, 11, 1), travel="mid"),
        H("聖母無染原罪日", D(y, 12, 8), travel="mid"),
        H("聖誕節", D(y, 12, 25), D(y, 12, 26), "high"),
        H("八月休假潮", D(y, 8, 8), D(y, 8, 24), "high", kind="season",
          note="義大利人集體休假，城市店家歇業、海邊爆滿"),
    ]


@country("ES")
def es(y):
    e = easter(y)
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("主顯節", D(y, 1, 6), travel="mid"),
        H("聖週（Semana Santa）", days(e, -7), e, "high",
          note="西班牙最大出遊週，全國飯店與火車一位難求"),
        H("勞動節", D(y, 5, 1), travel="mid"),
        H("聖母升天日", D(y, 8, 15), travel="mid"),
        H("國慶日", D(y, 10, 12), travel="mid"),
        H("諸聖節", D(y, 11, 1), travel="mid"),
        H("行憲紀念日", D(y, 12, 6), travel="high", note="與 12/8 合成 puente 長週末"),
        H("聖母無染原罪日", D(y, 12, 8), travel="high"),
        H("聖誕節", D(y, 12, 25), travel="high"),
        H("八月休假潮", D(y, 8, 1), D(y, 8, 31), "mid", kind="season"),
    ]


@country("NL")
def nl(y):
    c = _euro_core(y, None)
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("復活節連假", c["good_friday"], c["easter_monday"], "high"),
        H("國王日", D(y, 4, 27), travel="mid"),
        H("解放日", D(y, 5, 5), travel="low"),
        H("耶穌升天節", c["ascension"], travel="high"),
        H("聖靈降臨節", c["whit_monday"], travel="mid"),
        H("聖誕節", D(y, 12, 25), D(y, 12, 26), "high"),
        H("學校暑假", D(y, 7, 15), D(y, 8, 25), "high", kind="season"),
    ]


@country("CH")
def ch(y):
    c = _euro_core(y, None)
    return [
        H("元旦", D(y, 1, 1), D(y, 1, 2), "mid"),
        H("復活節連假", c["good_friday"], c["easter_monday"], "high"),
        H("勞動節", D(y, 5, 1), travel="low"),
        H("耶穌升天節", c["ascension"], travel="high"),
        H("聖靈降臨節", c["whit_monday"], travel="mid"),
        H("國慶日", D(y, 8, 1), travel="mid"),
        H("聖誕節", D(y, 12, 25), D(y, 12, 26), "high"),
    ]


@country("AT")
def at(y):
    c = _euro_core(y, None)
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("主顯節", D(y, 1, 6), travel="mid"),
        H("復活節星期一", c["easter_monday"], travel="high"),
        H("國定勞動節", D(y, 5, 1), travel="mid"),
        H("耶穌升天節", c["ascension"], travel="high"),
        H("聖靈降臨節", c["whit_monday"], travel="mid"),
        H("聖體聖血節", c["corpus"], travel="mid"),
        H("聖母升天日", D(y, 8, 15), travel="mid"),
        H("國慶日", D(y, 10, 26), travel="mid"),
        H("諸聖節", D(y, 11, 1), travel="mid"),
        H("聖誕節", D(y, 12, 25), D(y, 12, 26), "high"),
    ]


@country("PL")
def pl(y):
    c = _euro_core(y, None)
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("主顯節", D(y, 1, 6), travel="mid"),
        H("復活節連假", days(easter(y), 0), c["easter_monday"], "high"),
        H("五月連假（Majówka）", D(y, 5, 1), D(y, 5, 3), "high",
          note="波蘭人最愛的出國長週末"),
        H("聖體聖血節", c["corpus"], travel="mid"),
        H("聖母升天日", D(y, 8, 15), travel="mid"),
        H("諸聖節", D(y, 11, 1), travel="mid"),
        H("獨立紀念日", D(y, 11, 11), travel="mid"),
        H("聖誕節", D(y, 12, 25), D(y, 12, 26), "high"),
    ]


def _nordic(y, name_map, midsummer_start_dow):
    c = _euro_core(y, None)
    return c


@country("SE")
def se(y):
    c = _euro_core(y, None)
    midsummer = next(D(y, 6, day) for day in range(19, 26) if D(y, 6, day).weekday() == 4)
    all_saints = next(x for x in (D(y, 10, 31) + dt.timedelta(days=i) for i in range(7))
                      if x.weekday() == 5)
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("主顯節", D(y, 1, 6), travel="low"),
        H("復活節連假", c["good_friday"], c["easter_monday"], "high"),
        H("五一勞動節", D(y, 5, 1), travel="mid"),
        H("耶穌升天節", c["ascension"], travel="high"),
        H("國慶日", D(y, 6, 6), travel="mid"),
        H("仲夏節", days(midsummer, -1), midsummer, "high"),
        H("諸聖節", all_saints, travel="low"),
        H("聖誕節", D(y, 12, 24), D(y, 12, 26), "high"),
        H("工業休假月", D(y, 7, 1), D(y, 7, 31), "high", kind="season",
          note="瑞典人幾乎整個七月休假"),
    ]


@country("NO")
def no(y):
    c = _euro_core(y, None)
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("復活節連假", days(easter(y), -3), c["easter_monday"], "high"),
        H("勞動節", D(y, 5, 1), travel="mid"),
        H("憲法日", D(y, 5, 17), travel="mid"),
        H("耶穌升天節", c["ascension"], travel="high"),
        H("聖靈降臨節", c["whit_monday"], travel="mid"),
        H("聖誕節", D(y, 12, 25), D(y, 12, 26), "high"),
        H("共同休假期", D(y, 7, 1), D(y, 7, 31), "high", kind="season"),
    ]


@country("DK")
def dk(y):
    c = _euro_core(y, None)
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("復活節連假", days(easter(y), -3), c["easter_monday"], "high"),
        H("耶穌升天節", c["ascension"], travel="high"),
        H("聖靈降臨節", c["whit_monday"], travel="mid"),
        H("憲法日", D(y, 6, 5), travel="low"),
        H("聖誕節", D(y, 12, 24), D(y, 12, 26), "high"),
        H("共同休假期", D(y, 7, 1), D(y, 7, 31), "mid", kind="season"),
    ]


@country("FI")
def fi(y):
    c = _euro_core(y, None)
    midsummer = next(D(y, 6, day) for day in range(20, 27) if D(y, 6, day).weekday() == 5)
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("主顯節", D(y, 1, 6), travel="low"),
        H("復活節連假", c["good_friday"], c["easter_monday"], "high"),
        H("五一節（Vappu）", D(y, 5, 1), travel="mid"),
        H("耶穌升天節", c["ascension"], travel="mid"),
        H("仲夏節", days(midsummer, -1), midsummer, "high"),
        H("獨立紀念日", D(y, 12, 6), travel="mid"),
        H("聖誕節", D(y, 12, 24), D(y, 12, 26), "high"),
        H("共同休假期", D(y, 7, 1), D(y, 7, 31), "high", kind="season"),
    ]


@country("RU")
def ru(y):
    return [
        H("新年假期", D(y, 1, 1), D(y, 1, 8), "high",
          note="俄羅斯最長假期，東南亞海島與滑雪場人潮明顯增加"),
        H("祖國保衛者日", D(y, 2, 23), travel="mid"),
        H("國際婦女節", D(y, 3, 8), travel="mid"),
        H("春天與勞動節", D(y, 5, 1), D(y, 5, 3), "high"),
        H("勝利日", D(y, 5, 9), travel="mid"),
        H("俄羅斯日", D(y, 6, 12), travel="mid"),
        H("民族團結日", D(y, 11, 4), travel="mid"),
    ]


# ------------------------------------------------------------------ 美洲

@country("US")
def us(y):
    o = lambda x: observe(x, "us")
    thanksgiving = nth_weekday(y, 11, 3, 4)
    return [
        H("元旦", o(D(y, 1, 1)), travel="mid"),
        H("馬丁路德金恩紀念日", nth_weekday(y, 1, 0, 3), travel="mid"),
        H("總統日", nth_weekday(y, 2, 0, 3), travel="mid"),
        H("陣亡將士紀念日", nth_weekday(y, 5, 0, -1), travel="high",
          note="美國夏季旅遊季開跑的長週末"),
        H("六月節", o(D(y, 6, 19)), travel="low"),
        H("獨立紀念日", o(D(y, 7, 4)), travel="high"),
        H("勞動節", nth_weekday(y, 9, 0, 1), travel="high"),
        H("哥倫布日", nth_weekday(y, 10, 0, 2), travel="mid"),
        H("退伍軍人節", o(D(y, 11, 11)), travel="mid"),
        H("感恩節連假", days(thanksgiving, -1), days(thanksgiving, 3), "high",
          note="美國一年中機場最擁擠的期間"),
        H("聖誕節", o(D(y, 12, 25)), travel="high"),
        H("耶誕新年旅遊季", D(y, 12, 20), D(y, 12, 31), "high", kind="season"),
    ]


@country("CA")
def ca(y):
    e = easter(y)
    victoria = next(D(y, 5, day) for day in range(18, 25) if D(y, 5, day).weekday() == 0)
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("耶穌受難日", days(e, -2), travel="high"),
        H("維多利亞日", victoria, travel="mid"),
        H("加拿大日", D(y, 7, 1), travel="mid"),
        H("勞動節", nth_weekday(y, 9, 0, 1), travel="high"),
        H("感恩節", nth_weekday(y, 10, 0, 2), travel="mid"),
        H("國殤紀念日", D(y, 11, 11), travel="low"),
        H("聖誕節與節禮日", D(y, 12, 25), D(y, 12, 26), "high"),
    ]


@country("MX")
def mx(y):
    e = easter(y)
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("行憲紀念日", nth_weekday(y, 2, 0, 1), travel="mid"),
        H("華雷斯誕辰", nth_weekday(y, 3, 0, 3), travel="mid"),
        H("聖週", days(e, -7), e, "high", note="墨西哥全國度假週，海灘度假區客滿"),
        H("勞動節", D(y, 5, 1), travel="mid"),
        H("獨立紀念日", D(y, 9, 16), travel="mid"),
        H("亡靈節", D(y, 11, 2), travel="mid"),
        H("革命紀念日", nth_weekday(y, 11, 0, 3), travel="mid"),
        H("瓜達露佩聖母日", D(y, 12, 12), travel="low"),
        H("聖誕節", D(y, 12, 25), travel="high"),
    ]


@country("BR")
def br(y):
    e = easter(y)
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("嘉年華", days(e, -48), days(e, -46), "high",
          note="巴西全國停擺，國內外旅遊需求爆量"),
        H("耶穌受難日", days(e, -2), travel="high"),
        H("蒂拉登特斯日", D(y, 4, 21), travel="mid"),
        H("勞動節", D(y, 5, 1), travel="mid"),
        H("基督聖體節", days(e, 60), travel="mid"),
        H("獨立紀念日", D(y, 9, 7), travel="mid"),
        H("聖母顯現日", D(y, 10, 12), travel="mid"),
        H("追思亡者日", D(y, 11, 2), travel="mid"),
        H("共和國宣言日", D(y, 11, 15), travel="mid"),
        H("黑人意識日", D(y, 11, 20), travel="low"),
        H("聖誕節", D(y, 12, 25), travel="high"),
    ]


@country("AR")
def ar(y):
    e = easter(y)
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("嘉年華", days(e, -48), days(e, -47), "high"),
        H("真相與正義紀念日", D(y, 3, 24), travel="mid"),
        H("馬爾維納斯退伍軍人日", D(y, 4, 2), travel="mid"),
        H("耶穌受難日", days(e, -2), travel="mid"),
        H("勞動節", D(y, 5, 1), travel="mid"),
        H("五月革命紀念日", D(y, 5, 25), travel="mid"),
        H("獨立紀念日", D(y, 7, 9), travel="mid"),
        H("聖馬丁紀念日", nth_weekday(y, 8, 0, 3), travel="mid"),
        H("文化多元日", D(y, 10, 12), travel="mid"),
        H("主權日", D(y, 11, 20), travel="mid"),
        H("聖誕節", D(y, 12, 25), travel="high"),
    ]


# -------------------------------------------------------------- 中東與非洲

@country("TR")
def tr(y):
    I = ISLAMIC[y]
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("開齋節（Ramazan Bayramı）", days(I["fitr"], -1), days(I["fitr"], 2), "high",
          approx=True, note="土耳其人大量出遊，國內線與海岸城市爆滿"),
        H("國家主權與兒童日", D(y, 4, 23), travel="mid"),
        H("勞動節", D(y, 5, 1), travel="mid"),
        H("青年與體育日", D(y, 5, 19), travel="mid"),
        H("宰牲節（Kurban Bayramı）", days(I["adha"], -1), days(I["adha"], 3), "high", approx=True),
        H("民主日", D(y, 7, 15), travel="low"),
        H("勝利日", D(y, 8, 30), travel="mid"),
        H("共和國日", D(y, 10, 29), travel="mid"),
    ]


@country("AE")
def ae(y):
    I = ISLAMIC[y]
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("開齋節", days(I["fitr"], -1), days(I["fitr"], 2), "high", approx=True),
        H("阿拉法特日與宰牲節", days(I["adha"], -1), days(I["adha"], 2), "high", approx=True),
        H("伊斯蘭新年", days(I["adha"], 21), travel="low", approx=True),
        H("先知誕辰", days(I["adha"], 80), travel="low", approx=True),
        H("烈士日與國慶日", D(y, 12, 1), D(y, 12, 3), "high"),
    ]


@country("SA")
def sa(y):
    I = ISLAMIC[y]
    return [
        H("建國日", D(y, 2, 22), travel="mid"),
        H("開齋節", days(I["fitr"], -3), days(I["fitr"], 3), "high", approx=True,
          note="沙國最大出境旅遊潮"),
        H("宰牲節與朝覲", days(I["adha"], -3), days(I["adha"], 3), "high", approx=True),
        H("國慶日", D(y, 9, 23), travel="mid"),
    ]


@country("IL")
def il(y):
    T = IL_TABLE[y]
    return [
        H("普珥節", T["purim"], travel="low"),
        H("逾越節", T["pesach"][0], T["pesach"][1], "high",
          note="以色列全國放假，出國旅遊高峰"),
        H("五旬節", T["shavuot"], travel="mid"),
        H("猶太新年", T["rosh"][0], T["rosh"][1], "high"),
        H("贖罪日", T["kippur"], travel="mid"),
        H("住棚節", T["sukkot"][0], T["sukkot"][1], "high"),
    ]


@country("ZA")
def za(y):
    e = easter(y)
    o = lambda x: observe(x, "sun_to_mon")
    return [
        H("元旦", o(D(y, 1, 1)), travel="mid"),
        H("人權日", o(D(y, 3, 21)), travel="low"),
        H("復活節連假", days(e, -2), days(e, 1), "high"),
        H("自由日", o(D(y, 4, 27)), travel="mid"),
        H("勞動節", o(D(y, 5, 1)), travel="mid"),
        H("青年日", o(D(y, 6, 16)), travel="low"),
        H("全國婦女日", o(D(y, 8, 9)), travel="low"),
        H("文化傳承日", o(D(y, 9, 24)), travel="mid"),
        H("和解日", o(D(y, 12, 16)), travel="mid"),
        H("聖誕節與友善日", D(y, 12, 25), D(y, 12, 26), "high"),
    ]


@country("EG")
def eg(y):
    I = ISLAMIC[y]
    return [
        H("科普特聖誕節", D(y, 1, 7), travel="low"),
        H("革命紀念日", D(y, 1, 25), travel="low"),
        H("西奈解放日", D(y, 4, 25), travel="low"),
        H("聞風節", EG_SHAM[y], travel="mid"),
        H("勞動節", D(y, 5, 1), travel="mid"),
        H("開齋節", I["fitr"], days(I["fitr"], 2), "high", approx=True),
        H("七月革命紀念日", D(y, 7, 23), travel="low"),
        H("宰牲節", days(I["adha"], -1), days(I["adha"], 2), "high", approx=True),
        H("武裝部隊日", D(y, 10, 6), travel="low"),
    ]


# ------------------------------------------------------------------- 輸出

def main():
    countries = []
    holidays = {}
    for code, name, en, flag, region, weight in COUNTRIES:
        meta = {"code": code, "name": name, "en": en, "flag": flag,
                "region": region, "weight": weight}
        if code in WEEKENDS:
            meta["weekend"] = WEEKENDS[code]
        countries.append(meta)

        build = BUILDERS.get(code)
        if build is None:
            raise SystemExit(f"缺少 {code} 的假期定義")
        entries = []
        for y in YEARS:
            entries.extend(build(y))
        entries.sort(key=lambda x: (x["start"], x["end"]))
        # 去重（跨年度重複產生的季節性區間）
        seen, deduped = set(), []
        for x in entries:
            key = (x["name"], x["start"], x["end"])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(x)
        holidays[code] = deduped

    payload = {
        "generated": dt.date.today().isoformat(),
        "years": YEARS,
        "countries": countries,
        "holidays": holidays,
    }
    out = ROOT / "data" / "holidays.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")
    total = sum(len(v) for v in holidays.values())
    print(f"寫入 {out}：{len(countries)} 個國家 / {total} 筆假期 / {out.stat().st_size/1024:.0f} KB")


if __name__ == "__main__":
    main()
