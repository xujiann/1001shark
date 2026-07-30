#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""腾讯云 COS 上传（纯标准库实现签名，不依赖 SDK）。
   密钥从环境变量读取：COS_SECRET_ID / COS_SECRET_KEY
   用法: python cos_upload.py <本地目录> <远端前缀> [--limit N] [--workers N]
"""
import hashlib, hmac, os, sys, time, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

BUCKET = os.environ.get("COS_BUCKET", "pic-1302017848")
REGION = os.environ.get("COS_REGION", "ap-nanjing")
SID    = os.environ.get("COS_SECRET_ID", "")
SKEY   = os.environ.get("COS_SECRET_KEY", "")
HOST   = "%s.cos.%s.myqcloud.com" % (BUCKET, REGION)

def sign(method, uri, headers=None, expire=3600):
    """生成 COS 请求签名 (q-sign-algorithm=sha1)"""
    headers = headers or {}
    now = int(time.time())
    key_time = "%d;%d" % (now - 60, now + expire)
    sign_key = hmac.new(SKEY.encode(), key_time.encode(), hashlib.sha1).hexdigest()
    hl = sorted(k.lower() for k in headers)
    header_str = "&".join("%s=%s" % (k, urllib.parse.quote(str(headers[[x for x in headers if x.lower()==k][0]]), safe=""))
                          for k in hl)
    http_string = "%s\n%s\n\n%s\n" % (method.lower(), uri, header_str)
    sha1_http = hashlib.sha1(http_string.encode()).hexdigest()
    string_to_sign = "sha1\n%s\n%s\n" % (key_time, sha1_http)
    signature = hmac.new(sign_key.encode(), string_to_sign.encode(), hashlib.sha1).hexdigest()
    return ("q-sign-algorithm=sha1&q-ak=%s&q-sign-time=%s&q-key-time=%s"
            "&q-header-list=%s&q-url-param-list=&q-signature=%s"
            % (SID, key_time, key_time, ";".join(hl), signature))

def put(local_path, key, tries=3):
    """上传单个文件，key 如 'fish/1.jpg'"""
    uri = "/" + urllib.parse.quote(key)
    url = "https://%s%s" % (HOST, uri)
    data = open(local_path, "rb").read()
    ctype = "image/jpeg" if key.lower().endswith((".jpg",".jpeg")) else "application/octet-stream"
    for a in range(tries):
        try:
            headers = {"Host": HOST, "Content-Type": ctype}
            auth = sign("put", uri, {"host": HOST})
            req = urllib.request.Request(url, data=data, method="PUT",
                    headers={"Host": HOST, "Content-Type": ctype,
                             "Authorization": auth, "Content-Length": str(len(data))})
            with urllib.request.urlopen(req, timeout=90) as r:
                if r.status in (200, 204): return True, len(data)
        except urllib.error.HTTPError as e:
            body = e.read()[:200].decode("utf-8", "ignore")
            if a == tries - 1: return False, "HTTP %d %s" % (e.code, body)
            time.sleep(2)
        except Exception as e:
            if a == tries - 1: return False, str(e)[:80]
            time.sleep(2)
    return False, "retries exhausted"

def main():
    if not SID or not SKEY:
        print("缺少 COS_SECRET_ID / COS_SECRET_KEY 环境变量"); sys.exit(1)
    src = sys.argv[1]; prefix = sys.argv[2].strip("/")
    limit = int(sys.argv[sys.argv.index("--limit")+1]) if "--limit" in sys.argv else None
    workers = int(sys.argv[sys.argv.index("--workers")+1]) if "--workers" in sys.argv else 8
    files = sorted([f for f in os.listdir(src) if f.lower().endswith(".jpg")],
                   key=lambda x: int(x.split(".")[0]) if x.split(".")[0].isdigit() else 0)
    if limit: files = files[:limit]
    print("准备上传 %d 个文件 -> cos://%s/%s/ (并发 %d)" % (len(files), BUCKET, prefix, workers))
    ok = fail = 0; fails = []
    def work(f):
        return f, put(os.path.join(src, f), "%s/%s" % (prefix, f))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, (f, (good, info)) in enumerate(ex.map(work, files), 1):
            if good: ok += 1
            else:
                fail += 1; fails.append((f, info))
                if fail <= 3: print("  失败 %s: %s" % (f, info))
            if i % 200 == 0:
                print("  %d/%d (ok=%d fail=%d)" % (i, len(files), ok, fail)); sys.stdout.flush()
    print("=== 完成: %d 成功, %d 失败 ===" % (ok, fail))
    if fails: print("失败样例:", fails[:5])

if __name__ == "__main__":
    main()
