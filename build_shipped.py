#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从母版 shark.full.js 生成上线版 shark.js —— 只保留本地已有图片的物种。
   按「目」自动归入 鲨类/鳐类/银鲛 三大类（软骨鱼的天然分支结构）。
   附加 科/目/IUCN/GBIF，并产出 credits.json + gbif.json。"""
import collections, json, os, re, urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))

# 软骨鱼三大分支：板鳃亚纲的鲨形类 / 鳐形类 + 全头亚纲的银鲛
SHARK_ORDERS = {"Carcharhiniformes", "Lamniformes", "Orectolobiformes", "Squaliformes",
                "Hexanchiformes", "Squatiniformes", "Heterodontiformes",
                "Pristiophoriformes", "Echinorhiniformes"}
RAY_ORDERS   = {"Rajiformes", "Myliobatiformes", "Torpediniformes", "Pristiformes",
                "Rhinopristiformes", "Rhiniformes"}
CHIMAERA     = {"Chimaeriformes"}

def load(path):
    txt = open(os.path.join(ROOT, path), encoding="utf-8").read()
    arr = re.sub(r"/\*.*?\*/", "", txt[txt.index("["):txt.rindex("]") + 1], flags=re.S)
    return json.loads(arr)

def jload(name):
    p = os.path.join(ROOT, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}

def have_images():
    """哪些物种有图 —— 以 COS 上传清单 _uploaded.json 为准。
       历史上是扫描本地 images/ 目录，但项目在 OneDrive 里、图片会白占云盘空间，
       现已改为「下载→直传 COS→删本地」（见 fetch_to_cos.py），本地不再留图。
       若清单不存在则回退到扫描本地目录（兼容旧流程）。"""
    up = os.path.join(ROOT, "_uploaded.json")
    if os.path.exists(up):
        return set(json.load(open(up)))
    have, d = set(), os.path.join(ROOT, "images")
    if not os.path.isdir(d):
        return have
    for f in os.listdir(d):
        if f.endswith(".jpg") and f[:-4].isdigit() and os.path.getsize(os.path.join(d, f)) > 1500:
            have.add(int(f[:-4]))
    return have

def commons_name(u):
    u = urllib.parse.unquote((u or "").split("?")[0])
    for pat in (r"/commons/(?:thumb/)?[0-9a-f]/[0-9a-f]{2}/([^/]+)$",
                r"/commons/thumb/[0-9a-f]/[0-9a-f]{2}/([^/]+)/",
                r"Special:FilePath/(.+)$"):
        m = re.search(pat, u)
        if m:
            return m.group(1)
    return ""

def to_cat(la):
    if la in SHARK_ORDERS: return "shark"
    if la in RAY_ORDERS:   return "ray"
    if la in CHIMAERA:     return "chimaera"
    return ""

def main():
    full = load("shark.full.js")
    have = have_images()
    ship = [f for f in full if f["id"] in have]
    print("母版 %d 条 | 本地图 %d 张 | 上线 %d 条" % (len(full), len(have), len(ship)))

    orders, fams = jload("_orders_of_sp.json"), jload("_families.json")
    iucn, gbif = jload("_iucn.json"), jload("_gbif.json")

    n_ord = n_fam = n_iu = 0
    for f in ship:
        o = orders.get(f["sci"])
        if o and (o.get("zh") or o.get("la")):
            f["order"] = o.get("zh") or o.get("la")
            f["order_en"] = o.get("la", "")
            n_ord += 1
        fm = fams.get(f["sci"])
        if fm and (fm.get("zh") or fm.get("la")):
            f["family"] = fm.get("zh") or fm.get("la")
            f["family_en"] = fm.get("la", "")
            n_fam += 1
        c = iucn.get(f["sci"])
        if c:
            f["iucn"] = c
            n_iu += 1

    # 缺目的用同科其他物种补（科→目是稳定的一对一关系）
    f2o = {}
    for f in ship:
        if f.get("family") and f.get("order"):
            key = (f["order"], f.get("order_en", ""))
            f2o.setdefault(f["family"], collections.Counter())[key] += 1
    for f in ship:
        if f.get("order") or not f.get("family"):
            continue
        cand = f2o.get(f["family"])
        if cand:
            (zh, la), _ = cand.most_common(1)[0]
            f["order"], f["order_en"] = zh, la

    for f in ship:
        f["cat"] = to_cat(f.get("order_en", "")) or "shark"   # 兜底：软骨鱼里鲨类占多数
    print("补到: 目 %d | 科 %d | IUCN %d" % (n_ord, n_fam, n_iu))

    ship = [{k: v for k, v in f.items() if v not in ("", None)} for f in ship]
    body = ",\n".join(json.dumps(e, ensure_ascii=False) for e in ship)
    open(os.path.join(ROOT, "shark.js"), "w", encoding="utf-8").write(
        "/* 1001 种软骨鱼 — 上线数据集（%d 条，均有真实照片）\n"
        "   由 build_shipped.py 从母版 shark.full.js 生成。母版共 %d 条。 */\n"
        "window.SHARK_DATA = [\n" % (len(ship), len(full)) + body + "\n];\n")

    imgmap = jload("_imgmap.json")
    credits = {}
    for f in ship:
        n = commons_name(imgmap.get(str(f["id"]), ""))
        if n:
            credits[str(f["id"])] = n
    json.dump(credits, open(os.path.join(ROOT, "credits.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    gout = {f["sci"]: gbif[f["sci"]] for f in ship if gbif.get(f["sci"], {}).get("k")}
    json.dump(gout, open(os.path.join(ROOT, "gbif.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))

    cc = collections.Counter(f["cat"] for f in ship)
    withi = [f for f in ship if f.get("iucn")]
    th = sum(1 for f in withi if f["iucn"] in ("NT", "VU", "EN", "CR", "EW", "EX"))
    print("credits %d | gbif %d | 科 %d | 目 %d" % (
        len(credits), len(gout),
        len({f.get("family") for f in ship if f.get("family")}),
        len({f.get("order") for f in ship if f.get("order")})))
    print("三大类: " + " / ".join("%s %d" % (k, v) for k, v in cc.most_common()))
    if withi:
        print("受威胁: %d/%d = %.0f%%" % (th, len(withi), 100 * th / len(withi)))

if __name__ == "__main__":
    main()
