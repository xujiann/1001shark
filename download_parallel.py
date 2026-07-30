#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""并发下载 _imgmap.json 里的图片（串行版 5000 张要 40+ 分钟，并发约 5 分钟）。
   写临时文件再原子改名，避免中断留下半截文件。跳过已存在的。"""
import json, os, sys, time, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(ROOT, "images")
UA = "1001fish/1.0 (educational bilingual fish gallery; popstudy@gmail.com)"
WIDTH = 600

def thumb_url(u):
    return u + ("&" if "?" in u else "?") + "width=%d" % WIDTH

def fetch(item, tries=3):
    fid, url = item
    dest = os.path.join(IMG_DIR, "%s.jpg" % fid)
    if os.path.exists(dest) and os.path.getsize(dest) > 1500:
        return fid, "skip", 0
    for a in range(tries):
        try:
            req = urllib.request.Request(thumb_url(url), headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=180) as r:
                blob = r.read()
            if len(blob) < 1500:
                raise ValueError("too small")
            tmp = dest + ".part"
            with open(tmp, "wb") as f:
                f.write(blob)
            os.replace(tmp, dest)          # 原子替换
            return fid, "ok", len(blob)
        except Exception as e:
            if a == tries - 1:
                return fid, "fail:" + str(e)[:50], 0
            time.sleep(2 + a * 3)
    return fid, "fail", 0

def main():
    workers = int(sys.argv[sys.argv.index("--workers")+1]) if "--workers" in sys.argv else 6
    imgmap = json.load(open(os.path.join(ROOT, "_imgmap.json"), encoding="utf-8"))
    os.makedirs(IMG_DIR, exist_ok=True)
    items = sorted(imgmap.items(), key=lambda kv: int(kv[0]))
    todo = [(k, v) for k, v in items
            if not (os.path.exists(os.path.join(IMG_DIR, k + ".jpg"))
                    and os.path.getsize(os.path.join(IMG_DIR, k + ".jpg")) > 1500)]
    print("总 %d 张，待下载 %d 张，并发 %d" % (len(items), len(todo), workers)); sys.stdout.flush()

    ok = fail = 0; fails = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, (fid, status, n) in enumerate(ex.map(fetch, todo), 1):
            if status == "ok": ok += 1
            elif status.startswith("fail"):
                fail += 1; fails.append(fid)
            if i % 200 == 0:
                el = time.time() - t0
                print("  %d/%d (ok=%d fail=%d) %.0fs 剩约%.0f分" %
                      (i, len(todo), ok, fail, el, (len(todo)-i)/max(i/el,.01)/60)); sys.stdout.flush()
    print("=== 完成: %d 成功, %d 失败, 用时 %.0f 秒 ===" % (ok, fail, time.time()-t0))
    if fails:
        json.dump(fails, open(os.path.join(ROOT, "_dl_fails.json"), "w"), ensure_ascii=False)
        print("失败 id 已存 _dl_fails.json:", fails[:15])

if __name__ == "__main__":
    main()
