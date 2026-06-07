/**
 * 文档站飞书登录门禁（页面访问门禁）
 *
 * 在每个需要保护的 HTML <head> 引入（必须在页面内容渲染前同步执行）：
 *   <script src="./assets/auth-guard.js"></script>
 *
 * 依赖一个后端服务，提供 3 个接口（见 DEPLOY.md 第二节「后端接口要点」）：
 *   GET /auth/feishu/login?redirect=<回跳地址>  → 302 到飞书授权页
 *   GET /auth/feishu/callback?code&state         → 校验组织、建 session、跳回并带 ?doc_session=
 *   GET /auth/feishu/verify  (Bearer session)    → 200 已登录 / 401 未登录
 *
 * 换项目只改下面「配置」三行。
 */
(function () {
  // ── 配置 ────────────────────────────────────────────────
  var API_BASE   = 'https://your-auth-backend.example.com'; // 你的鉴权后端（https，固定，勿用 location.protocol）
  var SESSION_KEY = 'doc_session';                          // localStorage 里存 session 的键名
  var PARAM_KEY   = 'doc_session';                          // 后端 callback 回跳时带的参数名（与后端一致）
  // ────────────────────────────────────────────────────────

  var LOGIN_PATH = '/auth/feishu/login';
  var VERIFY_PATH = '/auth/feishu/verify';

  var host = location.hostname;
  // 本地开发 / 直接双击 file:// 不拦截，方便编辑预览
  if (location.protocol === 'file:' || host === 'localhost' || host === '127.0.0.1' || host === '' || host === '0.0.0.0') {
    return;
  }

  // 1. 接收 OAuth 回调带回来的 session，存下并清理 URL
  var params = new URLSearchParams(location.search);
  var incoming = params.get(PARAM_KEY);
  if (incoming) {
    localStorage.setItem(SESSION_KEY, incoming);
    params.delete(PARAM_KEY);
    history.replaceState({}, '', location.pathname + (params.toString() ? '?' + params.toString() : '') + location.hash);
  }

  // 2. 验证前先隐藏页面，避免未鉴权内容闪现
  var root = document.documentElement;
  root.style.visibility = 'hidden';

  var sid = localStorage.getItem(SESSION_KEY);
  function goLogin() {
    localStorage.removeItem(SESSION_KEY);
    location.href = API_BASE + LOGIN_PATH + '?redirect=' + encodeURIComponent(location.href);
  }
  function show() { root.style.visibility = ''; }

  // 3. 无 session 直接跳登录
  if (!sid) { goLogin(); return; }

  // 4. 有 session 调后端校验
  fetch(API_BASE + VERIFY_PATH, { headers: { 'Authorization': 'Bearer ' + sid } })
    .then(function (r) { if (r.ok) { show(); } else { goLogin(); } })
    .catch(function () { show(); }); // 后端抖动/离线时放行，不因服务不稳定阻断内部团队
})();
