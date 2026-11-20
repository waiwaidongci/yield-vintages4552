import { heading } from '../components/common/header.js';
import { status } from '../components/common/status.js';
import { curveBlock } from '../components/curve.js';
import { esc, isoDate } from '../utils/format.js';
import { MODES } from '../constants/enums.js';

export function audits(c, d, ctx) {
  const writable = ctx.role !== 'viewer';
  const store = ctx.store;
  const jobs = d.jobs;
  const selectedId = store.selectedJob || jobs[0]?.id;
  const selected = jobs.find(j => j.id === selectedId);
  const curves = store.curves && store.curves.job?.id === selectedId ? store.curves : null;

  const form = writable ? `<form id="audit-form" class="inline-form">
    <label>查账日（按当日能看到的版本核算）<input name="audit_date" type="date" required></label>
    <button>发起查账核算</button></form>
    <p class="method">同一查账日任务唯一：重复提交复用原单；worker 中断后重启自动恢复 running 原单，失败可重试，均不重复出曲线。</p>` : '';

  const jobList = jobs.length ? `<div class="job-list">${jobs.map(j =>
    `<button class="job-row ${j.id === selectedId ? 'active' : ''}" data-job="${j.id}">
      <span>${isoDate(j.audit_date)}</span>${status(j.status)}
      <small>${esc(j.mode ? MODES[j.mode] : '—')} · 受影响 ${esc((j.changed_lines || []).join(',') || '全线')}</small>
      ${j.status === 'failed' && writable ? `<em class="retry" data-retry="${j.id}">重试</em>` : ''}
    </button>`).join('')}</div>` : '<p class="empty">暂无查账任务。</p>';

  let detail = '<p class="empty">选择左侧查账日查看各线曲线。</p>';
  if (selected) {
    if (selected.status === 'failed') {
      detail = `<p class="error">核算失败：${esc(selected.error || '未知错误')}${writable ? '，可在左侧点击重试。' : ''}</p>`;
    } else if (selected.status !== 'completed') {
      detail = `<p class="empty">任务${selected.status === 'running' ? '核算中' : '排队中'}，完成后自动刷新…</p>`;
    } else if (curves) {
      detail = Object.entries(curves.lines).map(([code, pts]) =>
        curveBlock(code, d.lines.find(l => l.code === code)?.name, pts)).join('');
    } else {
      detail = '<p class="empty">曲线加载中…</p>';
    }
  }

  return heading('AUDIT DESK / 03', '查账日与累计返修风险曲线', '迟报与更正只影响新查账日；并发更正从受影响线最早变动天数增量重算，整条曲线一次性切换。') +
    form + `<div class="run-layout"><aside class="run-list">${jobList}</aside><div>${detail}</div></div>`;
}
