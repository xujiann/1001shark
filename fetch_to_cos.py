#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""下载图片 → 直传腾讯云 COS → 立即删本地。全程不在 OneDrive 留副本。

背景：项目目录在 OneDrive 里，images/ 会被同步到云盘白占空间（曾达 1.2GB）。
本脚本用系统临时目录中转，传完即删，本地零残留。

已上传的记录在 _uploaded.json（也是 build_shipped.py 判断「哪些物种有图」的依据，
不再依赖扫描本地 images/ 目录）。

用法:
  COS_SECRET_ID=xx COS_SECRET_KEY=yy python fetch_to_cos.py <imgmap.json> <cos前缀> [--workers N]
"""
import json, os, sys, tempfile, time, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
UA = "1001-collections/1.0 (educational gallery; popstudy@gmail.com)"
WIDTH = 600
TMP = os.path.join(tempfile.gettempdir(), "1001img")   # 系统临时目录，不在 OneDrive

sys.path.insert(0, ROOT)
import cos_upload   # 复用已验证的 COS 签名与上传


def fetch_one(args):
    fid, url, prefix = args
    tmp = os.path.join(TMP, "%s.jpg" % fid)
    src = url + ("&" if "?" in url else "?") + "width=%d" % WIDTH
    for a in range(3):
        try:
            req = urllib.request.Request(src, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=180) as r:
                blob = r.read()
            if len(blob) < 1500:
                raise ValueError("too small")
            with open(tmp, "wb") as f:
                f.write(blob)
            ok, info = cos_upload.put(tmp, "%s/%s.jpg" % (prefix, fid))
            os.remove(tmp)                      # 传完立刻删，本地不留
            return (fid, "ok", info) if ok else (fid, "cosfail", info)
        except Exception as e:
            if os.path.exists(tmp):
                try: os.remove(tmp)
                except OSError: pass
            if a == 2:
                return fid, "fail", str(e)[:60]
            time.sleep(2 + a * 3)
    return fid, "fail", ""


def main():
    if not os.environ.get("COS_SECRET_ID") or not os.environ.get("COS_SECRET_KEY"):
        print("缺少 COS_SECRET_ID / COS_SECRET_KEY 环境变量"); sys.exit(1)
    imgmap_file = sys.argv[1]
    prefix = sys.argv[2].strip("/")
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 6

    os.makedirs(TMP, exist_ok=True)
    imgmap = json.load(open(os.path.join(ROOT, imgmap_file), encoding="utf-8"))
    up_path = os.path.join(ROOT, "_uploaded.json")
    done = set(json.load(open(up_path))) if os.path.exists(up_path) else set()

    todo = [(k, v, prefix) for k, v in sorted(imgmap.items(), key=lambda kv: int(kv[0]))
            if int(k) not in done]
    print("总 %d，已传 %d，待办 %d（并发 %d，暂存 %s）" %
          (len(imgmap), len(done), len(todo), workers, TMP)); sys.stdout.flush()

    ok = fail = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, (fid, status, info) in enumerate(ex.map(fetch_one, todo), 1):
            if status == "ok":
                ok += 1; done.add(int(fid))
            else:
                fail += 1
                if fail <= 5: print("  失败 %s: %s %s" % (fid, status, info))
            if i % 50 == 0:
                json.dump(sorted(done), open(up_path, "w"))
                el = time.time() - t0
                print("  %d/%d ok=%d fail=%d %.0fs 剩约%.0f分" %
                      (i, len(todo), ok, fail, el, (len(todo)-i)/max(i/el, .01)/60))
                sys.stdout.flush()
    json.dump(sorted(done), open(up_path, "w"))
    print("=== 完成: %d 成功, %d 失败, 已上传总数 %d ===" % (ok, fail, len(done)))
    # 清空临时目录
    try:
        for f in os.listdir(TMP): os.remove(os.path.join(TMP, f))
    except OSError: pass


if __name__ == "__main__":
    main()
