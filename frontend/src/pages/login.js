import { esc } from '../utils/format.js';
export function login(c) {
  return `<main class="login"><section class="login-story"><p class="eyebrow">售后随访 · ${esc(c.id)}</p>
  <h1>${esc(c.title)}</h1><p class="statement">${esc(c.caption)}</p><div class="rule-line"></div>
  <p>${esc(c.scenario)}</p><small>原生 HTML / CSS / JavaScript · Python 实算 Aalen-Johansen</small></section>
  <section class="login-form"><p class="eyebrow">WORK DESK / 01</p><h2>进入售后工作席</h2>
  <form id="login"><label>工作邮箱<input name="email" value="admin@demo.local" type="email" required></label>
  <label>密码<input name="password" value="Demo2026!" type="password" required></label><button>进入工作席</button></form>
  <p>负责人 admin@demo.local<br>售后分析员 analyst@demo.local<br>阅读者 viewer@demo.local<br>演示密码：Demo2026!</p></section></main>`;
}
