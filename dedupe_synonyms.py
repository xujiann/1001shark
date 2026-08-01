#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""删除「同物异名」造成的重复条目 —— 保留 GBIF 认定的有效名（ACCEPTED），
   删掉异名（SYNONYM）那条。

只动母版 *.full.js；上线版由 build_shipped.py 重新生成。
依赖 check_synonyms.py 产出的 _syn_cache.json（GBIF 分类学地位）。
"""
import collections, io, json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
FULL = sys.argv[1] if len(sys.argv) > 1 else "fish.full.js"
VAR = "FISH_DATA" if "fish" in FULL else "SHARK_DATA"

def main():
    cache = json.load(open(os.path.join(ROOT, "_syn_cache.json"), encoding="utf-8"))
    txt = io.open(os.path.join(ROOT, FULL), encoding="utf-8").read()
    arr = re.sub(r"/\*.*?\*/", "", txt[txt.index("["):txt.rindex("]")+1], flags=re.S)
    data = json.loads(arr)

    by_zh = collections.defaultdict(list)
    for x in data:
        by_zh[x["name"]].append(x)

    drop = set()
    report = []
    for name, items in by_zh.items():
        if len(items) < 2:
            continue
        info = {x["id"]: cache.get(x["sci"], {}) for x in items}
        keys = {j.get("key") for j in info.values() if j.get("key")}
        if not ({j.get("accepted") for j in info.values() if j.get("accepted")} & keys):
            continue      # 不是同物异名，保留
        for x in items:
            j = info[x["id"]]
            if j.get("status") == "SYNONYM" and j.get("accepted") in keys:
                drop.add(x["id"])
                keep = [y["sci"] for y in items if y["id"] != x["id"]]
                report.append("  删 id%-5d %-28s（异名）→ 保留 %s" %
                              (x["id"], x["sci"], " / ".join(keep)))

    if not drop:
        print("没有需要删除的条目"); return

    kept = [x for x in data if x["id"] not in drop]
    header = txt[:txt.index("[")].rstrip()
    header = re.sub(r"（\d+ 条", "（%d 条" % len(kept), header)
    body = ",\n".join(json.dumps(e, ensure_ascii=False) for e in kept)
    io.open(os.path.join(ROOT, FULL), "w", encoding="utf-8").write(
        header.rsplit("window.", 1)[0] + "window.%s = [\n" % VAR + body + "\n];\n")

    print("删除 %d 条同物异名重复，母版 %d → %d" % (len(drop), len(data), len(kept)))
    print("\n".join(report))

if __name__ == "__main__":
    main()
