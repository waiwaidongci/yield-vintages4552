import { heading } from '../components/common/header.js';
import { table } from '../components/common/table.js';
import { esc, isoDate } from '../utils/format.js';
import { OUTCOMES } from '../constants/enums.js';

export function reasons(c, d, ctx) {
  const store = ctx.store;
  const jobs = d.jobs.filter(j => j.status === 'completed');
  const selectedId = store.reasonJob || store.selectedJob || jobs[0]?.id;
  const rows = (store.reasons || []).map(r => ({
    随访线: r.line_code,
    结局: OUTCOMES[r.outcome] || r.outcome,
    失败原因: r.reason || '—',
    累计批数: r.n_batches,
  }));
  const selector = jobs.length ? `<form id="reason-job" class="inline-form"><label>查账日
    <select name="job_id">${jobs.map(j => `<option value="${j.id}" ${j.id === selectedId ? 'selected' : ''}>${isoDate(j.audit_date)}</option>`).join('')}</select></label></form>`
    : '<p class="empty">尚无完成的查账日。</p>';
  return heading('FAILURE REASONS / 04', '失败原因累计批数', '按查账日有效登记汇总返修与报废原因；随访结束为删失，不计失败原因。') +
    selector + (rows.length ? table(rows) : '<p class="empty">该查账日暂无返修/报废原因记录。</p>');
}
