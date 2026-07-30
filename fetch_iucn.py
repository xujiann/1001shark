#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 Wikidata 采集 IUCN 濒危等级（P141），累积写入 _iucn.json。
   按 QID 映射成标准代码（LC/NT/VU/EN/CR/EW/EX/DD），不用中文标签
   —— Wikidata 上的中文标签繁简混杂（「易危物種」「无危物种」），QID 才稳定。
   可随时中断续跑。"""
import json, os, sys, time, urllib.parse, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "_iucn.json")
UA = "1001fish/1.0 (educational; popstudy@gmail.com)"
EP = "https://query.wikidata.org/sparql"
CHUNK = 120

# 用英文标签识别等级，避免硬编码 QID（此前吃过猜 QID 的亏）
LABEL2CODE = [
    ("critically endangered", "CR"), ("extinct in the wild", "EW"),
    ("near threatened", "NT"), ("least concern", "LC"),
    ("data deficient", "DD"), ("endangered", "EN"),
    ("vulnerable", "VU"), ("extinct", "EX"),
]

def to_code(label):
    l = (label or "").lower()
    for key, code in LABEL2CODE:      # 长的在前，避免 "endangered" 抢了 "critically endangered"
        if key in l:
            return code
    return ""

def sparql(q, tries=6):
    url = EP + "?" + urllib.parse.urlencode({"query": q, "format": "json"})
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept": "application/sparql-results+json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode("utf-8"))["results"]["bindings"]
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and a < tries - 1:
                print("   HTTP %d，等 60s" % e.code); sys.stdout.flush(); time.sleep(60); continue
            raise
        except Exception as e:
            if a < tries - 1:
                print("   %s，等 20s" % type(e).__name__); sys.stdout.flush(); time.sleep(20); continue
            raise

def load_scis():
    txt = open(os.path.join(ROOT, "shark.full.js"), encoding="utf-8").read()
    import re
    arr = re.sub(r"/\*.*?\*/", "", txt[txt.index("["):txt.rindex("]")+1], flags=re.S)
    return [f["sci"] for f in json.loads(arr)]

def main():
    scis = load_scis()
    out = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    todo = [s for s in scis if s not in out]
    print("共 %d 种，已有 %d，待查 %d" % (len(scis), len(out), len(todo))); sys.stdout.flush()

    for i in range(0, len(todo), CHUNK):
        chunk = todo[i:i+CHUNK]
        vals = " ".join('"%s"' % s.replace('"', '') for s in chunk)
        q = """SELECT ?sci ?st ?stLabel WHERE {
          VALUES ?sci { %s }
          ?item wdt:P225 ?sci ; wdt:P141 ?st .
          SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
        }""" % vals
        try:
            rows = sparql(q)
        except Exception as e:
            print("  块 %d 失败 %s" % (i, str(e)[:50])); continue
        got = 0
        for r in rows:
            sci = r["sci"]["value"]
            if sci in out: continue
            code = to_code(r.get("stLabel", {}).get("value", ""))
            if code:
                out[sci] = code; got += 1
        # 本块查不到的也记空串，避免下次重复查
        for s in chunk:
            out.setdefault(s, "")
        json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        have = sum(1 for v in out.values() if v)
        print("  %d-%d: +%d（累计有等级 %d）" % (i, i+len(chunk), got, have)); sys.stdout.flush()
        time.sleep(2)

    have = sum(1 for v in out.values() if v)
    print("=== 完成：%d/%d 有濒危等级 ===" % (have, len(out)))

if __name__ == "__main__":
    main()
