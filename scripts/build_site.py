# -*- coding: utf-8 -*-
"""
把 data/holidays.json 包成瀏覽器可直接載入的 data/holidays.js，
並產生兩個內嵌全部 CSS / JS / 資料的單檔版本：

* dist/index.html    —— 完整 HTML，可直接用瀏覽器開、email 傳、丟任何靜態空間
* dist/artifact.html —— 同樣內容但省略 doctype/html/head/body 外殼，
                        給需要自己包外層的環境（例如 Claude Artifact）使用

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

    # 去掉外殼版本：保留 <title>、字體連結與 <style>，其餘取 <body> 內容
    head = html[html.index("<head>") + 6: html.index("</head>")]
    keep = []
    for line in head.splitlines():
        st = line.strip()
        if st.startswith("<title>") or st.startswith("<link rel=\"preconnect\"") \
           or st.startswith("<link rel=\"stylesheet\"") or st.startswith("<meta name=\"description\""):
            keep.append(st)
    style = head[head.index("<style>"): head.index("</style>") + 8]
    body = html[html.index("<body>") + 6: html.rindex("</body>")].strip()
    shell = "\n".join(keep) + "\n" + style + "\n" + body + "\n"
    out2 = out_dir / "artifact.html"
    out2.write_text(shell, encoding="utf-8")

    print(f"寫入 data/holidays.js、{out}（{out.stat().st_size/1024:.0f} KB）"
          f"與 {out2}（{out2.stat().st_size/1024:.0f} KB）")


if __name__ == "__main__":
    main()
