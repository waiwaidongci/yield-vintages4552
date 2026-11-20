import { request } from './api/client.js';
import { loadAll, createLine, saveBatch, registerOutcome, enqueueAudit, retryAudit, loadCurves, loadReasons } from './api/business.js';
import { store, reload, setSession } from './stores/business.js';
import { pages, currentPage } from './router/index.js';
import { esc } from './utils/format.js';
import { action } from './hooks/action.js';
import { login } from './pages/login.js';
import { overview } from './pages/overview.js';
import { records } from './pages/records.js';
import { audits } from './pages/audits.js';
import { reasons } from './pages/reasons.js';
import { logs } from './pages/logs.js';

const c = await (await fetch('/project.json')).json();
const app = document.querySelector('#app');
let busy = false;
const renderers = { overview, records, audits, reasons, logs };

async function ensureJobDetails() {
  const page = currentPage();
  const jobs = store.data.jobs;
  const selectedId = store.selectedJob || jobs[0]?.id;
  const selected = jobs.find(j => j.id === selectedId);
  if (!selected || selected.status !== 'completed') return;
  store.selectedJob = selectedId;
  if (page === 'audits' && (!store.curves || store.curves.job.id !== selectedId)) {
    store.curves = await loadCurves(selectedId);
  }
  if (page === 'reasons' && (!store.reasonJob || store.reasonJob !== selectedId)) {
    store.reasonJob = selectedId;
    store.reasons = await loadReasons(selectedId);
  }
}

function render() {
  if (!store.session) {
    app.innerHTML = login(c) + '<div id="notice" role="status"></div>';
    document.querySelector('#login').onsubmit = e => {
      e.preventDefault();
      action(async () => {
        const b = Object.fromEntries(new FormData(e.target));
        setSession(await request('/auth/login', 'POST', b));
        await reload();
        render();
      });
    };
    return;
  }
  const page = currentPage();
  const role = store.session.role;
  app.innerHTML = `<div class="shell"><aside class="sidebar">
    <a href="#overview" class="brand">${esc(c.title.slice(0, 2))}<small>售后随访查账<br>${esc(c.slug)}</small></a>
    <nav>${pages.map(([id, title], i) =>
      `<a class="${page === id ? 'active' : ''}" href="#${id}"><span>0${i + 1}</span>${title}</a>`).join('')}</nav>
    <footer>${esc(store.session.email)}<br><b>${esc(role)}</b><br><button id="logout">退出</button></footer></aside>
    <main class="workspace"><div class="topline"><span>${esc(c.title)}</span><button id="refresh">刷新数据</button></div>
    <div id="notice" role="status"></div>${(renderers[page] || overview)(c, store.data, { role, store })}</main></div>`;
  bind(page, role);
}

function bind(page, role) {
  document.querySelector('#logout').onclick = () => { setSession(null); render(); };
  document.querySelector('#refresh').onclick = () => action(async () => { await reload(); render(); });
  if (role === 'viewer') return;

  const lf = document.querySelector('#line-form');
  if (lf) lf.onsubmit = e => {
    e.preventDefault();
    action(async () => { await createLine(Object.fromEntries(new FormData(lf))); await reload(); render(); });
  };
  const bf = document.querySelector('#batch-form');
  if (bf) bf.onsubmit = e => {
    e.preventDefault();
    action(async () => { await saveBatch(Object.fromEntries(new FormData(bf))); await reload(); render(); });
  };
  const of = document.querySelector('#outcome-form');
  if (of) {
    const syncVoid = () => {
      const isVoid = new FormData(of).get('action') === 'void';
      ['outcome', 'event_date', 'reason'].forEach(n => {
        const el = of.elements[n];
        if (el) el.disabled = isVoid;
      });
    };
    of.elements.action.onchange = syncVoid;
    syncVoid();
    of.onsubmit = e => {
      e.preventDefault();
      action(async () => {
        const b = Object.fromEntries(new FormData(of));
        const act = b.action;
        delete b.action;
        await registerOutcome(act, act === 'void' ? { batch_no: b.batch_no, record_date: b.record_date } : b);
        await reload();
        render();
      });
    };
  }
  const af = document.querySelector('#audit-form');
  if (af) af.onsubmit = e => {
    e.preventDefault();
    action(async () => {
      const b = Object.fromEntries(new FormData(af));
      const job = await enqueueAudit(b.audit_date);
      store.selectedJob = job.id;
      store.curves = null;
      await reload();
      render();
    });
  };
  document.querySelectorAll('[data-job]').forEach(btn => btn.onclick = () => action(async () => {
    store.selectedJob = Number(btn.dataset.job);
    store.curves = null;
    store.reasonJob = null;
    await ensureJobDetails();
    render();
  }));
  document.querySelectorAll('[data-retry]').forEach(btn => btn.onclick = e => {
    e.stopPropagation();
    action(async () => { await retryAudit(Number(btn.dataset.retry)); await reload(); render(); });
  });
  const rj = document.querySelector('#reason-job');
  if (rj) rj.onchange = () => action(async () => {
    store.reasonJob = Number(new FormData(rj).get('job_id'));
    store.reasons = await loadReasons(store.reasonJob);
    render();
  });
}

window.addEventListener('hashchange', render);
(async function boot() {
  if (store.session) {
    try { await reload(); } catch { setSession(null); }
  }
  await ensureJobDetails().catch(() => {});
  render();
  setInterval(async () => {
    if (!store.session || busy) return;
    if (!store.data.jobs.some(j => ['queued', 'running'].includes(j.status))) return;
    busy = true;
    try {
      await reload();
      await ensureJobDetails().catch(() => {});
      render();
    } finally { busy = false; }
  }, 2000);
  // 曲线/原因在页面切换或任务完成后懒加载
  window.addEventListener('hashchange', () => ensureJobDetails().then(render).catch(() => {}));
})();
