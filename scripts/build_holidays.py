# -*- coding: utf-8 -*-
"""
產生「全球連假雷達」使用的假期資料 (data/holidays.json)。

設計原則
--------
* 能用規則算的就用規則算（復活節、東正教復活節、第 n 個星期幾、補假），
  避免手 key 出錯。
* 大多數國家的假期是同一套骨架 + 幾個國定紀念日，所以用「範本 + 國慶日」
  的方式描述（PROFILES / SIMPLE），只有假期結構特殊的國家才單獨寫函式。
* 農曆 / 伊斯蘭曆 / 波斯曆節日以「錨點日期」表驅動，集中管理、方便逐年更新。
* travel 欄位 = 這個假期帶動「跨國」旅遊的程度，是外來人潮的權重。
* closure 欄位（在國家層級）= 當地放假時商店開不開，給目的地模式用。

更新方式：改下方 LUNAR / ISLAMIC / PERSIAN 錨點與 YEARS，再執行
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
    """Anonymous Gregorian algorithm -> 西方復活節主日"""
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


def orthodox_easter(year):
    """Meeus 儒略曆演算法 -> 東正教復活節（1900–2099 加 13 天轉西曆）"""
    a, b, c = year % 4, year % 7, year % 19
    dd = (19 * c + 15) % 30
    e = (2 * a + 4 * b - dd + 34) % 7
    month = (dd + e + 114) // 31
    day = ((dd + e + 114) % 31) + 1
    return D(year, month, day) + dt.timedelta(days=13)


def nth_weekday(year, month, weekday, n):
    """weekday: 0=週一 .. 6=週日；n 為第幾個，-1 表示最後一個"""
    if n > 0:
        first = D(year, month, 1)
        offset = (weekday - first.weekday()) % 7
        return first + dt.timedelta(days=offset + 7 * (n - 1))
    last_day = (D(year, month, 28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
    offset = (last_day.weekday() - weekday) % 7
    return last_day - dt.timedelta(days=offset)


def next_weekday_after(day, weekday):
    """day 之後（不含當日）的第一個指定星期幾"""
    offset = (weekday - day.weekday() - 1) % 7 + 1
    return day + dt.timedelta(days=offset)


def observe(day, rule):
    """把落在週末的假日移到補假日。rule 決定各國作法。"""
    wd = day.weekday()  # 5=週六 6=週日
    if rule == "tw":
        if wd == 5:
            return day - dt.timedelta(days=1)
        if wd == 6:
            return day + dt.timedelta(days=1)
    elif rule == "sun_to_mon":
        if wd == 6:
            return day + dt.timedelta(days=1)
    elif rule == "us":
        if wd == 5:
            return day - dt.timedelta(days=1)
        if wd == 6:
            return day + dt.timedelta(days=1)
    elif rule == "next_weekday":
        while day.weekday() >= 5:
            day += dt.timedelta(days=1)
    return day


def days(base, n):
    return base + dt.timedelta(days=n)


# --------------------------------------------- 農曆 / 伊斯蘭曆 / 波斯曆錨點
# 農曆節日換算後的西曆日期。伊斯蘭曆節日依實際觀月可能±1~2天，標記為 approx。
LUNAR = {
    2026: {
        "cny": d("2026-02-17"), "nye": d("2026-02-16"),
        "qingming": d("2026-04-05"), "dragon": d("2026-06-19"),
        "midautumn": d("2026-09-25"), "chongyang": d("2026-10-18"),
        "buddha": d("2026-05-24"), "vesak": d("2026-05-31"),
        "seollal": d("2026-02-17"), "chuseok": d("2026-09-25"),
        "deepavali": d("2026-11-08"), "holi": d("2026-03-03"),
        "dashain": d("2026-10-19"), "tihar": d("2026-11-08"),
    },
    2027: {
        "cny": d("2027-02-06"), "nye": d("2027-02-05"),
        "qingming": d("2027-04-05"), "dragon": d("2027-06-09"),
        "midautumn": d("2027-09-15"), "chongyang": d("2027-10-08"),
        "buddha": d("2027-05-13"), "vesak": d("2027-05-20"),
        "seollal": d("2027-02-06"), "chuseok": d("2027-09-15"),
        "deepavali": d("2027-10-29"), "holi": d("2027-03-21"),
        "dashain": d("2027-10-09"), "tihar": d("2027-10-29"),
    },
}

ISLAMIC = {
    2026: {"ramadan": d("2026-02-18"), "fitr": d("2026-03-20"), "adha": d("2026-05-27"),
           "newyear": d("2026-06-16"), "mawlid": d("2026-08-25")},
    2027: {"ramadan": d("2027-02-07"), "fitr": d("2027-03-09"), "adha": d("2027-05-16"),
           "newyear": d("2027-06-06"), "mawlid": d("2027-08-15")},
}

# 諾魯茲（波斯新年）—— 伊朗、中亞、高加索一帶
# 伊朗的諾魯茲跟著春分走；中亞與高加索各國則是法定的固定日期，兩者要分開。
PERSIAN = {2026: d("2026-03-20"), 2027: d("2027-03-20")}

# 其他需要逐年查表的節日
JP_EQUINOX = {2026: (d("2026-03-20"), d("2026-09-23")), 2027: (d("2027-03-21"), d("2027-09-23"))}
TH_LUNAR = {2026: {"makha": d("2026-03-03"), "asalha": d("2026-07-29")},
            2027: {"makha": d("2027-02-21"), "asalha": d("2027-07-18")}}
ID_NYEPI = {2026: d("2026-03-19"), 2027: d("2027-03-08")}
NZ_MATARIKI = {2026: d("2026-07-10"), 2027: d("2027-06-25")}
IN_DUSSEHRA = {2026: d("2026-10-20"), 2027: d("2027-10-09")}
VN_HUNG = {2026: d("2026-04-26"), 2027: d("2027-04-16")}
EG_SHAM = {2026: d("2026-04-13"), 2027: d("2027-05-03")}
KH_PCHUM = {2026: d("2026-09-21"), 2027: d("2027-10-10")}
# 蒙古白月節通常比農曆春節晚一天
MN_TSAGAAN = {2026: d("2026-02-18"), 2027: d("2027-02-07")}
IL_TABLE = {
    2026: {"purim": d("2026-03-03"), "pesach": (d("2026-04-02"), d("2026-04-08")),
           "shavuot": d("2026-05-22"), "rosh": (d("2026-09-12"), d("2026-09-13")),
           "kippur": d("2026-09-21"), "sukkot": (d("2026-09-26"), d("2026-10-02"))},
    2027: {"purim": d("2027-03-23"), "pesach": (d("2027-04-22"), d("2027-04-28")),
           "shavuot": d("2027-06-11"), "rosh": (d("2027-10-02"), d("2027-10-03")),
           "kippur": d("2027-10-11"), "sukkot": (d("2027-10-16"), d("2027-10-22"))},
}


def H(name, start, end=None, travel="low", approx=False, kind="public",
      note=None, closed=None):
    e = {"name": name, "start": start.isoformat(),
         "end": (end or start).isoformat(), "travel": travel}
    if approx:
        e["approx"] = True
    if kind != "public":
        e["kind"] = kind
    if note:
        e["note"] = note
    if closed is not None:
        e["closed"] = closed          # 覆寫國家層級的營業狀況
    return e


# ---------------------------------------------------------------- 假期範本
# 大多數國家的假期 = 一套宗教/文化骨架 + 幾個國定紀念日。

def p_west_cath(y, good_friday=True):
    e = easter(y)
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("復活節連假", days(e, -2 if good_friday else 0), days(e, 1), "high"),
        H("勞動節", D(y, 5, 1), travel="mid"),
        H("聖母升天日", D(y, 8, 15), travel="mid"),
        H("諸聖節", D(y, 11, 1), travel="mid"),
        H("聖誕節", D(y, 12, 25), D(y, 12, 26), "high"),
    ]


def p_west_prot(y):
    e = easter(y)
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("復活節連假", days(e, -2), days(e, 1), "high"),
        H("勞動節", D(y, 5, 1), travel="mid"),
        H("耶穌升天節", days(e, 39), travel="high"),
        H("聖靈降臨節", days(e, 50), travel="mid"),
        H("聖誕節", D(y, 12, 25), D(y, 12, 26), "high"),
    ]


def p_orthodox(y):
    oe = orthodox_easter(y)
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("東正教聖誕節", D(y, 1, 7), travel="mid"),
        H("東正教復活節連假", days(oe, -2), days(oe, 1), "high"),
        H("勞動節", D(y, 5, 1), travel="mid"),
    ]


def p_muslim(y):
    I = ISLAMIC[y]
    return [
        H("齋戒月", I["ramadan"], days(I["ramadan"], 28), "low", approx=True, kind="season",
          note="白天多數餐廳與咖啡店不營業，日落後才熱鬧起來"),
        H("開齋節", days(I["fitr"], -1), days(I["fitr"], 2), "high", approx=True, closed=True,
          note="全國最大節慶，商店與景點多半休息數日"),
        H("宰牲節", days(I["adha"], -1), days(I["adha"], 2), "high", approx=True, closed=True),
        H("伊斯蘭新年", I["newyear"], travel="low", approx=True),
        H("先知誕辰", I["mawlid"], travel="low", approx=True),
    ]


def p_latin(y):
    e = easter(y)
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("聖週", days(e, -3), e, "high", note="拉丁美洲全區度假週"),
        H("勞動節", D(y, 5, 1), travel="mid"),
        H("聖誕節", D(y, 12, 25), travel="high"),
    ]


def p_anglo(y):
    e = easter(y)
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("復活節連假", days(e, -2), days(e, 1), "high"),
        H("勞動節", D(y, 5, 1), travel="mid"),
        H("聖誕節與節禮日", D(y, 12, 25), D(y, 12, 26), "high"),
    ]


def p_persian(y):
    n = PERSIAN[y]
    return [H("諾魯茲（波斯新年）", n, days(n, 3), "high", note="全區最大長假，交通與住宿全滿")]


PROFILES = {
    "west_cath": p_west_cath,
    "west_cath_nogf": lambda y: p_west_cath(y, good_friday=False), "west_prot": p_west_prot, "orthodox": p_orthodox,
    "muslim": p_muslim, "latin": p_latin, "anglo": p_anglo, "persian": p_persian,
}


# ---------------------------------------------------------------- 國家清單
# weight  = 出境旅遊「人潮影響力」(0-100)，用來加權外來人潮。
# closure = 當地放假時的營業狀況：
#           open    幾乎照常營業
#           partial 銀行與公家機關休息，觀光區大多照常
#           strict  多數商店、超市、博物館休息
COUNTRIES = [
    # code, 中文名, English, 旗, 區域, weight, closure
    ("CN", "中國", "China", "🇨🇳", "東亞", 100, "open"),
    ("JP", "日本", "Japan", "🇯🇵", "東亞", 82, "open"),
    ("KR", "韓國", "South Korea", "🇰🇷", "東亞", 76, "open"),
    ("TW", "台灣", "Taiwan", "🇹🇼", "東亞", 62, "open"),
    ("HK", "香港", "Hong Kong", "🇭🇰", "東亞", 56, "open"),
    ("MO", "澳門", "Macau", "🇲🇴", "東亞", 20, "open"),
    ("MN", "蒙古", "Mongolia", "🇲🇳", "東亞", 8, "partial"),

    ("SG", "新加坡", "Singapore", "🇸🇬", "東南亞", 52, "open"),
    ("MY", "馬來西亞", "Malaysia", "🇲🇾", "東南亞", 46, "partial"),
    ("TH", "泰國", "Thailand", "🇹🇭", "東南亞", 46, "open"),
    ("VN", "越南", "Vietnam", "🇻🇳", "東南亞", 42, "partial"),
    ("ID", "印尼", "Indonesia", "🇮🇩", "東南亞", 46, "partial"),
    ("PH", "菲律賓", "Philippines", "🇵🇭", "東南亞", 36, "partial"),
    ("KH", "柬埔寨", "Cambodia", "🇰🇭", "東南亞", 12, "partial"),
    ("LA", "寮國", "Laos", "🇱🇦", "東南亞", 8, "partial"),
    ("MM", "緬甸", "Myanmar", "🇲🇲", "東南亞", 10, "partial"),
    ("BN", "汶萊", "Brunei", "🇧🇳", "東南亞", 8, "strict"),

    ("IN", "印度", "India", "🇮🇳", "南亞", 60, "partial"),
    ("NP", "尼泊爾", "Nepal", "🇳🇵", "南亞", 10, "partial"),
    ("LK", "斯里蘭卡", "Sri Lanka", "🇱🇰", "南亞", 12, "partial"),
    ("MV", "馬爾地夫", "Maldives", "🇲🇻", "南亞", 6, "open"),
    ("BD", "孟加拉", "Bangladesh", "🇧🇩", "南亞", 20, "partial"),
    ("PK", "巴基斯坦", "Pakistan", "🇵🇰", "南亞", 22, "partial"),

    ("KZ", "哈薩克", "Kazakhstan", "🇰🇿", "中亞高加索", 16, "partial"),
    ("UZ", "烏茲別克", "Uzbekistan", "🇺🇿", "中亞高加索", 12, "partial"),
    ("GE", "喬治亞", "Georgia", "🇬🇪", "中亞高加索", 10, "partial"),
    ("AM", "亞美尼亞", "Armenia", "🇦🇲", "中亞高加索", 8, "partial"),
    ("AZ", "亞塞拜然", "Azerbaijan", "🇦🇿", "中亞高加索", 10, "partial"),

    ("TR", "土耳其", "Türkiye", "🇹🇷", "中東", 36, "partial"),
    ("IL", "以色列", "Israel", "🇮🇱", "中東", 20, "strict"),
    ("AE", "阿聯", "UAE", "🇦🇪", "中東", 36, "partial"),
    ("SA", "沙烏地阿拉伯", "Saudi Arabia", "🇸🇦", "中東", 36, "strict"),
    ("QA", "卡達", "Qatar", "🇶🇦", "中東", 14, "partial"),
    ("KW", "科威特", "Kuwait", "🇰🇼", "中東", 14, "partial"),
    ("BH", "巴林", "Bahrain", "🇧🇭", "中東", 8, "partial"),
    ("OM", "阿曼", "Oman", "🇴🇲", "中東", 8, "partial"),
    ("JO", "約旦", "Jordan", "🇯🇴", "中東", 8, "partial"),
    ("LB", "黎巴嫩", "Lebanon", "🇱🇧", "中東", 8, "partial"),
    ("IR", "伊朗", "Iran", "🇮🇷", "中東", 16, "strict"),
    ("IQ", "伊拉克", "Iraq", "🇮🇶", "中東", 10, "partial"),

    ("GB", "英國", "United Kingdom", "🇬🇧", "歐洲", 66, "partial"),
    ("IE", "愛爾蘭", "Ireland", "🇮🇪", "歐洲", 22, "strict"),
    ("FR", "法國", "France", "🇫🇷", "歐洲", 66, "strict"),
    ("DE", "德國", "Germany", "🇩🇪", "歐洲", 70, "strict"),
    ("NL", "荷蘭", "Netherlands", "🇳🇱", "歐洲", 40, "strict"),
    ("BE", "比利時", "Belgium", "🇧🇪", "歐洲", 26, "strict"),
    ("LU", "盧森堡", "Luxembourg", "🇱🇺", "歐洲", 6, "strict"),
    ("CH", "瑞士", "Switzerland", "🇨🇭", "歐洲", 30, "strict"),
    ("AT", "奧地利", "Austria", "🇦🇹", "歐洲", 28, "strict"),
    ("IT", "義大利", "Italy", "🇮🇹", "歐洲", 56, "strict"),
    ("ES", "西班牙", "Spain", "🇪🇸", "歐洲", 50, "strict"),
    ("PT", "葡萄牙", "Portugal", "🇵🇹", "歐洲", 24, "strict"),
    ("GR", "希臘", "Greece", "🇬🇷", "歐洲", 20, "strict"),
    ("MT", "馬爾他", "Malta", "🇲🇹", "歐洲", 6, "strict"),
    ("CY", "賽普勒斯", "Cyprus", "🇨🇾", "歐洲", 6, "strict"),
    ("DK", "丹麥", "Denmark", "🇩🇰", "歐洲", 22, "strict"),
    ("SE", "瑞典", "Sweden", "🇸🇪", "歐洲", 26, "strict"),
    ("NO", "挪威", "Norway", "🇳🇴", "歐洲", 24, "strict"),
    ("FI", "芬蘭", "Finland", "🇫🇮", "歐洲", 20, "strict"),
    ("IS", "冰島", "Iceland", "🇮🇸", "歐洲", 6, "strict"),
    ("EE", "愛沙尼亞", "Estonia", "🇪🇪", "歐洲", 6, "strict"),
    ("LV", "拉脫維亞", "Latvia", "🇱🇻", "歐洲", 6, "strict"),
    ("LT", "立陶宛", "Lithuania", "🇱🇹", "歐洲", 8, "strict"),
    ("PL", "波蘭", "Poland", "🇵🇱", "歐洲", 32, "strict"),
    ("CZ", "捷克", "Czechia", "🇨🇿", "歐洲", 20, "strict"),
    ("SK", "斯洛伐克", "Slovakia", "🇸🇰", "歐洲", 10, "strict"),
    ("HU", "匈牙利", "Hungary", "🇭🇺", "歐洲", 14, "strict"),
    ("SI", "斯洛維尼亞", "Slovenia", "🇸🇮", "歐洲", 8, "strict"),
    ("HR", "克羅埃西亞", "Croatia", "🇭🇷", "歐洲", 12, "strict"),
    ("BA", "波士尼亞", "Bosnia & Herzegovina", "🇧🇦", "歐洲", 6, "partial"),
    ("RS", "塞爾維亞", "Serbia", "🇷🇸", "歐洲", 10, "partial"),
    ("ME", "蒙特內哥羅", "Montenegro", "🇲🇪", "歐洲", 4, "partial"),
    ("MK", "北馬其頓", "North Macedonia", "🇲🇰", "歐洲", 4, "partial"),
    ("AL", "阿爾巴尼亞", "Albania", "🇦🇱", "歐洲", 6, "partial"),
    ("RO", "羅馬尼亞", "Romania", "🇷🇴", "歐洲", 16, "partial"),
    ("BG", "保加利亞", "Bulgaria", "🇧🇬", "歐洲", 10, "partial"),
    ("UA", "烏克蘭", "Ukraine", "🇺🇦", "歐洲", 12, "partial"),
    ("RU", "俄羅斯", "Russia", "🇷🇺", "歐洲", 44, "partial"),
    ("BY", "白俄羅斯", "Belarus", "🇧🇾", "歐洲", 8, "partial"),
    ("MD", "摩爾多瓦", "Moldova", "🇲🇩", "歐洲", 4, "partial"),

    ("US", "美國", "United States", "🇺🇸", "北美", 86, "partial"),
    ("CA", "加拿大", "Canada", "🇨🇦", "北美", 46, "partial"),
    ("MX", "墨西哥", "Mexico", "🇲🇽", "北美", 36, "partial"),

    ("GT", "瓜地馬拉", "Guatemala", "🇬🇹", "中南美", 6, "partial"),
    ("CR", "哥斯大黎加", "Costa Rica", "🇨🇷", "中南美", 6, "partial"),
    ("PA", "巴拿馬", "Panama", "🇵🇦", "中南美", 6, "partial"),
    ("CU", "古巴", "Cuba", "🇨🇺", "中南美", 6, "partial"),
    ("DO", "多明尼加", "Dominican Republic", "🇩🇴", "中南美", 6, "partial"),
    ("JM", "牙買加", "Jamaica", "🇯🇲", "中南美", 4, "partial"),
    ("CO", "哥倫比亞", "Colombia", "🇨🇴", "中南美", 16, "partial"),
    ("VE", "委內瑞拉", "Venezuela", "🇻🇪", "中南美", 6, "partial"),
    ("EC", "厄瓜多", "Ecuador", "🇪🇨", "中南美", 6, "partial"),
    ("PE", "秘魯", "Peru", "🇵🇪", "中南美", 12, "partial"),
    ("BO", "玻利維亞", "Bolivia", "🇧🇴", "中南美", 4, "partial"),
    ("CL", "智利", "Chile", "🇨🇱", "中南美", 18, "partial"),
    ("AR", "阿根廷", "Argentina", "🇦🇷", "中南美", 20, "partial"),
    ("UY", "烏拉圭", "Uruguay", "🇺🇾", "中南美", 6, "partial"),
    ("PY", "巴拉圭", "Paraguay", "🇵🇾", "中南美", 4, "partial"),
    ("BR", "巴西", "Brazil", "🇧🇷", "中南美", 36, "partial"),

    ("EG", "埃及", "Egypt", "🇪🇬", "非洲", 16, "partial"),
    ("MA", "摩洛哥", "Morocco", "🇲🇦", "非洲", 14, "partial"),
    ("TN", "突尼西亞", "Tunisia", "🇹🇳", "非洲", 8, "partial"),
    ("DZ", "阿爾及利亞", "Algeria", "🇩🇿", "非洲", 10, "partial"),
    ("ZA", "南非", "South Africa", "🇿🇦", "非洲", 20, "partial"),
    ("KE", "肯亞", "Kenya", "🇰🇪", "非洲", 8, "partial"),
    ("TZ", "坦尚尼亞", "Tanzania", "🇹🇿", "非洲", 6, "partial"),
    ("ET", "衣索比亞", "Ethiopia", "🇪🇹", "非洲", 6, "partial"),
    ("NG", "奈及利亞", "Nigeria", "🇳🇬", "非洲", 12, "partial"),
    ("GH", "迦納", "Ghana", "🇬🇭", "非洲", 4, "partial"),
    ("SN", "塞內加爾", "Senegal", "🇸🇳", "非洲", 4, "partial"),
    ("MU", "模里西斯", "Mauritius", "🇲🇺", "非洲", 4, "partial"),
    ("SC", "塞席爾", "Seychelles", "🇸🇨", "非洲", 2, "partial"),
    ("ZW", "辛巴威", "Zimbabwe", "🇿🇼", "非洲", 4, "partial"),
    ("UG", "烏干達", "Uganda", "🇺🇬", "非洲", 4, "partial"),
    ("NA", "納米比亞", "Namibia", "🇳🇦", "非洲", 4, "partial"),
    ("BW", "波札那", "Botswana", "🇧🇼", "非洲", 4, "partial"),

    ("AU", "澳洲", "Australia", "🇦🇺", "大洋洲", 50, "partial"),
    ("NZ", "紐西蘭", "New Zealand", "🇳🇿", "大洋洲", 24, "partial"),
    ("FJ", "斐濟", "Fiji", "🇫🇯", "大洋洲", 4, "partial"),
    ("PG", "巴布亞紐幾內亞", "Papua New Guinea", "🇵🇬", "大洋洲", 2, "partial"),
    ("PW", "帛琉", "Palau", "🇵🇼", "大洋洲", 2, "partial"),
]

# 已逐一對照各國官方公告或權威來源核對過 2026 年假期的國家。
# 未列入的國家仍以節期範本產生，涵蓋主要假期，但未經逐項查證。
VERIFIED = {
    "CN", "JP", "KR", "TW", "HK", "MO", "MN",
    "SG", "MY", "TH", "VN", "ID", "PH", "KH", "LA",
    "IN", "NP",
    "KZ", "UZ", "AZ", "GE",
    "TR", "AE", "SA", "IL", "QA", "KW", "BH", "OM", "IQ",
    "GB", "IE", "FR", "DE", "NL", "BE", "LU", "CH", "AT", "IT", "ES", "PT",
    "GR", "MT", "CY", "SE", "IS", "EE", "PL", "CZ", "SK", "HU", "SI", "HR", "RU",
    "US", "CA", "MX", "BR", "CL", "PE",
    "EG", "ZA", "KE",
}

# 週末不是週六日的國家（0=週一 … 6=週日）
WEEKENDS = {
    "SA": [4, 5], "IL": [4, 5], "EG": [4, 5], "KW": [4, 5], "QA": [4, 5],
    "BH": [4, 5], "OM": [4, 5], "JO": [4, 5], "IQ": [4, 5], "IR": [4, 5],
    "AF": [3, 4], "BD": [4, 5], "MV": [4, 5], "DZ": [4, 5], "LY": [4, 5],
}


# --------------------------------------- 用範本描述的國家（profile + 紀念日）
# p = 假期範本；n = 固定日期的國定紀念日 (名稱, 月, 日, travel)；x = 需要計算的節日
def S(p=None, n=(), x=None):
    return {"p": p, "n": list(n), "x": x}


def _oe(y, off):
    return days(orthodox_easter(y), off)


def _e(y, off):
    return days(easter(y), off)


SIMPLE = {
    # ---------------------------------------------------------- 東亞 / 東南亞
    "MN": S(n=[("元旦", 1, 1, "mid"), ("婦女節", 3, 8, "low"), ("兒童節", 6, 1, "low"),
               ("獨立紀念日", 12, 29, "low")],
            x=lambda y: [
                H("白月節（Tsagaan Sar）", MN_TSAGAAN[y], days(MN_TSAGAAN[y], 2), "high",
                  approx=True, note="蒙古最大節慶，全國返鄉"),
                H("那達慕大會", D(y, 7, 10), D(y, 7, 15), "high", note="全國停擺的傳統運動會")]),
    "KH": S(n=[("元旦", 1, 1, "mid"), ("勝利日", 1, 7, "low"), ("婦女節", 3, 8, "low"),
               ("勞動節", 5, 1, "mid"), ("國王誕辰", 5, 14, "low"), ("憲法日", 9, 24, "low"),
               ("獨立紀念日", 11, 9, "low")],
            x=lambda y: [
                H("高棉新年", D(y, 4, 14), D(y, 4, 16), "high", closed=True,
                  note="全國放假返鄉，吳哥窟一帶人潮最多"),
                H("御耕節", D(y, 5, 15), travel="low"),
                H("王太后誕辰", D(y, 6, 18), travel="low"),
                H("亡人節（Pchum Ben）", KH_PCHUM[y], days(KH_PCHUM[y], 2), "high", approx=True),
                H("送水節", D(y, 11, 23), D(y, 11, 25), "mid", approx=True)]),
    "LA": S(n=[("元旦", 1, 1, "mid"), ("建軍節", 1, 20, "low"), ("婦女節", 3, 8, "low"),
               ("勞動節", 5, 1, "mid"), ("國慶日", 12, 2, "mid")],
            x=lambda y: [H("寮國新年（Pi Mai）", D(y, 4, 13), D(y, 4, 16), "high", closed=True)]),
    "MM": S(n=[("獨立紀念日", 1, 4, "low"), ("聯邦日", 2, 12, "low"), ("勞動節", 5, 1, "mid"),
               ("烈士日", 7, 19, "low"), ("聖誕節", 12, 25, "low")],
            x=lambda y: [
                H("潑水節與緬甸新年", D(y, 4, 13), D(y, 4, 17), "high", closed=True),
                H("衛塞節", LUNAR[y]["vesak"], travel="low")]),
    "BN": S("muslim", n=[("元旦", 1, 1, "mid"), ("國慶日", 2, 23, "mid"),
                         ("蘇丹誕辰", 7, 15, "low")],
            x=lambda y: [H("農曆新年", LUNAR[y]["cny"], travel="mid")]),

    # ------------------------------------------------------------------ 南亞
    "NP": S(n=[("民主日", 2, 19, "low"), ("勞動節", 5, 1, "mid"), ("憲法日", 9, 19, "low")],
            x=lambda y: [
                H("尼泊爾新年", D(y, 4, 14), travel="mid"),
                H("荷麗節", LUNAR[y]["holi"], travel="mid"),
                H("德賽節（Dashain）", LUNAR[y]["dashain"], days(LUNAR[y]["dashain"], 5),
                  "high", approx=True, closed=True, note="尼泊爾最長假期，全國商店歇業返鄉"),
                H("提哈節（Tihar）", LUNAR[y]["tihar"], days(LUNAR[y]["tihar"], 3),
                  "high", approx=True)]),
    "LK": S(n=[("獨立紀念日", 2, 4, "low"), ("勞動節", 5, 1, "mid"), ("聖誕節", 12, 25, "mid")],
            x=lambda y: [
                H("僧伽羅與坦米爾新年", D(y, 4, 13), D(y, 4, 14), "high", closed=True),
                H("衛塞節", LUNAR[y]["vesak"], days(LUNAR[y]["vesak"], 1), "mid"),
                H("開齋節", ISLAMIC[y]["fitr"], travel="low", approx=True),
                H("屠妖節", LUNAR[y]["deepavali"], travel="low")]),
    "MV": S("muslim", n=[("獨立紀念日", 7, 26, "low"), ("共和國日", 11, 11, "low")]),
    "BD": S(n=[("語言烈士日", 2, 21, "low"), ("獨立紀念日", 3, 26, "mid"),
               ("勞動節", 5, 1, "mid"), ("勝利日", 12, 16, "mid")],
            x=lambda y: [
                H("孟加拉新年", D(y, 4, 14), travel="mid"),
                H("開齋節", days(ISLAMIC[y]["fitr"], -1), days(ISLAMIC[y]["fitr"], 2), "high",
                  approx=True, closed=True),
                H("宰牲節", days(ISLAMIC[y]["adha"], -1), days(ISLAMIC[y]["adha"], 2), "high",
                  approx=True, closed=True)]),
    "PK": S("muslim", n=[("喀什米爾日", 2, 5, "low"), ("巴基斯坦日", 3, 23, "mid"),
                         ("勞動節", 5, 1, "mid"), ("獨立紀念日", 8, 14, "mid"),
                         ("真納誕辰", 12, 25, "low")]),

    # ------------------------------------------------------------ 中亞高加索
    "KZ": S(n=[("新年", 1, 1, "mid"), ("東正教聖誕節", 1, 7, "low"), ("婦女節", 3, 8, "low"),
               ("團結日", 5, 1, "mid"), ("祖國保衛者日", 5, 7, "low"), ("勝利日", 5, 9, "mid"),
               ("首都日", 7, 6, "low"), ("憲法日", 8, 30, "low"), ("共和國日", 10, 25, "mid"),
               ("獨立紀念日", 12, 16, "mid")],
            x=lambda y: [H("納吾肉孜節", D(y, 3, 21), D(y, 3, 23), "high",
                           note="中亞最大春節，全國放長假")]),
    "UZ": S(n=[("新年", 1, 1, "mid"), ("婦女節", 3, 8, "low"), ("紀念日", 5, 9, "low"),
               ("獨立紀念日", 9, 1, "mid"), ("憲法日", 12, 8, "low")],
            x=lambda y: [
                H("納吾肉孜節", D(y, 3, 21), travel="high"),
                H("開齋節", ISLAMIC[y]["fitr"], travel="mid", approx=True),
                H("宰牲節", ISLAMIC[y]["adha"], travel="mid", approx=True)]),
    "GE": S(n=[("新年", 1, 1, "mid"), ("東正教聖誕節", 1, 7, "mid"), ("主顯節", 1, 19, "low"),
               ("母親節", 3, 3, "low"), ("婦女節", 3, 8, "low"), ("獨立紀念日", 5, 26, "mid"),
               ("聖母升天日", 8, 28, "mid"), ("光明節", 10, 14, "low"), ("聖喬治日", 11, 23, "low")],
            x=lambda y: [H("東正教復活節連假", _oe(y, -2), _oe(y, 1), "high")]),
    "AM": S(n=[("新年", 1, 1, "mid"), ("聖誕節", 1, 6, "mid"), ("建軍節", 1, 28, "low"),
               ("婦女節", 3, 8, "low"), ("種族滅絕紀念日", 4, 24, "low"), ("勞動節", 5, 1, "mid"),
               ("勝利日", 5, 9, "mid"), ("共和國日", 5, 28, "mid"), ("憲法日", 7, 5, "low"),
               ("獨立紀念日", 9, 21, "mid")]),
    "AZ": S(n=[("新年", 1, 1, "mid"), ("婦女節", 3, 8, "low"), ("勝利日", 5, 9, "low"),
               ("共和國日", 5, 28, "mid"), ("救國日", 6, 15, "low"), ("獨立紀念日", 10, 18, "mid")],
            x=lambda y: [
                H("諾魯茲", D(y, 3, 20), D(y, 3, 24), "high"),
                H("開齋節", ISLAMIC[y]["fitr"], days(ISLAMIC[y]["fitr"], 1), "mid", approx=True),
                H("宰牲節", ISLAMIC[y]["adha"], days(ISLAMIC[y]["adha"], 1), "mid", approx=True)]),

    # ------------------------------------------------------------------ 中東
    "QA": S("muslim", n=[("國慶日", 12, 18, "mid"), ("體育日", 2, 10, "low")]),
    "KW": S("muslim", n=[("新年", 1, 1, "mid"), ("國慶日", 2, 25, "mid"), ("解放日", 2, 26, "mid")]),
    "BH": S("muslim", n=[("新年", 1, 1, "mid"), ("勞動節", 5, 1, "mid"),
                         ("國慶日", 12, 16, "mid"), ("登基紀念日", 12, 17, "mid")]),
    "OM": S("muslim", n=[("國慶日", 11, 18, "mid"), ("國慶翌日", 11, 19, "mid"),
                         ("蘇丹登基日", 1, 11, "low")]),
    "JO": S("muslim", n=[("新年", 1, 1, "mid"), ("勞動節", 5, 1, "mid"),
                         ("獨立紀念日", 5, 25, "mid"), ("聖誕節", 12, 25, "low")]),
    "LB": S("muslim", n=[("新年", 1, 1, "mid"), ("聖馬龍日", 2, 9, "low"), ("勞動節", 5, 1, "mid"),
                         ("烈士日", 5, 6, "low"), ("獨立紀念日", 11, 22, "mid"),
                         ("聖誕節", 12, 25, "mid")],
            x=lambda y: [H("復活節連假", _e(y, -2), _e(y, 1), "mid"),
                         H("東正教復活節", _oe(y, -2), _oe(y, 1), "mid")]),
    "IR": S("persian", n=[("伊斯蘭革命勝利日", 2, 11, "low"), ("石油國有化日", 3, 19, "low"),
                          ("伊斯蘭共和日", 4, 1, "mid")],
            x=lambda y: [
                H("諾魯茲假期", PERSIAN[y], days(PERSIAN[y], 12), "high", kind="season",
                  note="伊朗新年連假可長達兩週，國內交通與旅館全滿"),
                H("開齋節", ISLAMIC[y]["fitr"], days(ISLAMIC[y]["fitr"], 1), "mid",
                  approx=True, closed=True),
                H("宰牲節", ISLAMIC[y]["adha"], travel="mid", approx=True, closed=True)]),
    "IQ": S("muslim", n=[("新年", 1, 1, "mid"), ("建軍節", 1, 6, "low"),
                         ("勞動節", 5, 1, "mid"), ("共和日", 7, 14, "mid")],
            x=lambda y: [H("諾魯茲（Newroz）", D(y, 3, 21), travel="mid")]),
}


SIMPLE.update({
    # ------------------------------------------------------------------ 歐洲
    "IE": S(n=[("元旦", 1, 1, "mid"), ("聖派翠克節", 3, 17, "high")],
            x=lambda y: [
                H("復活節星期一", _e(y, 1), travel="high"),
                H("五月銀行假日", nth_weekday(y, 5, 0, 1), travel="mid"),
                H("六月銀行假日", nth_weekday(y, 6, 0, 1), travel="mid"),
                H("八月銀行假日", nth_weekday(y, 8, 0, 1), travel="high"),
                H("十月銀行假日", nth_weekday(y, 10, 0, -1), travel="mid"),
                H("聖誕節與聖史蒂芬日", D(y, 12, 25), D(y, 12, 26), "high")]),
    "BE": S("west_cath_nogf", n=[("國慶日", 7, 21, "mid"), ("停戰紀念日", 11, 11, "low")],
            x=lambda y: [H("耶穌升天節", _e(y, 39), travel="high"),
                         H("聖靈降臨節", _e(y, 50), travel="mid")]),
    "LU": S("west_cath_nogf", n=[("國慶日", 6, 23, "mid")],
            x=lambda y: [H("耶穌升天節", _e(y, 39), travel="high"),
                         H("聖靈降臨節", _e(y, 50), travel="mid")]),
    "PT": S(n=[("元旦", 1, 1, "mid"), ("自由日", 4, 25, "mid"), ("勞動節", 5, 1, "mid"),
               ("葡萄牙日", 6, 10, "mid"), ("聖母升天日", 8, 15, "mid"),
               ("共和國日", 10, 5, "mid"), ("諸聖節", 11, 1, "mid"),
               ("復辟紀念日", 12, 1, "mid"), ("聖母無染原罪日", 12, 8, "mid"),
               ("聖誕節", 12, 25, "high")],
            x=lambda y: [H("復活節連假", _e(y, -2), _e(y, 0), "high"),
                         H("聖體聖血節", _e(y, 60), travel="mid")]),
    "GR": S(n=[("元旦", 1, 1, "mid"), ("主顯節", 1, 6, "mid"), ("獨立紀念日", 3, 25, "mid"),
               ("勞動節", 5, 1, "mid"), ("聖母升天日", 8, 15, "high"),
               ("說不日", 10, 28, "mid"), ("聖誕節", 12, 25, "high")],
            x=lambda y: [
                H("潔淨星期一", _oe(y, -48), travel="mid"),
                H("東正教復活節連假", _oe(y, -2), _oe(y, 1), "high",
                  note="希臘最大節慶，全國返鄉、離島船票一位難求"),
                H("聖靈降臨節", _oe(y, 50), travel="mid"),
                H("節禮日", D(y, 12, 26), travel="high")]),
    "MT": S("west_cath", n=[("聖保羅船難日", 2, 10, "low"), ("聖約瑟夫日", 3, 19, "low"),
                            ("自由日", 3, 31, "low"), ("六月七日事件紀念日", 6, 7, "low"),
                            ("勝利日", 9, 8, "mid"), ("獨立紀念日", 9, 21, "mid"),
                            ("聖母無染原罪日", 12, 8, "mid"), ("共和國日", 12, 13, "mid")]),
    "CY": S(n=[("元旦", 1, 1, "mid"), ("主顯節", 1, 6, "mid"), ("希臘獨立日", 3, 25, "mid"),
               ("賽普勒斯國家日", 4, 1, "mid"), ("勞動節", 5, 1, "mid"),
               ("聖母升天日", 8, 15, "mid"), ("獨立紀念日", 10, 1, "mid"),
               ("說不日", 10, 28, "mid"), ("平安夜", 12, 24, "mid"),
               ("聖誕節", 12, 25, "high")],
            x=lambda y: [H("綠色星期一", _oe(y, -48), travel="mid"),
                         H("東正教復活節連假", _oe(y, -2), _oe(y, 1), "high"),
                         H("聖靈降臨節", _oe(y, 50), travel="mid"),
                         H("節禮日", D(y, 12, 26), travel="high")]),
    "IS": S(n=[("元旦", 1, 1, "mid"), ("勞動節", 5, 1, "mid"), ("國慶日", 6, 17, "mid"),
               ("平安夜與聖誕節", 12, 24, "high"), ("除夕", 12, 31, "mid")],
            x=lambda y: [
                H("復活節連假", _e(y, -3), _e(y, 1), "high"),
                H("夏季第一天", next_weekday_after(D(y, 4, 18), 3), travel="mid"),
                H("耶穌升天節", _e(y, 39), travel="mid"),
                H("聖靈降臨節", _e(y, 50), travel="mid"),
                H("商人假日", nth_weekday(y, 8, 0, 1), travel="high",
                  note="冰島國內最大的旅遊長週末"),
                H("聖誕節與節禮日", D(y, 12, 25), D(y, 12, 26), "high")]),
    "EE": S(n=[("元旦", 1, 1, "mid"), ("獨立紀念日", 2, 24, "mid"), ("春天節", 5, 1, "mid"),
               ("勝利日", 6, 23, "high"), ("仲夏節", 6, 24, "high"),
               ("恢復獨立日", 8, 20, "mid"), ("聖誕節", 12, 24, "high")],
            x=lambda y: [H("復活節連假", _e(y, -2), _e(y, 1), "high"),
                         H("聖靈降臨節", _e(y, 49), travel="mid"),
                         H("聖誕假期", D(y, 12, 25), D(y, 12, 26), "high")]),
    "LV": S(n=[("元旦", 1, 1, "mid"), ("勞動節", 5, 1, "mid"), ("獨立宣言日", 5, 4, "mid"),
               ("仲夏前夕", 6, 23, "high"), ("仲夏節", 6, 24, "high"),
               ("獨立紀念日", 11, 18, "mid"), ("聖誕節", 12, 24, "high")],
            x=lambda y: [H("復活節連假", _e(y, -2), _e(y, 1), "high"),
                         H("聖誕假期", D(y, 12, 25), D(y, 12, 26), "high")]),
    "LT": S(n=[("元旦", 1, 1, "mid"), ("國家重建日", 2, 16, "mid"), ("恢復獨立日", 3, 11, "mid"),
               ("勞動節", 5, 1, "mid"), ("仲夏節", 6, 24, "high"), ("國王加冕日", 7, 6, "mid"),
               ("聖母升天日", 8, 15, "mid"), ("諸聖節", 11, 1, "mid"),
               ("平安夜", 12, 24, "high")],
            x=lambda y: [H("復活節連假", _e(y, 0), _e(y, 1), "high"),
                         H("聖誕假期", D(y, 12, 25), D(y, 12, 26), "high")]),
    "CZ": S(n=[("元旦", 1, 1, "mid"), ("勞動節", 5, 1, "mid"), ("解放日", 5, 8, "mid"),
               ("西里爾與美多德日", 7, 5, "mid"), ("胡斯日", 7, 6, "mid"),
               ("建國日", 9, 28, "mid"), ("獨立紀念日", 10, 28, "mid"),
               ("自由民主鬥爭日", 11, 17, "mid"), ("聖誕假期", 12, 24, "high")],
            x=lambda y: [H("復活節連假", _e(y, -2), _e(y, 1), "high"),
                         H("聖誕節與節禮日", D(y, 12, 25), D(y, 12, 26), "high")]),
    "SK": S(n=[("元旦", 1, 1, "mid"), ("主顯節", 1, 6, "mid"), ("勞動節", 5, 1, "mid"),
               ("解放日", 5, 8, "mid"), ("西里爾與美多德日", 7, 5, "mid"),
               ("民族起義日", 8, 29, "mid"), ("憲法日", 9, 1, "mid"),
               ("七苦聖母日", 9, 15, "mid"), ("諸聖節", 11, 1, "mid"),
               ("自由鬥爭日", 11, 17, "mid"), ("聖誕假期", 12, 24, "high")],
            x=lambda y: [H("復活節連假", _e(y, -2), _e(y, 1), "high"),
                         H("聖誕節與節禮日", D(y, 12, 25), D(y, 12, 26), "high")]),
    "HU": S(n=[("元旦", 1, 1, "mid"), ("革命紀念日", 3, 15, "mid"), ("勞動節", 5, 1, "mid"),
               ("國慶日", 8, 20, "high"), ("共和國日", 10, 23, "mid"),
               ("諸聖節", 11, 1, "mid"), ("聖誕節", 12, 25, "high")],
            x=lambda y: [H("復活節連假", _e(y, -2), _e(y, 1), "high"),
                         H("聖靈降臨節", _e(y, 50), travel="mid"),
                         H("節禮日", D(y, 12, 26), travel="high")]),
    "SI": S(n=[("元旦", 1, 1, "mid"), ("文化節", 2, 8, "mid"), ("起義日", 4, 27, "mid"),
               ("勞動節", 5, 1, "high"), ("國慶日", 6, 25, "mid"),
               ("聖母升天日", 8, 15, "mid"), ("宗教改革日", 10, 31, "mid"),
               ("諸聖節", 11, 1, "mid"), ("聖誕節", 12, 25, "high"),
               ("獨立與統一日", 12, 26, "high")],
            x=lambda y: [H("復活節星期一", _e(y, 1), travel="high"),
                         H("勞動節連假", D(y, 5, 2), travel="high")]),
    "HR": S(n=[("元旦", 1, 1, "mid"), ("主顯節", 1, 6, "mid"), ("勞動節", 5, 1, "mid"),
               ("國慶日", 5, 30, "mid"), ("反法西斯鬥爭日", 6, 22, "mid"),
               ("勝利日", 8, 5, "mid"), ("聖母升天日", 8, 15, "high"),
               ("諸聖節", 11, 1, "mid"), ("追思紀念日", 11, 18, "low"),
               ("聖誕節", 12, 25, "high"), ("聖史蒂芬日", 12, 26, "high")],
            x=lambda y: [H("復活節星期一", _e(y, 1), travel="high"),
                         H("聖體聖血節", _e(y, 60), travel="mid")]),
    "BA": S(n=[("新年", 1, 1, "mid"), ("勞動節", 5, 1, "mid"), ("國慶日", 11, 25, "mid")],
            x=lambda y: [H("東正教聖誕節", D(y, 1, 7), travel="mid"),
                         H("東正教復活節", _oe(y, -2), _oe(y, 1), "mid"),
                         H("開齋節", ISLAMIC[y]["fitr"], travel="mid", approx=True),
                         H("天主教聖誕節", D(y, 12, 25), travel="mid")]),
    "RS": S(n=[("新年", 1, 1, "mid"), ("東正教聖誕節", 1, 7, "mid"),
               ("國慶日", 2, 15, "mid"), ("勞動節", 5, 1, "mid"),
               ("停戰紀念日", 11, 11, "low")],
            x=lambda y: [H("東正教復活節連假", _oe(y, -2), _oe(y, 1), "high")]),
    "ME": S(n=[("新年", 1, 1, "mid"), ("東正教聖誕節", 1, 7, "mid"), ("勞動節", 5, 1, "mid"),
               ("獨立紀念日", 5, 21, "mid"), ("國家日", 7, 13, "mid")],
            x=lambda y: [H("東正教復活節連假", _oe(y, -2), _oe(y, 1), "high")]),
    "MK": S("orthodox", n=[("聖西里爾與美多德日", 5, 24, "low"), ("共和國日", 8, 2, "mid"),
                           ("獨立紀念日", 9, 8, "mid"), ("起義日", 10, 11, "low")]),
    "AL": S(n=[("新年", 1, 1, "mid"), ("夏日節", 3, 14, "mid"), ("勞動節", 5, 1, "mid"),
               ("德蕾莎修女日", 9, 5, "low"), ("獨立紀念日", 11, 28, "mid"),
               ("解放日", 11, 29, "mid"), ("聖誕節", 12, 25, "mid")],
            x=lambda y: [H("蘇丹諾魯茲節", D(y, 3, 22), travel="mid"),
                         H("復活節", _e(y, 0), travel="mid"),
                         H("東正教復活節", _oe(y, 0), travel="mid"),
                         H("開齋節", ISLAMIC[y]["fitr"], travel="mid", approx=True),
                         H("宰牲節", ISLAMIC[y]["adha"], travel="low", approx=True)]),
    "RO": S(n=[("新年", 1, 1, "mid"), ("聯合日", 1, 24, "mid"), ("勞動節", 5, 1, "mid"),
               ("兒童節", 6, 1, "low"), ("聖母升天日", 8, 15, "mid"),
               ("聖安德魯日", 11, 30, "mid"), ("國慶日", 12, 1, "mid"),
               ("聖誕節", 12, 25, "high")],
            x=lambda y: [H("東正教復活節連假", _oe(y, -2), _oe(y, 1), "high"),
                         H("聖靈降臨節", _oe(y, 49), _oe(y, 50), "mid"),
                         H("節禮日", D(y, 12, 26), travel="high")]),
    "BG": S(n=[("新年", 1, 1, "mid"), ("解放紀念日", 3, 3, "mid"), ("勞動節", 5, 1, "mid"),
               ("聖喬治日與建軍節", 5, 6, "mid"), ("文化與文字日", 5, 24, "mid"),
               ("統一日", 9, 6, "mid"), ("獨立紀念日", 9, 22, "mid"),
               ("平安夜與聖誕節", 12, 24, "high")],
            x=lambda y: [H("東正教復活節連假", _oe(y, -2), _oe(y, 1), "high"),
                         H("聖誕假期", D(y, 12, 25), D(y, 12, 26), "high")]),
    "UA": S(n=[("新年", 1, 1, "mid"), ("聖誕節", 12, 25, "high"), ("婦女節", 3, 8, "low"),
               ("勞動節", 5, 1, "mid"), ("憲法日", 6, 28, "mid"),
               ("獨立紀念日", 8, 24, "mid"), ("保衛者日", 10, 1, "mid")],
            x=lambda y: [H("復活節連假", _oe(y, 0), _oe(y, 1), "high"),
                         H("聖三一節", _oe(y, 49), travel="mid")]),
    "BY": S(n=[("新年", 1, 1, "mid"), ("東正教聖誕節", 1, 7, "mid"), ("婦女節", 3, 8, "low"),
               ("勞動節", 5, 1, "mid"), ("勝利日", 5, 9, "mid"),
               ("獨立紀念日", 7, 3, "mid"), ("十月革命日", 11, 7, "low"),
               ("天主教聖誕節", 12, 25, "mid")],
            x=lambda y: [H("東正教復活節", _oe(y, 0), travel="mid"),
                         H("拉東尼察", _oe(y, 9), travel="low")]),
    "MD": S("orthodox", n=[("新年", 1, 1, "mid"), ("婦女節", 3, 8, "low"),
                           ("勝利日", 5, 9, "mid"), ("共和國日", 8, 27, "mid"),
                           ("語言日", 8, 31, "low"), ("聖誕節", 12, 25, "mid")]),
})


SIMPLE.update({
    # ---------------------------------------------------------------- 中南美
    "GT": S("latin", n=[("軍隊日", 6, 30, "low"), ("獨立紀念日", 9, 15, "mid"),
                        ("革命日", 10, 20, "low"), ("諸聖節", 11, 1, "mid")]),
    "CR": S("latin", n=[("瓜納卡斯特日", 7, 25, "low"), ("聖母日", 8, 2, "low"),
                        ("母親節", 8, 15, "mid"), ("獨立紀念日", 9, 15, "mid"),
                        ("廢除軍隊日", 12, 1, "low")]),
    "PA": S("latin", n=[("烈士日", 1, 9, "low"), ("獨立紀念日", 11, 3, "mid"),
                        ("科隆日", 11, 5, "low"), ("起義日", 11, 10, "low"),
                        ("脫離西班牙獨立日", 11, 28, "mid")],
            x=lambda y: [H("嘉年華", _e(y, -48), _e(y, -47), "high")]),
    "CU": S(n=[("解放日", 1, 1, "mid"), ("勝利日", 1, 2, "mid"), ("勞動節", 5, 1, "mid"),
               ("革命紀念日", 7, 25, "high"), ("獨立戰爭紀念日", 10, 10, "mid"),
               ("聖誕節", 12, 25, "mid"), ("除夕", 12, 31, "mid")],
            x=lambda y: [H("耶穌受難日", _e(y, -2), travel="mid")]),
    "DO": S("latin", n=[("杜阿爾特日", 1, 26, "low"), ("獨立紀念日", 2, 27, "mid"),
                        ("復辟紀念日", 8, 16, "mid"), ("聖母日", 9, 24, "low"),
                        ("憲法日", 11, 6, "low")]),
    "JM": S("anglo", n=[("解放日", 8, 1, "mid"), ("獨立紀念日", 8, 6, "mid")],
            x=lambda y: [H("聖灰星期三", _e(y, -46), travel="low"),
                         H("國家英雄日", nth_weekday(y, 10, 0, 3), travel="mid")]),
    "CO": S("latin", n=[("主顯節", 1, 6, "mid"), ("獨立紀念日", 7, 20, "mid"),
                        ("博亞卡戰役日", 8, 7, "mid"), ("諸聖節", 11, 1, "mid"),
                        ("卡塔赫納獨立日", 11, 11, "mid"), ("聖母無染原罪日", 12, 8, "mid")]),
    "VE": S("latin", n=[("獨立宣言日", 4, 19, "mid"), ("獨立紀念日", 7, 5, "mid"),
                        ("玻利瓦誕辰", 7, 24, "mid"), ("原住民抵抗日", 10, 12, "low")],
            x=lambda y: [H("嘉年華", _e(y, -48), _e(y, -47), "high")]),
    "EC": S("latin", n=[("獨立紀念日", 8, 10, "mid"), ("瓜亞基爾獨立日", 10, 9, "mid"),
                        ("亡靈節", 11, 2, "mid"), ("基多建城日", 12, 6, "low")],
            x=lambda y: [H("嘉年華", _e(y, -48), _e(y, -47), "high")]),
    "PE": S("latin", n=[("聖彼得與聖保羅日", 6, 29, "mid"), ("胡寧戰役紀念日", 8, 6, "mid"),
                        ("獨立紀念日", 7, 28, "high"),
                        ("國家日", 7, 29, "high"), ("聖羅莎日", 8, 30, "mid"),
                        ("安加莫斯戰役日", 10, 8, "low"), ("諸聖節", 11, 1, "mid"),
                        ("聖母無染原罪日", 12, 8, "mid")]),
    "BO": S("latin", n=[("多民族國日", 1, 22, "low"), ("獨立紀念日", 8, 6, "mid"),
                        ("亡靈節", 11, 2, "mid")],
            x=lambda y: [H("嘉年華", _e(y, -48), _e(y, -47), "high")]),
    "CL": S("latin", n=[("海軍日", 5, 21, "mid"), ("聖彼得與聖保羅日", 6, 29, "low"),
                        ("卡門聖母日", 7, 16, "mid"), ("聖母升天日", 8, 15, "mid"),
                        ("獨立紀念日", 9, 18, "high"), ("光榮軍隊日", 9, 19, "high"),
                        ("哥倫布日", 10, 12, "mid"), ("諸聖節", 11, 1, "mid"),
                        ("聖母無染原罪日", 12, 8, "mid")]),
    "UY": S(n=[("元旦", 1, 1, "mid"), ("勞動節", 5, 1, "mid"), ("憲法日", 7, 18, "mid"),
               ("獨立紀念日", 8, 25, "mid"), ("哥倫布日", 10, 12, "low"),
               ("聖誕節", 12, 25, "high")],
            x=lambda y: [H("嘉年華", _e(y, -48), _e(y, -47), "high"),
                         H("旅遊週（聖週）", _e(y, -6), _e(y, 0), "high",
                           note="烏拉圭全國度假週")]),
    "PY": S("latin", n=[("英雄日", 3, 1, "low"), ("獨立紀念日", 5, 14, "mid"),
                        ("國家日", 5, 15, "mid"), ("查科停戰日", 6, 12, "low"),
                        ("聖母日", 12, 8, "mid")]),

    # ------------------------------------------------------------------ 非洲
    "MA": S("muslim", n=[("獨立宣言日", 1, 11, "low"), ("勞動節", 5, 1, "mid"),
                         ("王座日", 7, 30, "mid"), ("烏埃德日", 8, 14, "low"),
                         ("國王與人民革命日", 8, 20, "mid"), ("青年節", 8, 21, "low"),
                         ("綠色進軍日", 11, 6, "mid"), ("獨立紀念日", 11, 18, "mid")],
            x=lambda y: [H("元旦", D(y, 1, 1), travel="mid")]),
    "TN": S("muslim", n=[("元旦", 1, 1, "mid"), ("革命日", 1, 14, "low"),
                         ("獨立紀念日", 3, 20, "mid"), ("烈士日", 4, 9, "low"),
                         ("勞動節", 5, 1, "mid"), ("共和日", 7, 25, "mid"),
                         ("婦女節", 8, 13, "low"), ("變革日", 10, 15, "low")]),
    "DZ": S("muslim", n=[("元旦", 1, 1, "mid"), ("亞馬齊新年", 1, 12, "low"),
                         ("勞動節", 5, 1, "mid"), ("學生日", 5, 19, "low"),
                         ("獨立紀念日", 7, 5, "mid"), ("革命紀念日", 11, 1, "mid")]),
    "KE": S(n=[("元旦", 1, 1, "mid"), ("勞動節", 5, 1, "mid"), ("馬達拉卡日", 6, 1, "mid"),
               ("胡德日", 10, 10, "low"), ("馬沙卡日", 10, 20, "mid"),
               ("賈姆胡里日", 12, 12, "mid"), ("聖誕節", 12, 25, "high"),
               ("節禮日", 12, 26, "high")],
            x=lambda y: [H("復活節連假", _e(y, -2), _e(y, 1), "high"),
                         H("開齋節", ISLAMIC[y]["fitr"], travel="low", approx=True)]),
    "TZ": S(n=[("元旦", 1, 1, "mid"), ("桑吉巴革命日", 1, 12, "low"),
               ("卡魯梅日", 4, 7, "low"), ("聯合日", 4, 26, "mid"), ("勞動節", 5, 1, "mid"),
               ("農民日", 8, 8, "low"), ("尼雷爾日", 10, 14, "low"),
               ("獨立紀念日", 12, 9, "mid"), ("聖誕節", 12, 25, "high"),
               ("節禮日", 12, 26, "high")],
            x=lambda y: [H("復活節連假", _e(y, -2), _e(y, 1), "high"),
                         H("開齋節", ISLAMIC[y]["fitr"], days(ISLAMIC[y]["fitr"], 1), "mid",
                           approx=True),
                         H("宰牲節", ISLAMIC[y]["adha"], travel="low", approx=True)]),
    "ET": S(n=[("聖誕節", 1, 7, "mid"), ("主顯節", 1, 19, "mid"), ("建軍節", 3, 2, "low"),
               ("勞動節", 5, 1, "mid"), ("愛國者日", 5, 5, "low"),
               ("政權垮台日", 5, 28, "low"), ("新年", 9, 11, "high"),
               ("十字架節", 9, 27, "mid")],
            x=lambda y: [H("東正教復活節", _oe(y, -2), _oe(y, 0), "high"),
                         H("開齋節", ISLAMIC[y]["fitr"], travel="mid", approx=True),
                         H("宰牲節", ISLAMIC[y]["adha"], travel="low", approx=True)]),
    "NG": S(n=[("元旦", 1, 1, "mid"), ("勞動節", 5, 1, "mid"), ("民主日", 6, 12, "mid"),
               ("獨立紀念日", 10, 1, "mid"), ("聖誕節", 12, 25, "high"),
               ("節禮日", 12, 26, "high")],
            x=lambda y: [H("復活節連假", _e(y, -2), _e(y, 1), "high"),
                         H("開齋節", ISLAMIC[y]["fitr"], days(ISLAMIC[y]["fitr"], 1), "high",
                           approx=True, closed=True),
                         H("宰牲節", ISLAMIC[y]["adha"], days(ISLAMIC[y]["adha"], 1), "mid",
                           approx=True)]),
    "GH": S(n=[("元旦", 1, 1, "mid"), ("憲法日", 1, 7, "low"), ("獨立紀念日", 3, 6, "mid"),
               ("勞動節", 5, 1, "mid"), ("建國者日", 8, 4, "low"),
               ("聖誕節", 12, 25, "high"), ("節禮日", 12, 26, "high")],
            x=lambda y: [H("復活節連假", _e(y, -2), _e(y, 1), "high"),
                         H("農民日", nth_weekday(y, 12, 4, 1), travel="low")]),
    "SN": S("muslim", n=[("元旦", 1, 1, "mid"), ("獨立紀念日", 4, 4, "mid"),
                         ("勞動節", 5, 1, "mid"), ("聖母升天日", 8, 15, "low"),
                         ("諸聖節", 11, 1, "low"), ("聖誕節", 12, 25, "mid")],
            x=lambda y: [H("復活節星期一", _e(y, 1), travel="mid"),
                         H("耶穌升天節", _e(y, 39), travel="low")]),
    "MU": S(n=[("元旦", 1, 1, "mid"), ("廢奴紀念日", 2, 1, "low"),
               ("獨立與共和日", 3, 12, "mid"), ("勞動節", 5, 1, "mid"),
               ("聖母升天日", 8, 15, "low"), ("聖誕節", 12, 25, "high")],
            x=lambda y: [H("農曆新年", LUNAR[y]["cny"], travel="mid"),
                         H("屠妖節", LUNAR[y]["deepavali"], travel="mid"),
                         H("開齋節", ISLAMIC[y]["fitr"], travel="mid", approx=True)]),
    "SC": S(n=[("元旦", 1, 1, "mid"), ("勞動節", 5, 1, "mid"), ("憲法日", 6, 18, "low"),
               ("國慶日", 6, 29, "mid"), ("聖母升天日", 8, 15, "low"),
               ("諸聖節", 11, 1, "low"), ("聖誕節", 12, 25, "high")],
            x=lambda y: [H("復活節連假", _e(y, -2), _e(y, 1), "high"),
                         H("聖體聖血節", _e(y, 60), travel="low")]),
    "ZW": S(n=[("元旦", 1, 1, "mid"), ("青年日", 2, 21, "low"), ("獨立紀念日", 4, 18, "mid"),
               ("勞動節", 5, 1, "mid"), ("非洲日", 5, 25, "low"),
               ("團結日", 12, 22, "low"), ("聖誕節", 12, 25, "high"),
               ("節禮日", 12, 26, "high")],
            x=lambda y: [H("復活節連假", _e(y, -2), _e(y, 1), "high"),
                         H("英雄日與國防軍日", nth_weekday(y, 8, 0, 2),
                           days(nth_weekday(y, 8, 0, 2), 1), "mid")]),
    "UG": S(n=[("元旦", 1, 1, "mid"), ("解放日", 1, 26, "low"), ("婦女節", 3, 8, "low"),
               ("勞動節", 5, 1, "mid"), ("烈士日", 6, 3, "low"), ("英雄日", 6, 9, "low"),
               ("獨立紀念日", 10, 9, "mid"), ("聖誕節", 12, 25, "high"),
               ("節禮日", 12, 26, "high")],
            x=lambda y: [H("復活節連假", _e(y, -2), _e(y, 1), "high"),
                         H("開齋節", ISLAMIC[y]["fitr"], travel="low", approx=True)]),
    "NA": S(n=[("元旦", 1, 1, "mid"), ("獨立紀念日", 3, 21, "mid"), ("卡辛加日", 5, 4, "low"),
               ("非洲日", 5, 25, "low"), ("種族滅絕紀念日", 5, 28, "low"),
               ("英雄日", 8, 26, "mid"), ("人權日", 12, 10, "low"),
               ("聖誕節", 12, 25, "high"), ("家庭日", 12, 26, "high")],
            x=lambda y: [H("復活節連假", _e(y, -2), _e(y, 1), "high"),
                         H("耶穌升天節", _e(y, 39), travel="low")]),
    "BW": S(n=[("元旦", 1, 1, "mid"), ("勞動節", 5, 1, "mid"),
               ("波札那日", 9, 30, "mid"), ("聖誕節", 12, 25, "high"),
               ("節禮日", 12, 26, "high")],
            x=lambda y: [H("復活節連假", _e(y, -2), _e(y, 1), "high"),
                         H("耶穌升天節", _e(y, 39), travel="low"),
                         H("總統日", nth_weekday(y, 7, 0, 3),
                           days(nth_weekday(y, 7, 0, 3), 1), "mid")]),

    # ---------------------------------------------------------------- 大洋洲
    "FJ": S(n=[("元旦", 1, 1, "mid"), ("憲法日", 9, 7, "low"), ("斐濟日", 10, 10, "mid"),
               ("聖誕節", 12, 25, "high"), ("節禮日", 12, 26, "high")],
            x=lambda y: [H("復活節連假", _e(y, -2), _e(y, 1), "high"),
                         H("屠妖節", LUNAR[y]["deepavali"], travel="mid"),
                         H("先知誕辰", ISLAMIC[y]["mawlid"], travel="low", approx=True)]),
    "PG": S(n=[("元旦", 1, 1, "mid"), ("憶念日", 7, 23, "low"), ("獨立紀念日", 9, 16, "mid"),
               ("聖誕節", 12, 25, "high"), ("節禮日", 12, 26, "high")],
            x=lambda y: [H("復活節連假", _e(y, -3), _e(y, 1), "high"),
                         H("國王誕辰", nth_weekday(y, 6, 0, 2), travel="low")]),
    "PW": S(n=[("元旦", 1, 1, "mid"), ("青年日", 3, 15, "low"), ("敬老日", 5, 5, "low"),
               ("憲法日", 7, 9, "mid"), ("獨立紀念日", 10, 1, "mid"),
               ("聖誕節", 12, 25, "high")],
            x=lambda y: [H("勞動節", nth_weekday(y, 9, 0, 1), travel="mid"),
                         H("感恩節", nth_weekday(y, 11, 3, 4), travel="mid")]),
})


# ------------------------------------- 假期結構特殊、單獨描述的國家
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
        H("春節", days(L["nye"], -2), days(L["cny"], 5), "high", approx=True, closed=True,
          note="全球最大規模的人口移動；中國境內大量商店、餐廳歇業數日"),
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
        H("黃金週", D(y, 4, 29), days(gw_end, -1), "high", kind="season", closed=False,
          note="日本全國最大連假，國內外機票住宿全面漲價；商店照常營業但到處大排長龍"),
        H("盂蘭盆節（お盆）", D(y, 8, 13), D(y, 8, 16), "high", kind="season",
          note="非法定假日，但企業普遍放假、返鄉與出國高峰"),
        H("年末年始", D(y, 12, 29), D(y, 12, 31), "high", kind="season", closed=True,
          note="日本少數會大規模歇業的期間，餐廳與小店多休到 1/3 前後"),
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
        H("春節（설날）", days(L["seollal"], -1), days(L["seollal"], 1), "high", closed=True,
          note="韓國最大連假，出國旅遊需求暴增；當地餐廳與小店多休息"),
        H("中秋節（추석）", days(L["chuseok"], -1), days(L["chuseok"], 1), "high", closed=True,
          note="韓國第二大連假；當地餐廳與小店多休息"),
    ]
    return out


@country("TW")
def tw(y):
    L = LUNAR[y]
    # 台灣的補假若撞到另一個假日要再往後順延（2027 的兒童節就是這個情形），
    # 所以先把「本來就在平日」的假日佔位，再安排需要補假的。
    fixed = {
        "開國紀念日": D(y, 1, 1), "和平紀念日": D(y, 2, 28), "兒童節": D(y, 4, 4),
        "清明節": L["qingming"], "勞動節": D(y, 5, 1), "端午節": L["dragon"],
        "中秋節": L["midautumn"], "教師節": D(y, 9, 28), "國慶日": D(y, 10, 10),
        "台灣光復節": D(y, 10, 25), "行憲紀念日": D(y, 12, 25),
    }
    used = set(x for x in fixed.values() if x.weekday() < 5)

    def o(x):
        if x.weekday() < 5:
            return x
        placed = observe(x, "tw")
        while placed in used or placed.weekday() >= 5:
            placed = days(placed, 1)
        used.add(placed)
        return placed

    # 春節：除夕前一日至初三，逢週末往後補假
    start, end = days(L["nye"], -1), days(L["cny"], 2)
    weekend_in = sum(1 for i in range((end - start).days + 1)
                     if (start + dt.timedelta(days=i)).weekday() >= 5)
    cur = end
    for _ in range(weekend_in):
        cur = days(cur, 1)
        while cur.weekday() >= 5:
            cur = days(cur, 1)
    out = [H("農曆春節", start, cur, "high", closed=True,
             note="台灣最長連假；初一到初三不少餐廳與小店休息")]
    # 清明節要排在兒童節之前，兒童節的補假才會正確順延（2027 就是這個情形）
    for name in ["開國紀念日", "和平紀念日", "清明節", "兒童節", "勞動節", "端午節",
                 "中秋節", "教師節", "國慶日", "台灣光復節", "行憲紀念日"]:
        out.append(H(name, o(fixed[name]), travel="mid"))

    # 次年元旦逢週六時，補假會落在今年年底（例如 2027/12/31）
    if D(y + 1, 1, 1).weekday() == 5:
        out.append(H("開國紀念日（補假）", D(y, 12, 31), travel="mid"))
    return out


@country("HK")
def hk(y):
    L, e = LUNAR[y], easter(y)
    # 香港的補假若撞到另一個公眾假期要再往後順延。2026 年清明逢週日、
    # 補假又碰上復活節星期一，官方因此加放 4/7。
    taken = set()
    for i in range(3):
        taken.add(days(L["cny"], i))
    for i in range(-2, 2):
        taken.add(days(e, i))
    for fx in (D(y, 1, 1), D(y, 5, 1), L["dragon"], D(y, 7, 1),
               days(L["midautumn"], 1), D(y, 10, 1), D(y, 12, 25), D(y, 12, 26)):
        if fx.weekday() != 6:
            taken.add(fx)

    def o(x):
        if x.weekday() != 6:      # 香港只有逢週日才補假
            return x
        placed = days(x, 1)
        while placed in taken or placed.weekday() == 6:
            placed = days(placed, 1)
        taken.add(placed)
        return placed

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


# 冬至（澳門的法定假期，日期為當年冬至）
MO_DONGZHI = {2026: d("2026-12-21"), 2027: d("2027-12-22")}


@country("MO")
def mo(y):
    L, e = LUNAR[y], easter(y)
    o = lambda x: observe(x, "sun_to_mon")
    return [
        H("元旦", o(D(y, 1, 1)), travel="mid"),
        H("農曆新年", days(L["nye"], -1), days(L["cny"], 2), "high",
          note="除夕下午起放假，賭場與商圈人潮最多"),
        H("耶穌受難日與復活節", days(e, -2), days(e, -1), "mid"),
        H("清明節", o(L["qingming"]), travel="low"),
        H("勞動節", o(D(y, 5, 1)), travel="mid"),
        H("佛誕", o(L["buddha"]), travel="low"),
        H("端午節", o(L["dragon"]), travel="low"),
        H("中秋節翌日", o(days(L["midautumn"], 1)), travel="mid"),
        H("國慶日", D(y, 10, 1), D(y, 10, 2), "mid"),
        H("重陽節", o(L["chongyang"]), travel="low"),
        H("追思節", D(y, 11, 2), travel="low"),
        H("聖母無原罪瞻禮", D(y, 12, 8), travel="low"),
        H("澳門特區成立紀念日", D(y, 12, 20), travel="mid"),
        H("冬至", MO_DONGZHI[y], travel="low"),
        H("聖誕節前日與聖誕節", D(y, 12, 24), D(y, 12, 25), "mid"),
    ]


# 東南亞（新馬印）官方公告的開齋節日期。當地依觀月判定，會比通式晚一天。
SEA_FITR = {2026: d("2026-03-21"), 2027: d("2027-03-10")}


def sun_pair(x):
    """逢週日的假期：當天照放，隔週一補假。回傳 (起, 迄)。"""
    return (x, days(x, 1)) if x.weekday() == 6 else (x, x)


@country("SG")
def sg(y):
    L, I, e = LUNAR[y], ISLAMIC[y], easter(y)
    out = []

    def add(name, day, travel="low", approx=False, note=None):
        a, b = sun_pair(day)
        out.append(H(name, a, b, travel, approx=approx, note=note))

    add("元旦", D(y, 1, 1), "mid")
    out.append(H("農曆新年", L["cny"], days(L["cny"], 1), "high"))
    add("開齋節", SEA_FITR[y], "mid", approx=True)
    out.append(H("耶穌受難日", days(e, -2), travel="mid"))
    add("勞動節", D(y, 5, 1), "mid")
    add("衛塞節", L["vesak"])
    add("哈芝節", I["adha"], approx=True)
    add("國慶日", D(y, 8, 9), "mid")
    add("屠妖節", L["deepavali"])
    add("聖誕節", D(y, 12, 25), "mid")
    return out


@country("MY")
def my(y):
    L, I, F = LUNAR[y], ISLAMIC[y], SEA_FITR[y]
    o = lambda x: observe(x, "sun_to_mon")
    agong = nth_weekday(y, 6, 0, 1)
    vesak_sub = L["vesak"]
    if vesak_sub.weekday() == 6:
        vesak_sub = days(vesak_sub, 1)
        if vesak_sub == agong:
            vesak_sub = days(vesak_sub, 1)
    return [
        H("元旦", o(D(y, 1, 1)), travel="mid"),
        H("農曆新年", L["cny"], days(L["cny"], 1), "high"),
        H("開齋節（Hari Raya Aidilfitri）", days(F, -1), days(F, 2),
          "high", approx=True, closed=True, note="馬來西亞最大返鄉與旅遊潮，商店多歇業"),
        H("勞動節", o(D(y, 5, 1)), travel="mid"),
        # 衛塞節逢週日補假，但若補假日撞上最高元首誕辰要再順延（2026 即為此例）
        H("衛塞節", L["vesak"], vesak_sub, "low"),
        H("最高元首誕辰", agong, travel="low"),
        H("伊斯蘭新年", I["newyear"], travel="low", approx=True),
        H("先知誕辰", I["mawlid"], travel="low", approx=True),
        H("哈芝節（Hari Raya Haji）", I["adha"], days(I["adha"], 1), "mid", approx=True),
        H("國慶日", o(D(y, 8, 31)), travel="mid"),
        H("馬來西亞日", o(D(y, 9, 16)), travel="mid"),
        H("屠妖節", o(L["deepavali"]), travel="low"),
        H("聖誕節", o(D(y, 12, 25)), travel="mid"),
    ]


@country("TH")
def th(y):
    L, T = LUNAR[y], TH_LUNAR[y]
    out, taken = [], set()

    def add(name, day, travel="low", note=None):
        """泰國假日逢週末會補到下一個工作日，補假日與當天都要算。"""
        end = day
        if day.weekday() >= 5:
            end = days(day, 1)
            while end.weekday() >= 5 or end in taken:
                end = days(end, 1)
            taken.add(end)
        else:
            taken.add(day)
        out.append(H(name, day, end, travel, note=note))

    out.append(H("元旦假期", D(y, 1, 1), D(y, 1, 2), "mid",
                 note="內閣通常會加放 1/2 讓跨年假期連起來"))
    add("萬佛節", T["makha"])
    add("卻克里王朝紀念日", D(y, 4, 6))
    out.append(H("宋干節（潑水節）", D(y, 4, 13), D(y, 4, 15), "high",
                 note="泰國新年，全國移動、班機與飯店最滿"))
    add("勞動節", D(y, 5, 1), "mid")
    add("加冕紀念日", D(y, 5, 4))
    add("衛塞節", L["vesak"])
    add("王后誕辰", D(y, 6, 3))
    add("國王誕辰", D(y, 7, 28), "mid")
    out.append(H("三寶佛節與守夏節", T["asalha"], days(T["asalha"], 1), "mid"))
    add("王太后誕辰（母親節）", D(y, 8, 12), "mid")
    add("九世王逝世紀念日", D(y, 10, 13))
    add("五世王紀念日", D(y, 10, 23))
    add("先王誕辰與父親節", D(y, 12, 5), "mid")
    add("行憲紀念日", D(y, 12, 10))
    out.append(H("跨年", D(y, 12, 31), travel="high"))
    return out


@country("VN")
def vn(y):
    L = LUNAR[y]
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("春節（Tết）", days(L["nye"], -2), days(L["cny"], 5), "high", approx=True, closed=True,
          note="越南最大長假，全國停擺、返鄉與出國潮；多數店家關門近一週"),
        H("雄王紀念日", VN_HUNG[y],
          days(VN_HUNG[y], 1) if VN_HUNG[y].weekday() == 6 else VN_HUNG[y], "low"),
        H("南方解放日與勞動節", D(y, 4, 30), D(y, 5, 3), "high", approx=True,
          note="政府通常會調休成 4~5 天連假"),
        H("國慶日", D(y, 9, 2), days(D(y, 9, 2), 2), "mid", approx=True),
    ]


@country("ID")
def idn(y):
    I, L, e, F = ISLAMIC[y], LUNAR[y], easter(y), SEA_FITR[y]
    return [
        H("元旦", D(y, 1, 1), travel="mid"),
        H("先知夜行登霄日", days(I["ramadan"], -33), travel="low", approx=True),
        H("農曆新年與共同假期", days(L["cny"], -1), L["cny"], "mid"),
        H("靜居日（Nyepi）與共同假期", days(ID_NYEPI[y], -1), ID_NYEPI[y], "mid", closed=True,
          note="峇里島全島停擺，機場關閉一整天，旅館不得外出"),
        H("開齋節與共同假期", days(F, -1), days(F, 3), "high", approx=True, closed=True,
          note="Mudik 返鄉潮，東南亞航線最擁擠的期間之一；當地商店大量歇業"),
        H("耶穌受難日與復活節", days(e, -2), e, "low"),
        H("勞動節", D(y, 5, 1), travel="mid"),
        H("耶穌升天日與共同假期", days(e, 39), days(e, 40), "low"),
        H("宰牲節與共同假期", I["adha"], days(I["adha"], 1), "mid", approx=True),
        H("衛塞節", L["vesak"], travel="low"),
        H("潘查希拉日", D(y, 6, 1), travel="low"),
        H("伊斯蘭新年", I["newyear"], travel="low", approx=True),
        H("獨立紀念日", D(y, 8, 17), travel="mid"),
        H("先知誕辰", I["mawlid"], travel="low", approx=True),
        H("聖誕節與共同假期", D(y, 12, 24), D(y, 12, 25), "mid"),
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
        H("諸聖節與追思亡者日", D(y, 11, 1), D(y, 11, 2), "mid"),
        H("博尼法秀日", D(y, 11, 30), travel="low"),
        H("聖母無染原罪日", D(y, 12, 8), travel="low"),
        H("平安夜與聖誕節", D(y, 12, 24), D(y, 12, 25), "high"),
        H("黎剎日與跨年", D(y, 12, 30), D(y, 12, 31), "high"),
    ]


@country("IN")
def ind(y):
    I, L, e = ISLAMIC[y], LUNAR[y], easter(y)
    return [
        H("共和國日", D(y, 1, 26), travel="mid"),
        H("荷麗節（Holi）", L["holi"], days(L["holi"], 1), "mid"),
        H("耶穌受難日", days(e, -2), travel="low"),
        H("開齋節", SEA_FITR[y], travel="mid", approx=True),
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
        H("耶穌受難日", days(e, -2), travel="high"),
        H("聖週（Semana Santa）", days(e, -7), e, "high", kind="season",
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
        H("聖誕假期", D(y, 12, 24), D(y, 12, 26), "high"),
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
        H("仲夏節前夕與仲夏節", midsummer, days(midsummer, 1), "high"),
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
        H("國際婦女節", D(y, 3, 8),
          days(D(y, 3, 8), 1) if D(y, 3, 8).weekday() >= 5 else D(y, 3, 8), "mid"),
        H("春天與勞動節", D(y, 5, 1), D(y, 5, 3), "high"),
        H("勝利日", D(y, 5, 9),
          days(D(y, 5, 9), 2) if D(y, 5, 9).weekday() == 5 else
          (days(D(y, 5, 9), 1) if D(y, 5, 9).weekday() == 6 else D(y, 5, 9)), "mid"),
        H("俄羅斯日", D(y, 6, 12), travel="mid"),
        H("民族團結日", D(y, 11, 4), travel="mid"),
        H("跨年調休日", D(y, 12, 31), travel="mid", approx=True),
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
        H("真相與和解日", D(y, 9, 30), travel="low"),
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
        H("耶穌受難日", days(e, -2), travel="high"),
        H("聖週", days(e, -7), e, "high", kind="season",
          note="墨西哥全國度假週，海灘度假區客滿"),
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
        H("嘉年華", days(e, -48), days(e, -47), "high",
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
        H("阿拉法特日與宰牲節", days(I["adha"], -2), days(I["adha"], 2), "high", approx=True),
        H("伊斯蘭新年", days(I["adha"], 21), travel="low", approx=True),
        H("先知誕辰", days(I["adha"], 80), travel="low", approx=True),
        H("烈士日與國慶日", D(y, 12, 1), D(y, 12, 3), "high"),
    ]


@country("SA")
def sa(y):
    I = ISLAMIC[y]
    return [
        H("建國日", D(y, 2, 22), travel="mid"),
        H("開齋節", days(I["fitr"], -3), days(I["fitr"], 3), "high", approx=True, closed=True,
          note="沙國最大出境旅遊潮，當地幾乎全面停擺"),
        H("宰牲節與朝覲", days(I["adha"], -3), days(I["adha"], 3), "high", approx=True),
        H("國慶日", D(y, 9, 23), travel="mid"),
    ]


@country("IL")
def il(y):
    T = IL_TABLE[y]
    return [
        H("普珥節", T["purim"], travel="low"),
        H("逾越節", T["pesach"][0], T["pesach"][1], "high", closed=True,
          note="以色列全國放假，出國旅遊高峰；當地餐廳供餐受限"),
        H("五旬節", T["shavuot"], travel="mid"),
        H("猶太新年", T["rosh"][0], T["rosh"][1], "high"),
        H("贖罪日", T["kippur"], travel="mid", closed=True,
          note="全國完全停止運作，機場關閉、無大眾運輸、店家全關"),
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

def build_country(code, year):
    """有專屬函式的用專屬函式，其餘用「範本 + 國定紀念日」組出來。"""
    if code in BUILDERS:
        return BUILDERS[code](year)
    spec = SIMPLE.get(code)
    if spec is None:
        raise SystemExit(f"缺少 {code} 的假期定義")
    out = []
    if spec["p"]:
        out += PROFILES[spec["p"]](year)
    for name, month, day, travel in spec["n"]:
        out.append(H(name, D(year, month, day), travel=travel))
    if spec["x"]:
        out += spec["x"](year)
    return out


def main():
    countries, holidays = [], {}
    for code, name, en, flag, region, weight, closure in COUNTRIES:
        meta = {"code": code, "name": name, "en": en, "flag": flag,
                "region": region, "weight": weight, "closure": closure,
                "verified": code in VERIFIED}
        if code in WEEKENDS:
            meta["weekend"] = WEEKENDS[code]
        countries.append(meta)

        entries = []
        for y in YEARS:
            entries.extend(build_country(code, y))
        entries.sort(key=lambda x: (x["start"], x["end"]))

        seen, deduped = set(), []
        for x in entries:
            key = (x["name"], x["start"], x["end"])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(x)
        holidays[code] = deduped

    payload = {"generated": dt.date.today().isoformat(), "years": YEARS,
               "countries": countries, "holidays": holidays}
    out = ROOT / "data" / "holidays.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")
    total = sum(len(v) for v in holidays.values())
    detailed = sum(1 for c, *_ in COUNTRIES if c in BUILDERS)
    print(f"寫入 {out}：{len(countries)} 個國家（{detailed} 個專屬定義 / "
          f"{len(countries) - detailed} 個範本，{len(VERIFIED)} 個已逐一核對）、"
          f"{total} 筆假期、{out.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
