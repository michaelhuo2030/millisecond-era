/* millisecond-era · shared site navigation + site-wide EN/中 language toggle
 * One line to include on any page:  <script src="{relative}/site-nav.js"></script>
 *
 * Base path: auto-detected so the SAME file works on localhost root AND GitHub Pages
 *   (/millisecond-era/...). Include with a RELATIVE src per page depth.
 *
 * Language: ONE global toggle, default English. State in localStorage('msEraLang')
 *   — the SAME key the per-page civ-demo i18n uses, so a choice persists site-wide.
 *   On change it: (1) sets <html data-lang>, which drives CSS for pages that mark
 *   bilingual text with .lang-en / .lang-zh spans; (2) calls the page's own
 *   setLang(l) if present (the civ demos' dictionary i18n). Both stay in sync.
 *
 * To make a page bilingual: wrap display text as
 *     <span class="lang-en">English</span><span class="lang-zh">中文</span>
 *   (use class="lang-en"/"lang-zh" on any element). No per-page JS needed.
 */
(function () {
  if (window.__mseNavLoaded) return;
  window.__mseNavLoaded = true;

  // ---- base path -----------------------------------------------------------
  var m = location.pathname.match(/^(.*?\/millisecond-era\/)/);
  var BASE = m ? m[1] : '/';

  // ---- language state ------------------------------------------------------
  function readLang() {
    try {
      var s = localStorage.getItem('msEraLang');
      if (s === 'en' || s === 'zh') return s;
    } catch (e) {}
    return 'en'; // default English (students read English)
  }
  var LANG = readLang();

  function applyLang(l) {
    LANG = l;
    try { localStorage.setItem('msEraLang', l); } catch (e) {}
    document.documentElement.setAttribute('data-lang', l);
    document.documentElement.lang = (l === 'zh' ? 'zh' : 'en');
    // bridge to per-page dictionary i18n (civ demos define a global setLang)
    if (typeof window.setLang === 'function' && !window.__mseInSetLang) {
      try { window.__mseInSetLang = true; window.setLang(l); } finally { window.__mseInSetLang = false; }
    }
    var en = document.getElementById('mse-lang-en'), zh = document.getElementById('mse-lang-zh');
    if (en) en.classList.toggle('on', l === 'en');
    if (zh) zh.classList.toggle('on', l === 'zh');
    try { window.dispatchEvent(new CustomEvent('mse:lang', { detail: l })); } catch (e) {}
  }
  // expose a global so any page can call it too
  window.mseSetLang = applyLang;

  // ---- nav model (bilingual labels) ---------------------------------------
  var LINKS = [
    { href: '',                              en: '🏠 Millisecond Era', zh: '🏠 毫秒纪元', home: true },
    { href: 'learn/demos/index.html',        en: '⚡ Speed',     zh: '⚡ 速度' },
    { href: 'learn/reram-cim-visual.html',   en: '🧱 The Chip',  zh: '🧱 看芯片' },
    { href: 'learn/hdc-101.html',            en: '🧠 How',       zh: '🧠 原理' },
    { href: 'learn/civilization/index.html', en: '🛡️ Apps',      zh: '🛡️ 应用' },
    { href: 'learn/speed-trial.html',        en: '📊 Proof',     zh: '📊 自己验证' },
    { href: 'https://github.com/michaelhuo2030/millisecond-era', en: '⌥ Source', zh: '⌥ 源码', ext: true }
  ];
  function resolve(l) { return l.ext ? l.href : (BASE + l.href); }
  function isActive(l) {
    if (l.ext) return false;
    if (l.home) return location.pathname === BASE || /\/index\.html?$/.test(location.pathname) && location.pathname.replace(/index\.html?$/, '') === BASE;
    return location.pathname.indexOf(BASE + l.href) === 0;
  }

  // ---- styles --------------------------------------------------------------
  var css = '' +
    // language visibility (drives every page that uses .lang-en / .lang-zh)
    'html[data-lang="en"] .lang-zh{display:none!important}' +
    'html[data-lang="zh"] .lang-en{display:none!important}' +
    'html:not([data-lang]) .lang-zh{display:none!important}' +   // default EN before JS
    // nav bar
    '#mse-nav{position:fixed;top:0;left:0;right:0;z-index:2147483000;' +
      'display:flex;align-items:center;gap:2px;flex-wrap:nowrap;overflow-x:auto;' +
      'background:rgba(8,10,16,.86);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);' +
      'border-bottom:1px solid #222634;padding:0 10px;height:44px;' +
      'font:600 13px/1 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif;box-shadow:0 2px 12px #0006}' +
    '#mse-nav::-webkit-scrollbar{display:none}' +
    '#mse-nav a{flex:0 0 auto;color:#aeb6c6;text-decoration:none;padding:7px 11px;border-radius:9px;white-space:nowrap;transition:background .12s,color .12s}' +
    '#mse-nav a:hover{color:#fff;background:#1b2030}' +
    '#mse-nav a.mse-home{color:#7aa9ff;font-weight:800}' +
    '#mse-nav a.mse-active{color:#0a0d12;background:#7aa9ff}' +
    '#mse-nav .mse-sp{flex:1 1 auto}' +
    '#mse-nav .mse-ext{color:#717a8c}' +
    // language segmented control
    '#mse-lang{flex:0 0 auto;display:inline-flex;margin-left:6px;border:1px solid #2d3346;border-radius:8px;overflow:hidden}' +
    '#mse-lang button{appearance:none;border:0;background:transparent;color:#9aa3b5;font:700 12px/1 inherit;padding:7px 9px;cursor:pointer}' +
    '#mse-lang button.on{background:#7aa9ff;color:#0a0d12}' +
    '#mse-nav-spacer{height:44px}' +
    '@media print{#mse-nav,#mse-nav-spacer{display:none}}';
  var st = document.createElement('style');
  st.textContent = css;
  (document.head || document.documentElement).appendChild(st);
  // set lang attribute ASAP to minimise flash
  document.documentElement.setAttribute('data-lang', LANG);
  document.documentElement.lang = (LANG === 'zh' ? 'zh' : 'en');

  // ---- build bar -----------------------------------------------------------
  function build() {
    if (document.getElementById('mse-nav')) return;
    var nav = document.createElement('nav');
    nav.id = 'mse-nav';
    var html = '';
    LINKS.forEach(function (l) {
      var cls = [];
      if (l.home) cls.push('mse-home');
      if (l.ext) cls.push('mse-ext');
      if (isActive(l)) cls.push('mse-active');
      var attrs = l.ext ? ' target="_blank" rel="noopener"' : '';
      var label = '<span class="lang-en">' + l.en + '</span><span class="lang-zh">' + l.zh + '</span>';
      html += '<a href="' + resolve(l) + '"' + attrs + (cls.length ? ' class="' + cls.join(' ') + '"' : '') + '>' + label + '</a>';
      if (l.home) html += '<span class="mse-sp" aria-hidden="true"></span>';
    });
    html += '<span id="mse-lang"><button id="mse-lang-en" type="button">EN</button><button id="mse-lang-zh" type="button">中</button></span>';
    nav.innerHTML = html;

    var spacer = document.createElement('div');
    spacer.id = 'mse-nav-spacer';
    document.body.insertBefore(spacer, document.body.firstChild);
    document.body.insertBefore(nav, document.body.firstChild);

    document.getElementById('mse-lang-en').addEventListener('click', function () { applyLang('en'); });
    document.getElementById('mse-lang-zh').addEventListener('click', function () { applyLang('zh'); });
    applyLang(LANG); // sync buttons + bridge to page i18n
  }

  if (document.body) build();
  else document.addEventListener('DOMContentLoaded', build);
})();
