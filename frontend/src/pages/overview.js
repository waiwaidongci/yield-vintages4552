import { heading } from '../components/common/header.js';
import { status } from '../components/common/status.js';
import { esc, pct, isoDate } from '../utils/format.js';

export function overview(c, d) {
  const jobs = d.jobs;
  const latest = jobs.find(j => j.status === 'completed');
  const batchCount = d.batches.length;
  const lineCount = d.lines.length;
  let headline = '<p class="empty">尚无完成的查账日，先在「查账日与风险曲线」发起核算。</p>';
  if (latest) {
    headline = `<div class="metrics"><div><small>最新查账日</small><strong>${isoDate(latest.audit_date)}</strong></div>
      <div><small>核算模式</small><strong>${latest.mode === 'incremental' ? '增量重算' : '整体重算'}</strong></div>
      <div><small>受影响线</small><strong>${esc((latest.changed_lines || []).join('、') || '—')}</strong></div>
      <div><small>随访线 / 批次</small><strong>${lineCount} 线 · ${batchCount} 批</strong></div></div>
      <p class="method">口径：同日先入组，再以同一在险批数并列累计返修与报废风险，最后移除随访结束批次；
      迟报与更正仅在其到账日之后的查账日可见，历史查账日曲线冻结。</p>`;
  }
  return heading('OVERVIEW / 01', '出厂后返修风险总览', '按查账日可见版本核算，各随访线曲线独立可追溯。') +
    `<div class="overview"><aside class="overview-count"><b>${batchCount}</b><p>个在档批次</p><hr>
     <p>${lineCount} 条随访线<br>${d.outcomes.length} 条结局版本流水<br>${jobs.length} 个查账日任务</p>
     <p>${esc(c.algorithm)}</p></aside><div>${headline}
     <h2>最近查账任务</h2>${jobs.length ? '<div class="job-list">' + jobs.slice(0, 6).map(j =>
      `<a class="job-row" href="#audits"><span>${isoDate(j.audit_date)}</span>${status(j.status)}<small>${esc(j.mode || '—')} · ${esc((j.changed_lines || []).join(',') || '全线')}</small></a>`).join('') + '</div>'
      : '<p class="empty">暂无任务。</p>'}</div></div>`;
}
