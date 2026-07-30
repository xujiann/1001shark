#!/bin/bash
# 增量上线：图片下到哪就上线到哪。补完图后跑这一条命令即可。
#   用法: COS_SECRET_ID=xxx COS_SECRET_KEY=yyy bash sync_and_deploy.sh
set -e
cd "C:/Users/drxuj/OneDrive/claude/1001shark"

echo "== 1/5 从母版重建上线数据（只含已有图的物种）=="
python build_shipped.py

echo "== 2/5 目名繁转简（可选，缺 opencc 只警告不中断）=="
node convert_orders.js || echo "  ⚠ 繁转简失败，继续部署"

echo "== 3-4/5 图片已由 fetch_to_cos.py 直传 COS，本地无图，跳过上传 =="

echo "== 5/5 打缓存版本号 + 提交部署 =="
# 静态资源加 ?v=时间戳，否则老访客会一直用缓存的旧 css/js 看不到更新
V=$(date +%Y%m%d%H%M)
python - "$V" <<'PY'
import io, re, sys
v = sys.argv[1]
p = "index.html"; s = io.open(p, encoding="utf-8").read()
for f in ("style.css", "shark.js", "app.js"):
    s = re.sub(r'(href|src)="%s(\?v=\d+)?"' % re.escape(f),
               lambda m: '%s="%s?v=%s"' % (m.group(1), f, v), s)
io.open(p, "w", encoding="utf-8").write(s)
p = "app.js"; a = io.open(p, encoding="utf-8").read()
a = re.sub(r'fetch\("credits\.json(\?v=\d+)?"\)', 'fetch("credits.json?v=%s")' % v, a)
io.open(p, "w", encoding="utf-8").write(a)
print("  版本号 %s" % v)
PY

N=$(python -c "import json,re;t=open('shark.js',encoding='utf-8').read();print(len(json.loads(re.sub(r'/\*.*?\*/','',t[t.index('['):t.rindex(']')+1],flags=re.S))))")
git add -A
git -c user.name=cosmos1001 -c user.email=popstudy@gmail.com commit -q -m "Sync: $N shark species live" || echo "  (无变更)"
git push origin main | tail -1
echo ""
echo "完成：$N 种已上线 https://xujiann.github.io/1001shark/"
