/* millisecond-era · shared site navigation
 * One line to include on any page:  <script src="{BASE}site-nav.js"></script>
 * Auto-detects base path so the SAME file works on:
 *   - local server at repo root   (http://localhost:8792/learn/demos/reflex.html  -> BASE "/")
 *   - GitHub Pages project site   (https://michaelhuo2030.github.io/millisecond-era/... -> BASE "/millisecond-era/")
 * Injects a slim sticky top bar + a spacer so it never overlaps page content,
 * regardless of the page's own CSS. Pure vanilla JS, zero dependencies.
 */
(function () {
  if (window.__mseNavLoaded) return;
  window.__mseNavLoaded = true;

  // --- base path detection -------------------------------------------------
  var m = location.pathname.match(/^(.*?\/millisecond-era\/)/);
  var BASE = m ? m[1] : '/';
  var here = location.pathname.replace(/index\.html?$/, '');

  // --- nav model -----------------------------------------------------------
  var LINKS = [
    { href: '',                               label: '🏠 毫秒纪元', home: true },
    { href: 'learn/demos/index.html',         label: '⚡ 速度' },
    { href: 'learn/reram-cim-visual.html',    label: '🧱 看芯片' },
    { href: 'learn/hdc-101.html',             label: '🧠 原理' },
    { href: 'learn/civilization/index.html',  label: '🛡️ 应用' },
    { href: 'learn/speed-trial.html',         label: '📊 自己验证' },
    { href: 'https://github.com/michaelhuo2030/millisecond-era', label: '⌥ 源码', ext: true }
  ];

  function resolve(l) { return l.ext ? l.href : (BASE + l.href); }
  function isActive(l) {
    if (l.ext) return false;
    var target = (BASE + l.href).replace(/index\.html?$/, '');
    if (l.home) return here === BASE || here === BASE + 'index.html' || location.pathname === BASE;
    return location.pathname.indexOf(BASE + l.href) === 0 || here === target;
  }

  // --- styles --------------------------------------------------------------
  var css = '' +
    '#mse-nav{position:fixed;top:0;left:0;right:0;z-index:2147483000;' +
      'display:flex;align-items:center;gap:2px;flex-wrap:nowrap;overflow-x:auto;' +
      'background:rgba(8,10,16,.86);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);' +
      'border-bottom:1px solid #222634;padding:0 10px;height:44px;' +
      'font:600 13px/1 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif;' +
      'box-shadow:0 2px 12px #0006}' +
    '#mse-nav::-webkit-scrollbar{display:none}' +
    '#mse-nav a{flex:0 0 auto;color:#aeb6c6;text-decoration:none;padding:7px 11px;border-radius:9px;' +
      'white-space:nowrap;transition:background .12s,color .12s}' +
    '#mse-nav a:hover{color:#fff;background:#1b2030}' +
    '#mse-nav a.mse-home{color:#7aa9ff;font-weight:800}' +
    '#mse-nav a.mse-active{color:#0a0d12;background:#7aa9ff}' +
    '#mse-nav .mse-sp{flex:1 1 auto}' +
    '#mse-nav .mse-ext{color:#717a8c}' +
    '#mse-nav-spacer{height:44px}' +
    '@media print{#mse-nav,#mse-nav-spacer{display:none}}';
  var st = document.createElement('style');
  st.textContent = css;
  document.head.appendChild(st);

  // --- bar -----------------------------------------------------------------
  function build() {
    if (document.getElementById('mse-nav')) return;
    var nav = document.createElement('nav');
    nav.id = 'mse-nav';
    var html = '';
    LINKS.forEach(function (l, i) {
      var cls = [];
      if (l.home) cls.push('mse-home');
      if (l.ext) cls.push('mse-ext');
      if (isActive(l)) cls.push('mse-active');
      var attrs = l.ext ? ' target="_blank" rel="noopener"' : '';
      html += '<a href="' + resolve(l) + '"' + attrs + (cls.length ? ' class="' + cls.join(' ') + '"' : '') + '>' + l.label + '</a>';
      if (l.home) html += '<span class="mse-sp" aria-hidden="true"></span>';
    });
    nav.innerHTML = html;
    var spacer = document.createElement('div');
    spacer.id = 'mse-nav-spacer';
    document.body.insertBefore(spacer, document.body.firstChild);
    document.body.insertBefore(nav, document.body.firstChild);
  }

  if (document.body) build();
  else document.addEventListener('DOMContentLoaded', build);
})();
