#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""找出数据里的「同物异名」重复条目。

判据不能只看 GBIF 的 usageKey ——异名也有自己的 key，光比 key 会漏判。
要看 `status`：SYNONYM 的条目带 `acceptedUsageKey`，指向有效名的 key。
两条记录若一条的 acceptedUsageKey 等于另一条的 usageKey，就是同一个物种。

只报告，不自动删——删哪条要看图片质量与命名习惯，交人判断。
"""
import collections, io, json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
UA = "1001fish/1.0 (educational; popstudy@gmail.com)"
DATA = sys.argv[1] if len(sys.argv) > 1 else "fish.js"
CACHE = os.path.join(ROOT, "_syn_cache.json")

def load():
    t = io.open(os.path.join(ROOT, DATA), encoding="utf-8").read()
    return json.loads(re.sub(r"/\*.*?\*/", "", t[t.index("["):t.rindex("]")+1], flags=re.S))

def match(name, cache):
    if name in cache:
        return cache[name]
    u = "https://api.gbif.org/v1/species/match?name=" + urllib.parse.quote(name)
    for a in range(3):
        try:
            d = json.loads(urllib.request.urlopen(
                urllib.request.Request(u, headers={"User-Agent": UA}), timeout=40).read())
            r = {"status": d.get("status"), "key": d.get("usageKey"),
                 "accepted": d.get("acceptedUsageKey")}
            cache[name] = r
            return r
        except Exception:
            if a == 2:
                cache[name] = {"status": "ERR"}
                return cache[name]
            time.sleep(2)

def main():
    d = load()
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    by_zh = collections.defaultdict(list)
    for x in d:
        by_zh[x["name"]].append(x)
    groups = {k: v for k, v in by_zh.items() if len(v) > 1}
    print("重名 %d 组，逐组核对 GBIF 分类学地位…" % len(groups))

    dups, ok = [], []
    for i, (name, items) in enumerate(sorted(groups.items()), 1):
        info = [match(x["sci"], cache) for x in items]
        keys = {j.get("key") for j in info if j.get("key")}
        accs = {j.get("accepted") for j in info if j.get("accepted")}
        # 有条目的 accepted 指向同组另一条的 key → 同物异名
        if accs & keys:
            dups.append((name, items, info))
        else:
            ok.append((name, items, info))
        if i % 5 == 0:
            json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
        time.sleep(0.4)
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)

    out = ["同物异名（同一物种收录了两次）: %d 组" % len(dups), ""]
    for name, items, info in dups:
        out.append("  %s" % name)
        for x, j in zip(items, info):
            out.append("     id%-5d %-28s %-9s key=%s accepted=%s" %
                       (x["id"], x["sci"], j.get("status"), j.get("key"), j.get("accepted")))
    out += ["", "不同物种共用俗名（保留）: %d 组" % len(ok)]
    for name, items, info in ok:
        out.append("  %-14s %s" % (name, " / ".join(x["sci"] for x in items)))
    io.open(os.path.join(ROOT, "_syn_report.txt"), "w", encoding="utf-8").write("\n".join(out))
    print("同物异名 %d 组 / 合理重名 %d 组 → _syn_report.txt" % (len(dups), len(ok)))

if __name__ == "__main__":
    main()
