"use strict";
(function () {
  const DATA = window.SHARK_DATA || [];

  // 图片基址：腾讯云 COS 南京区（国内直连，比 jsDelivr 快约 10 倍）。本地开发可改回 "images"
  const IMG_BASE = "https://pic-1302017848.cos.ap-nanjing.myqcloud.com/shark";

  // category metadata: label(zh/en), color var, representative emoji
  // 软骨鱼的天然三分结构（比主题分类更科学）：鲨类 / 鳐类 / 银鲛
  const CATS = {
    shark:    { zh:"鲨类",   en:"Sharks",    color:"var(--c-shark)",  emoji:"🦈" },
    ray:      { zh:"鳐类",   en:"Rays",      color:"var(--c-ray)",    emoji:"🐟" },
    chimaera: { zh:"银鲛",   en:"Chimaeras", color:"var(--c-chim)",   emoji:"👻" },
  };
  const CAT_ORDER = ["shark","ray","chimaera"];

  // per-category emoji pools for a little variety on cards
  const EMOJI = { shark:["🦈"], ray:["🐟","🥏"], chimaera:["👻"] };
  // IUCN 濒危等级（世界自然保护联盟标准代码）
  const IUCN = {
    EX:{zh:"灭绝",en:"Extinct"},          EW:{zh:"野外灭绝",en:"Extinct in the Wild"},
    CR:{zh:"极危",en:"Critically Endangered"}, EN:{zh:"濒危",en:"Endangered"},
    VU:{zh:"易危",en:"Vulnerable"},        NT:{zh:"近危",en:"Near Threatened"},
    LC:{zh:"无危",en:"Least Concern"},     DD:{zh:"数据缺乏",en:"Data Deficient"},
  };
  const THREATENED = ["NT","VU","EN","CR","EW","EX"];   // 受威胁及以上

  function emojiFor(f){ const p = EMOJI[f.cat]||["🐟"]; return p[f.id % p.length]; }

  // ---- i18n ----
  const I18N = {
    zh:{ sub:"种软骨鱼", subtitle:"鲨、鳐、银鲛 —— 消失最快的一类鱼", species:"种", families:"科",
         search:"搜索名称、拼音、学名、目、科…", allFam:"全部科", all:"全部", orders:"目", featured:"精选", lIucn:"保护级别", threatened:"受威胁", allIucn:"全部保护级别",
         sortDefault:"默认", sortName:"按名称", sortOrder:"按目", sortFamily:"按科", random:"随机一条",
         noresults:"未找到符合条件的软骨鱼", reset:"重置筛选",
         lOrder:"目", lFamily:"科", lHabitat:"栖息水域", lSize:"最大体长", allOrd:"全部目",
         prev:"← 上一条", next:"下一条 →",
         footer:"554 种软骨鱼 · 鲨 · 鳐 · 银鲛 · 全球现存种的 43%", langbtn:"EN",
         share:"复制链接", copied:"已复制 ✓", photo:"图片：", dist:"全球分布", records:"条观测记录", distSrc:"数据 GBIF",
         byFamily:"按科浏览", allFamiliesTitle:"按科浏览", famCount:"种", backToFamilies:"← 所有科" },
    en:{ sub:" Cartilaginous Fishes", subtitle:"Sharks, rays and chimaeras — the fastest-vanishing fishes", species:"species", families:"families",
         search:"Search name, sci. name, order, family…", allFam:"All families", all:"All", orders:"orders", featured:"Featured", lIucn:"IUCN status", threatened:"Threatened", allIucn:"All IUCN status",
         sortDefault:"Default", sortName:"By name", sortOrder:"By order", sortFamily:"By family", random:"Random",
         noresults:"No species match your filters", reset:"Reset filters",
         lOrder:"Order", lFamily:"Family", lHabitat:"Habitat", lSize:"Max length", allOrd:"All orders",
         prev:"← Prev", next:"Next →",
         footer:"554 cartilaginous fishes · sharks · rays · chimaeras · 43% of all living species", langbtn:"中",
         share:"Copy link", copied:"Copied ✓", photo:"Photo: ", dist:"Global distribution", records:"records", distSrc:"via GBIF",
         byFamily:"By family", allFamiliesTitle:"Browse by family", famCount:"species", backToFamilies:"← All families" },
  };
  let lang = localStorage.getItem("shark-lang") || "zh";

  // ---- state ----
  let activeCat = "";     // "" = all
  let famFilter = "";
  let ordFilter = "";
  let iucnFilter = "";
  let sort = "default";
  let query = "";
  let filtered = [];
  // 1001 条全部有图，直接渲染 <img>，加载失败时由 error 监听移除、露出 emoji 占位。
  // 图片署名（Commons 文件名）按需懒加载，不进首屏关键路径。
  let CREDITS = null, creditsPromise = null;
  function loadCredits(){
    if(CREDITS) return Promise.resolve(CREDITS);
    if(!creditsPromise){
      creditsPromise = fetch("credits.json?v=202607312319").then(r=>r.ok?r.json():{})
        .then(c=>{ CREDITS = c||{}; return CREDITS; })
        .catch(()=>{ CREDITS = {}; return CREDITS; });
    }
    return creditsPromise;
  }

  // ---- elements ----
  const $ = id => document.getElementById(id);
  const gallery = $("gallery"), catTabs = $("cat-tabs"), famSel = $("family-filter"),
        sortSel = $("sort-filter"), searchIn = $("search"), clearBtn = $("clear-search"),
        ordSel = $("order-filter"), iucnSel = $("iucn-filter"),
        noResults = $("no-results");

  // 73% 的物种没有英文俗名（很多冷门鱼学界就没起），英文模式退回学名；
  // 否则模板插值会把 undefined 直接渲染成 "undefined" 字样。
  function nameOf(f){ return lang==="zh" ? f.name : (f.name_en || f.sci); }
  function subOf(f){ return (lang==="zh" ? f.name_en : f.name) || ""; }

  // ---- build family dropdown ----
  function buildFamilies(){
    const fams = [...new Set(DATA.map(f=>lang==="zh"?f.family:f.family_en).filter(Boolean))].sort((a,b)=>a.localeCompare(b));
    const cur = famFilter;
    famSel.innerHTML = `<option value="">${I18N[lang].allFam}</option>` +
      fams.map(fm=>`<option value="${fm}">${fm}</option>`).join("");
    famSel.value = cur;
  }

  // ---- 目筛选（76 个目，比 442 个科更粗粒度、更好认）----
  function buildOrders(){
    const cnt = new Map();
    DATA.forEach(f=>{ if(f.order) cnt.set(f.order,(cnt.get(f.order)||0)+1); });
    const list=[...cnt.entries()].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0],"zh"));
    const cur=ordFilter;
    ordSel.innerHTML=`<option value="">${I18N[lang].allOrd}</option>`+
      list.map(([o,n])=>`<option value="${o}">${o} (${n})</option>`).join("");
    ordSel.value=cur;
  }

  // ---- 保护级别筛选 ----
  function buildIucn(){
    const cnt=new Map();
    DATA.forEach(f=>{ if(f.iucn) cnt.set(f.iucn,(cnt.get(f.iucn)||0)+1); });
    if(!cnt.size){ iucnSel.style.display="none"; return; }
    iucnSel.style.display="";
    const order=["EX","EW","CR","EN","VU","NT","LC","DD"];
    const th=DATA.filter(f=>THREATENED.includes(f.iucn)).length;
    const cur=iucnFilter;
    iucnSel.innerHTML=`<option value="">${I18N[lang].allIucn}</option>`+
      (th?`<option value="__threat">⚠ ${I18N[lang].threatened} (${th})</option>`:"")+
      order.filter(k=>cnt.get(k)).map(k=>
        `<option value="${k}">${lang==="zh"?IUCN[k].zh:IUCN[k].en} (${cnt.get(k)})</option>`).join("");
    iucnSel.value=cur;
  }

  // ---- category tabs ----
  function buildTabs(){
    const counts = {}; DATA.forEach(f=>counts[f.cat]=(counts[f.cat]||0)+1);
    let html = `<button class="cat-tab ${activeCat===""?"active":""}" data-cat="" style="--tabc:var(--accent)">`+
               `<span class="dot"></span>${I18N[lang].all} <span class="cnt">${DATA.length}</span></button>`;
    html += CAT_ORDER.filter(c=>counts[c]).map(c=>{
      const m=CATS[c];
      return `<button class="cat-tab ${activeCat===c?"active":""}" data-cat="${c}" style="--tabc:${m.color}">`+
             `<span class="dot"></span>${lang==="zh"?m.zh:m.en} <span class="cnt">${counts[c]}</span></button>`;
    }).join("");
    catTabs.innerHTML = html;
    catTabs.querySelectorAll(".cat-tab").forEach(t=>t.onclick=()=>{
      activeCat=t.dataset.cat; buildTabs(); apply();
    });
  }

  // ---- 按科浏览：227 个科用下拉框太难逛，做成可视索引 ----
  let famView = false;
  let FAMS = null;   // [{zh,la,count,repId}]，按数量降序

  function buildFamData(){
    if(FAMS) return FAMS;
    const map = new Map();
    DATA.forEach(f=>{
      if(!f.family) return;
      let e = map.get(f.family);
      if(!e){ e = {zh:f.family, la:f.family_en||"", count:0, repId:f.id}; map.set(f.family, e); }
      e.count++;
    });
    FAMS = [...map.values()].sort((a,b)=> b.count-a.count || a.zh.localeCompare(b.zh,"zh"));
    return FAMS;
  }

  function renderFamilyIndex(){
    const el = $("family-index");
    el.innerHTML = buildFamData().map(fm=>
      `<button class="fam-card" data-fam="${fm.zh.replace(/"/g,"&quot;")}">`+
        `<img class="fam-thumb" src="${IMG_BASE}/${fm.repId}.jpg" alt="" loading="lazy">`+
        `<span class="fam-body">`+
          `<span class="fam-zh">${lang==="zh"?fm.zh:(fm.la||fm.zh)}</span>`+
          `<span class="fam-la">${lang==="zh"?fm.la:fm.zh}</span>`+
          `<span class="fam-cnt">${fm.count} ${I18N[lang].famCount}</span>`+
        `</span></button>`
    ).join("");
  }

  function showFamilyIndex(){
    famView = true; famFilter = ""; famSel.value = "";
    renderFamilyIndex();
    $("family-index").style.display = "grid";
    $("family-header").style.display = "none";
    gallery.style.display = "none";
    noResults.style.display = "none";
    if(sentinel) sentinel.style.display = "none";
    $("family-view-btn").classList.add("active");
  }

  function hideFamilyIndex(){
    famView = false;
    $("family-index").style.display = "none";
    gallery.style.display = "";
    if(sentinel) sentinel.style.display = "";
    $("family-view-btn").classList.remove("active");
  }

  function openFamily(fam){
    const fm = buildFamData().find(x=>x.zh===fam);
    hideFamilyIndex();
    famFilter = lang==="zh" ? fam : (fm && fm.la ? fm.la : fam);
    famSel.value = famFilter;
    const h = $("family-header");
    h.innerHTML = `<button class="fh-back" id="fh-back">${I18N[lang].backToFamilies}</button>`+
      `<h2>${lang==="zh"?fm.zh:(fm.la||fm.zh)}</h2>`+
      `<span class="fh-la">${lang==="zh"?fm.la:fm.zh}</span>`+
      `<span class="fh-cnt">${fm.count} ${I18N[lang].famCount}</span>`;
    h.style.display = "flex";
    $("fh-back").onclick = showFamilyIndex;
    apply();
    window.scrollTo({top:0, behavior: reduceMotion ? "auto" : "smooth"});
  }

  // ---- filtering ----
  function apply(){
    const q = query.trim().toLowerCase();
    filtered = DATA.filter(f=>{
      if(activeCat && f.cat!==activeCat) return false;
      if(famFilter && (lang==="zh"?f.family:f.family_en)!==famFilter) return false;
      if(ordFilter && f.order!==ordFilter) return false;
      if(iucnFilter==="__threat"){ if(!THREATENED.includes(f.iucn)) return false; }
      else if(iucnFilter && f.iucn!==iucnFilter) return false;
      if(q){
        const hay = [f.name,f.name_en,f.sci,f.family,f.family_en,f.habitat,f.habitat_en,f.order,f.order_en,f.py]
          .filter(Boolean).join(" ").toLowerCase();
        if(!hay.includes(q)) return false;
      }
      return true;
    });
    if(sort==="name") filtered.sort((a,b)=>nameOf(a).localeCompare(nameOf(b),lang==="zh"?"zh":"en"));
    else if(sort==="order") filtered.sort((a,b)=>(a.order||"￿").localeCompare(b.order||"￿","zh") || a.id-b.id);
    else if(sort==="family") filtered.sort((a,b)=>(lang==="zh"?a.family:a.family_en).localeCompare(lang==="zh"?b.family:b.family_en,lang==="zh"?"zh":"en"));
    else filtered.sort((a,b)=>a.id-b.id);
    render();
  }

  // 增量渲染：1001 条太多，先渲一页，滚动到底再续（配合懒加载图片，保持流畅）
  const PAGE = 120;
  let shownCount = 0, sentinel = null, io = null;

  function cardHTML(f){
    const m=CATS[f.cat];
    const photo = `<img class="card-photo" src="${IMG_BASE}/${f.id}.jpg" alt="" loading="lazy">`;
    return `<article class="card" data-id="${f.id}" style="--cardc:${m.color}" tabindex="0" role="button" aria-label="${nameOf(f)}">`+
      `<div class="card-img"><span class="card-cat">${lang==="zh"?m.zh:m.en}</span>`+
      `<span class="card-emoji">${emojiFor(f)}</span>${photo}`+
      (f.iucn?`<span class="iucn iucn-${f.iucn}" title="${IUCN[f.iucn]?(lang==="zh"?IUCN[f.iucn].zh:IUCN[f.iucn].en):f.iucn}">${f.iucn}</span>`:"")+`</div>`+
      `<div class="card-body">`+
        `<div class="card-name">${nameOf(f)}</div>`+
        `<div class="card-en">${subOf(f)}</div>`+
        `<div class="card-sci">${nameOf(f)===f.sci ? "" : f.sci}</div>`+
        `<div class="card-meta"><span>${(lang==="zh"?f.family:f.family_en)||""}</span><span>${f.size||""}</span></div>`+
      `</div></article>`;
  }

  function renderMore(){
    const next = filtered.slice(shownCount, shownCount + PAGE);
    if(!next.length) return;
    gallery.insertAdjacentHTML("beforeend", next.map(cardHTML).join(""));
    shownCount += next.length;
  }

  function render(){
    gallery.innerHTML = "";
    shownCount = 0;
    if(!filtered.length){ noResults.style.display="block"; }
    else{ noResults.style.display="none"; renderMore(); }
    if(!sentinel){
      sentinel = document.createElement("div");
      sentinel.style.height = "1px";
      gallery.after(sentinel);
      io = new IntersectionObserver(es=>{ if(es[0].isIntersecting) renderMore(); }, {rootMargin:"800px"});
      io.observe(sentinel);
    }
    $("shown-count").textContent = filtered.length;
  }

  // 图片署名：链回 Wikimedia Commons 原始文件页（CC 图片应署名）
  function renderCredit(id){
    const el = $("modal-credit"); if(!el) return;
    const name = CREDITS && CREDITS[id];
    if(!name){ el.innerHTML = ""; return; }
    const disp = decodeURIComponent(name).replace(/_/g," ");
    el.innerHTML = I18N[lang].photo +
      `<a href="https://commons.wikimedia.org/wiki/File:${encodeURIComponent(name)}" target="_blank" rel="noopener">${disp}</a>` +
      " · Wikimedia Commons";
  }

  // ---- GBIF 全球分布图 ----
  const GBIF_BASE = "https://tile.gbif.org/4326/omt/0/{x}/0@1x.png?style=gbif-light";
  const GBIF_PTS  = "https://api.gbif.org/v2/map/occurrence/density/0/{x}/0@1x.png" +
                    "?srs=EPSG%3A4326&style=classic.point&taxonKey=";
  let GBIF = null, gbifPromise = null;
  function loadGbif(){
    if(GBIF) return Promise.resolve(GBIF);
    if(!gbifPromise) gbifPromise = fetch("gbif.json").then(r=>r.ok?r.json():{})
      .then(g=>{ GBIF = g||{}; return GBIF; }).catch(()=>{ GBIF={}; return GBIF; });
    return gbifPromise;
  }
  function renderDist(f){
    const wrap = $("dist-wrap"); if(!wrap) return;
    const g = GBIF && GBIF[f.sci];
    if(!g || !g.k){ wrap.style.display="none"; return; }
    wrap.style.display="";
    $("t-dist").textContent = I18N[lang].dist;
    $("dist-n").innerHTML = g.n ? `<span class="dist-n">${g.n.toLocaleString()}</span> ${I18N[lang].records} · ${I18N[lang].distSrc}` : I18N[lang].distSrc;
    $("dist-map").innerHTML = [0,1].map(x=>
      `<img class="dm-base ${x?"r":"l"}" src="${GBIF_BASE.replace("{x}",x)}" alt="" loading="lazy">`).join("")+
      [0,1].map(x=>
      `<img class="dm-pts ${x?"r":"l"}" src="${GBIF_PTS.replace("{x}",x)+g.k}" alt="" loading="lazy">`).join("");
  }

  // ---- modal ----
  let modalId = null, modalOpener = null;
  function openModal(id){
    const f = DATA.find(x=>x.id===id); if(!f) return;
    if(!$("modal").classList.contains("open")) modalOpener = document.activeElement;
    modalId = id; const m=CATS[f.cat];
    const box = document.querySelector(".modal-box");
    box.style.setProperty("--cardc", m.color);
    $("modal-img").innerHTML = `<img src="${IMG_BASE}/${f.id}.jpg" alt="${nameOf(f)}">`;
    $("modal-img").firstChild.onerror = function(){
      $("modal-img").innerHTML=""; $("modal-img").textContent = emojiFor(f);
    };
    $("modal-credit").innerHTML = "";
    loadCredits().then(()=>{ if(modalId===id) renderCredit(id); });
    $("dist-wrap").style.display="none";
    loadGbif().then(()=>{ if(modalId===id) renderDist(f); });
    $("modal-cat").textContent = lang==="zh"?m.zh:m.en;
    $("modal-name").textContent = nameOf(f);
    $("modal-en").textContent = subOf(f);
    $("modal-sci").textContent = f.sci;
    const iu=$("modal-iucn");
    if(f.iucn && IUCN[f.iucn]){
      iu.textContent=(lang==="zh"?IUCN[f.iucn].zh:IUCN[f.iucn].en)+" ("+f.iucn+")";
      iu.className="modal-iucn iucn-"+f.iucn; iu.style.display="";
    } else { iu.style.display="none"; }
    $("modal-order").textContent = (lang==="zh"?(f.order||f.order_en):(f.order_en||f.order)) || "—";
    $("modal-family").textContent = (lang==="zh"?f.family:f.family_en) || "—";
    $("modal-habitat").textContent = (lang==="zh"?f.habitat:f.habitat_en) || "—";
    $("modal-size").textContent = f.size || "—";
    const idx = filtered.findIndex(x=>x.id===id);
    $("modal-num").textContent = idx>=0 ? `${idx+1} / ${filtered.length}` : "";
    $("modal-share").textContent = "⎘ " + I18N[lang].share;
    const wasOpen = $("modal").classList.contains("open");
    $("modal").classList.add("open");
    if(!wasOpen) $("modal-close").focus();   // 打开时焦点移到关闭按钮（可访问性）
    try{ history.replaceState(null,"", "#f"+id); }catch(e){}
    // 预加载上/下一条图片，翻页更顺
    if(idx>=0){
      [filtered[idx-1], filtered[(idx+1)%filtered.length]].forEach(nf=>{
        if(nf && hasImg(nf.id)){ const im=new Image(); im.src=`${IMG_BASE}/${nf.id}.jpg`; }
      });
    }
  }
  function closeModal(){
    $("modal").classList.remove("open"); modalId=null;
    try{ history.replaceState(null,"", location.pathname+location.search); }catch(e){}
    if(modalOpener && modalOpener.focus){ modalOpener.focus(); modalOpener=null; }   // 焦点还给来源卡片
  }
  function step(d){
    const idx = filtered.findIndex(x=>x.id===modalId);
    if(idx<0) return;
    const n = (idx+d+filtered.length)%filtered.length;
    openModal(filtered[n].id);
  }

  // ---- language ----
  function applyLang(){
    const t = I18N[lang];
    // 已选中的科要跟着语言换名，否则筛选值对不上（中文科名 vs 拉丁科名）→ 结果为 0
    if(famFilter){
      const fm = buildFamData().find(x=>x.zh===famFilter || x.la===famFilter);
      if(fm){
        famFilter = lang==="zh" ? fm.zh : (fm.la || fm.zh);
        const h = $("family-header");
        if(h.style.display !== "none"){
          h.innerHTML = `<button class="fh-back" id="fh-back">${t.backToFamilies}</button>`+
            `<h2>${lang==="zh"?fm.zh:(fm.la||fm.zh)}</h2>`+
            `<span class="fh-la">${lang==="zh"?fm.la:fm.zh}</span>`+
            `<span class="fh-cnt">${fm.count} ${t.famCount}</span>`;
          $("fh-back").onclick = showFamilyIndex;
        }
      }
    }
    document.documentElement.lang = lang==="zh"?"zh-CN":"en";
    $("t-sub").textContent = t.sub;
    $("t-subtitle").textContent = t.subtitle;
    $("t-species").textContent = t.species;
    $("t-families").textContent = t.families;
    $("t-orders").textContent = t.orders;
    searchIn.placeholder = t.search;
    sortSel.options[0].text=t.sortDefault; sortSel.options[1].text=t.sortName; sortSel.options[2].text=t.sortOrder; sortSel.options[3].text=t.sortFamily;
    $("random-btn").textContent = t.random;
    document.getElementById("t-noresults").textContent = t.noresults;
    $("reset-btn").textContent = t.reset;
    $("l-iucn").textContent=t.lIucn; $("l-order").textContent=t.lOrder; $("l-family").textContent=t.lFamily; $("l-habitat").textContent=t.lHabitat; $("l-size").textContent=t.lSize;
    $("prev-fish").textContent=t.prev; $("next-fish").textContent=t.next;
    $("modal-share").textContent="⎘ "+t.share;
    $("family-view-btn").textContent=t.byFamily;
    if(famView) renderFamilyIndex();
    document.getElementById("t-footer").textContent=t.footer;
    $("lang-toggle").textContent=t.langbtn;
    buildOrders(); buildIucn(); buildFamilies(); buildTabs(); apply();
  }

  // ---- events ----
  gallery.addEventListener("click",e=>{ const c=e.target.closest(".card"); if(c) openModal(+c.dataset.id); });
  gallery.addEventListener("keydown",e=>{
    if(e.key!=="Enter"&&e.key!==" ") return;
    const c=e.target.closest(".card"); if(c){ e.preventDefault(); openModal(+c.dataset.id); }
  });
  searchIn.addEventListener("input",()=>{ query=searchIn.value; clearBtn.style.display=query?"block":"none";
    if(famView && query){ hideFamilyIndex(); $("family-header").style.display="none"; famFilter=""; famSel.value=""; }
    apply(); });
  clearBtn.onclick=()=>{ searchIn.value=""; query=""; clearBtn.style.display="none"; apply(); };
  iucnSel.onchange=()=>{ iucnFilter=iucnSel.value; if(famView) hideFamilyIndex(); $("family-header").style.display="none"; apply(); };
  ordSel.onchange=()=>{ ordFilter=ordSel.value; if(famView) hideFamilyIndex(); $("family-header").style.display="none"; apply(); };
  famSel.onchange=()=>{ famFilter=famSel.value; if(famView) hideFamilyIndex(); $("family-header").style.display="none"; apply(); };
  $("family-view-btn").onclick=()=>{ famView ? (hideFamilyIndex(), $("family-header").style.display="none", apply()) : showFamilyIndex(); };
  $("family-index").addEventListener("click", e=>{
    const c = e.target.closest(".fam-card"); if(c) openFamily(c.dataset.fam);
  });
  sortSel.onchange=()=>{ sort=sortSel.value; apply(); };
  $("random-btn").onclick=()=>{ if(filtered.length) openModal(filtered[Math.floor(Math.random()*filtered.length)].id); };
  $("modal-close").onclick=closeModal;
  $("modal").onclick=e=>{ if(e.target===$("modal")) closeModal(); };
  $("prev-fish").onclick=()=>step(-1);
  $("next-fish").onclick=()=>step(1);
  $("modal-share").onclick=()=>{
    if(!modalId) return;
    const link = location.origin + location.pathname + "#f" + modalId;
    const done=()=>{ const b=$("modal-share"); b.textContent="⎘ "+I18N[lang].copied;
      setTimeout(()=>{ b.textContent="⎘ "+I18N[lang].share; }, 1500); };
    if(navigator.clipboard&&navigator.clipboard.writeText){ navigator.clipboard.writeText(link).then(done,done); }
    else{ const t=document.createElement("textarea"); t.value=link; document.body.appendChild(t); t.select();
      try{document.execCommand("copy");}catch(e){} t.remove(); done(); }
  };
  $("reset-btn").onclick=()=>{ activeCat="";famFilter="";ordFilter="";ordSel.value="";iucnFilter="";iucnSel.value="";query="";searchIn.value="";clearBtn.style.display="none";
    if(famView) hideFamilyIndex(); $("family-header").style.display="none";
    buildTabs();buildFamilies();apply(); };
  $("lang-toggle").onclick=()=>{ lang=lang==="zh"?"en":"zh"; localStorage.setItem("shark-lang",lang); applyLang(); };
  document.addEventListener("keydown",e=>{
    const modalOpen = $("modal").classList.contains("open");
    if(e.key==="Escape"){ closeModal(); return; }
    if(modalOpen){
      if(e.key==="ArrowLeft") step(-1);
      else if(e.key==="ArrowRight") step(1);
      else if(e.key==="Tab"){   // 焦点困在弹窗内（可访问性）
        const foc=[...document.querySelectorAll(".modal-box button")].filter(b=>b.offsetParent!==null);
        if(foc.length){
          const first=foc[0], last=foc[foc.length-1];
          if(e.shiftKey && document.activeElement===first){ e.preventDefault(); last.focus(); }
          else if(!e.shiftKey && document.activeElement===last){ e.preventDefault(); first.focus(); }
        }
      }
      return;
    }
    if(e.key==="/"&&document.activeElement!==searchIn){ e.preventDefault(); searchIn.focus(); }
    else if(e.key.toLowerCase()==="r"&&document.activeElement!==searchIn){ $("random-btn").click(); }
  });

  // 从 URL 恢复状态：?q= 预填搜索；#f<id> 直接打开某条鱼（可分享的深链）
  function applyUrlState(){
    const params = new URLSearchParams(location.search);
    const q = params.get("q");
    if(q){ searchIn.value=q; query=q; clearBtn.style.display="block"; apply(); }
    const m = location.hash.match(/^#f(\d+)$/);
    if(m){ const id=+m[1]; if(DATA.some(f=>f.id===id)) openModal(id); }
  }

  // 回到顶部
  const toTop = $("to-top");
  window.addEventListener("scroll", ()=>{ toTop.classList.toggle("show", window.scrollY > 600); }, {passive:true});
  const reduceMotion = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  toTop.onclick = ()=> window.scrollTo({top:0, behavior: reduceMotion ? "auto" : "smooth"});

  // 卡片图加载失败时移除，露出 emoji 占位（error 不冒泡，用捕获）
  gallery.addEventListener("error", e=>{
    if(e.target && e.target.classList && e.target.classList.contains("card-photo")) e.target.remove();
  }, true);

  // ---- init ----
  $("family-count").textContent = new Set(DATA.map(f=>f.family).filter(Boolean)).size;
  $("order-count").textContent = new Set(DATA.map(f=>f.order).filter(Boolean)).size;
  applyLang();
  applyUrlState();
})();
