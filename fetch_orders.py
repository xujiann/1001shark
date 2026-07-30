#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为 fish.js 中 family 为空的条目（cat=more 的 762 条）从 Wikidata 补科名。
   分块查询（学名 VALUES → 科的拉丁名 P225 + 中文标签），写 _orders_of_sp.json {sci:{la,zh}}。"""
import json, os, re, sys, time, urllib.parse, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
UA = "1001fish/1.0 (educational; popstudy@gmail.com)"
EP = "https://query.wikidata.org/sparql"
CHUNK = 100

def load_more_scis():
    txt = open(os.path.join(ROOT, "shark.full.js"), encoding="utf-8").read()
    arr = re.sub(r"/\*.*?\*/", "", txt[txt.index("["):txt.rindex("]")+1], flags=re.S)
    d = json.loads(arr)
    return [f["sci"] for f in d]

def query(scis, tries=6):
    values = " ".join('"%s"' % s.replace('"', '') for s in scis)
    q = ("SELECT ?sci ?famLa ?famZh WHERE { VALUES ?sci { %s } "
         "?item wdt:P225 ?sci ; wdt:P171* ?fam . "
         "?fam wdt:P105 wd:Q36602 ; wdt:P225 ?famLa . "
         'OPTIONAL { ?fam rdfs:label ?famZh . FILTER(LANG(?famZh)="zh") } }' % values)
    url = EP + "?" + urllib.parse.urlencode({"query": q, "format": "json"})
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                     "Accept": "application/sparql-results+json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))["results"]["bindings"]
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and a < tries - 1:
                print("   %d, wait 65s..." % e.code); sys.stdout.flush(); time.sleep(65); continue
            raise
        except Exception as e:   # 网络超时/断连：退避重试
            if a < tries - 1:
                print("   net err (%s), wait 20s..." % type(e).__name__); sys.stdout.flush(); time.sleep(20); continue
            raise

def main():
    scis = load_more_scis()
    print("need orders for", len(scis), "species")
    out = {}
    if os.path.exists(os.path.join(ROOT, "_orders_of_sp.json")):
        out = json.load(open(os.path.join(ROOT, "_orders_of_sp.json"), encoding="utf-8"))
    todo = [s for s in scis if s not in out]
    for i in range(0, len(todo), CHUNK):
        chunk = todo[i:i+CHUNK]
        rows = query(chunk)
        got = 0
        for r in rows:
            sci = r["sci"]["value"]
            if sci in out:
                continue
            out[sci] = {"la": r.get("famLa", {}).get("value", ""),
                        "zh": r.get("famZh", {}).get("value", "")}
            got += 1
        json.dump(out, open(os.path.join(ROOT, "_orders_of_sp.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=0)
        print("  chunk %d-%d: +%d (total %d)" % (i, i+len(chunk), got, len(out)))
        time.sleep(2)
    print("=== done: %d/%d have order ===" % (len([s for s in scis if s in out]), len(scis)))

if __name__ == "__main__":
    main()
