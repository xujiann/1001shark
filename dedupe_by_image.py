#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""靠「共用同一张照片」找出 GBIF 状态查不出来的同物异名。

为什么需要这一步：check_synonyms.py 用 GBIF 的 SYNONYM/ACCEPTED 状态判定，
但遇到分类学界尚有分歧的名字（如 Carcharocles / Otodus angustidens），
GBIF 两边都标 ACCEPTED，就漏判了。

更强的信号：Wikidata 给这两条记录配了同一张照片 —— 说明是同一条鱼。
再加一道保险：**种加词必须相同**（属被移动但种加词保留，是同物异名的典型特征）。
种加词不同却共用图片的，属于「不同物种但其中一条配错了图」，不在此处理。

保留哪条：优先 GBIF 判为 ACCEPTED 的；都没判就留 id 较小的（先收录的）。
只动母版 *.full.js，上线版由 build_shipped.py 重新生成。
"""
import collections, io, json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
FULL = sys.argv[1] if len(sys.argv) > 1 else "fish.full.js"
SHIPPED = FULL.replace(".full", "")
VAR = "SHARK_DATA" if "shark" in FULL else "FISH_DATA"

def load(path):
    t = io.open(os.path.join(ROOT, path), encoding="utf-8").read()
    return t, json.loads(re.sub(r"/\*.*?\*/", "", t[t.index("["):t.rindex("]")+1], flags=re.S))

def main():
    credits = json.load(open(os.path.join(ROOT, "credits.json"), encoding="utf-8"))
    cache_p = os.path.join(ROOT, "_syn_cache.json")
    cache = json.load(open(cache_p, encoding="utf-8")) if os.path.exists(cache_p) else {}

    _, shipped = load(SHIPPED)
    by_id = {str(x["id"]): x for x in shipped}

    # 同一张 Commons 图 → 候选重复
    by_img = collections.defaultdict(list)
    for i, f in credits.items():
        if i in by_id:
            by_img[f].append(i)

    drop, report = set(), []
    for f, ids in by_img.items():
        if len(ids) < 2:
            continue
        eps = {by_id[i]["sci"].split()[-1].lower() for i in ids}
        if len(eps) != 1:
            continue                      # 种加词不同 → 是配错图，不是异名
        # 保留 GBIF 认定 ACCEPTED 的；没有就留 id 最小的
        acc = [i for i in ids if cache.get(by_id[i]["sci"], {}).get("status") == "ACCEPTED"]
        keep = acc[0] if acc else min(ids, key=lambda x: int(x))
        for i in ids:
            if i != keep:
                drop.add(int(i))
                report.append("  删 id%-5s %-30s → 保留 %s" %
                              (i, by_id[i]["sci"], by_id[keep]["sci"]))

    if not drop:
        print("没有需要合并的同物异名"); return

    head, data = load(FULL)
    kept = [x for x in data if x["id"] not in drop]
    header = head[:head.index("[")].rsplit("window.", 1)[0]
    header = re.sub(r"（\d+ 条", "（%d 条" % len(kept), header)
    body = ",\n".join(json.dumps(e, ensure_ascii=False) for e in kept)
    io.open(os.path.join(ROOT, FULL), "w", encoding="utf-8").write(
        header + "window.%s = [\n" % VAR + body + "\n];\n")

    print("按共用图片合并 %d 条同物异名，母版 %d → %d" % (len(drop), len(data), len(kept)))
    print("\n".join(report))

if __name__ == "__main__":
    main()
