#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为每个物种取 GBIF taxonKey（用于弹窗里渲染分布图）+ 观测记录数。
   累积写 _gbif.json: {sci: {"k":taxonKey, "n":观测数}}；可随时中断续跑。
   分布图本身不下载——前端按需向 GBIF 瓦片接口取，零存储。"""
import json, os, sys, time, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "_gbif.json")
UA = "1001fish/1.0 (educational bilingual fish gallery; popstudy@gmail.com)"

def get_json(url, tries=3, timeout=40):
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if a == tries - 1: return None
            time.sleep(1.5 + a * 2)
    return None

def lookup(sci):
    """学名 -> (taxonKey, 观测数)。只接受 SPECIES 级的精确/模糊匹配。"""
    d = get_json("https://api.gbif.org/v1/species/match?name=" + urllib.parse.quote(sci))
    if not d or d.get("matchType") == "NONE": return sci, None
    key = d.get("usageKey")
    if not key or d.get("rank") not in ("SPECIES", "SUBSPECIES"): return sci, None
    # capabilities 顺带给出观测总数，比 occurrence/search 轻
    cap = get_json("https://api.gbif.org/v2/map/occurrence/density/capabilities.json?taxonKey=%d" % key)
    n = (cap or {}).get("total", 0)
    return sci, {"k": key, "n": n}

def load_scis():
    import re
    txt = open(os.path.join(ROOT, "shark.full.js"), encoding="utf-8").read()
    arr = re.sub(r"/\*.*?\*/", "", txt[txt.index("["):txt.rindex("]")+1], flags=re.S)
    return [f["sci"] for f in json.loads(arr)]

def main():
    workers = int(sys.argv[sys.argv.index("--workers")+1]) if "--workers" in sys.argv else 8
    scis = load_scis()
    out = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    todo = [s for s in scis if s not in out]
    print("共 %d 种，已有 %d，待查 %d（并发 %d）" % (len(scis), len(out), len(todo), workers))
    sys.stdout.flush()

    ok = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, (sci, res) in enumerate(ex.map(lookup, todo), 1):
            out[sci] = res if res else {}
            if res: ok += 1
            if i % 100 == 0:
                json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
                el = time.time() - t0
                print("  %d/%d 命中 %d，%.0fs，剩约 %.0f 分" %
                      (i, len(todo), ok, el, (len(todo)-i)/max(i/el, .01)/60)); sys.stdout.flush()
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    have = sum(1 for v in out.values() if v)
    print("=== 完成：%d/%d 有 GBIF 记录 ===" % (have, len(out)))

if __name__ == "__main__":
    main()
