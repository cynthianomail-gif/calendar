# -*- coding: utf-8 -*-
"""
把 data/holidays.json 包成瀏覽器可直接載入的 data/holidays.js，
並產生 dist/index.html —— 一個把 CSS / JS / 資料全部內嵌的單檔版本，
方便直接用 email 傳、或丟到任何靜態空間、甚至離線用瀏覽器開。

    python3 scripts/build_site.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    data = (ROOT / "data" / "holidays.json").read_text(encoding="utf-8")
    js = "window.HOLIDAY_DATA=" + data + ";\n"
    (ROOT / "data" / "holidays.js").write_text(js, encoding="utf-8")

    html = (ROOT / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "assets" / "styles.css").read_text(encoding="utf-8")
    app = (ROOT / "assets" / "app.js").read_text(encoding="utf-8")

    html = html.replace(
        '<link rel="stylesheet" href="assets/styles.css">',
        "<style>\n" + css + "\n</style>",
    )
    html = html.replace(
        '<script src="data/holidays.js"></script>\n<script src="assets/app.js"></script>',
        "<script>\n" + js + "</script>\n<script>\n" + app + "\n</script>",
    )

    out_dir = ROOT / "dist"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"寫入 data/holidays.js 與 {out}（{out.stat().st_size/1024:.0f} KB 單檔版）")


if __name__ == "__main__":
    main()
