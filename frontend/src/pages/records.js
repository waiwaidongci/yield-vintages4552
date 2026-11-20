import { heading } from '../components/common/header.js';
import { table } from '../components/common/table.js';
import { esc, isoDate } from '../utils/format.js';
import { OUTCOMES, ACTIONS } from '../constants/enums.js';

const input = (name, label, type = 'date', required = true) =>
  `<label>${label}<input name="${name}" type="${type}" ${required ? 'required' : ''}></label>`;

export function records(c, d, ctx) {
  const writable = ctx.role !== 'viewer';
  const lineOpts = d.lines.map(l => `<option value="${esc(l.code)}">${esc(l.code)} ${esc(l.name)}</option>`).join('');
  const batchOpts = d.batches.map(b => `<option value="${esc(b.batch_no)}">${esc(b.batch_no)}（${esc(b.line_code)}）</option>`).join('');

  const lineForm = writable ? `<details><summary>新增随访线</summary><form id="line-form" class="form-grid">
    <label>随访线编号<input name="code" placeholder="L-C" required></label>
    <label>随访线名称<input name="name" placeholder="三号随访线" required></label>
    <div><button>建档</button></div></form></details>` : '';

  const batchForm = writable ? `<details><summary>录入 / 更正批次出厂与入组日期（追加版本，不覆盖旧版本）</summary>
    <form id="batch-form" class="form-grid">
      <label>批次号<input name="batch_no" value="${esc(c.example.batch_no)}" required></label>
      <label>随访线<select name="line_code">${lineOpts}</select></label>
      ${input('ship_date', '出厂日期')}${input('enroll_date', '入组日期')}${input('record_date', '记录到账日期')}
      <div><button>保存批次版本</button></div></form>
    <p class="method">到账日期决定该版本在哪个查账日开始可见；入组不得早于出厂。更正请用同批次号再次提交，系统自动追加版本并记录取代关系。</p></details>` : '';

  const outcomeForm = writable ? `<details open><summary>结局登记：首报 / 更正 / 作废（追加流水）</summary>
    <form id="outcome-form" class="form-grid">
      <label>动作<select name="action">${Object.entries(ACTIONS).map(([v, l]) => `<option value="${v}">${l}</option>`).join('')}</select></label>
      <label>批次<select name="batch_no">${batchOpts}</select></label>
      <label>结局类型<select name="outcome">${Object.entries(OUTCOMES).map(([v, l]) => `<option value="${v}">${l}</option>`).join('')}</select></label>
      ${input('event_date', '结局发生日期')}
      <label>失败原因（返修/报废必填，随访结束留空）<input name="reason" placeholder="如：密封件老化"></label>
      ${input('record_date', '到账日期（决定可见查账日）')}
      <div><button>提交结局流水</button></div></form>
    <p class="warning">作废动作只需批次与到账日；重复首报会被拒绝，更正必须基于有效登记。迟报的到账日晚于发生日是允许的，但不允许倒签。</p></details>` : '';

  const batchRows = d.batches.map(b => ({
    批次号: b.batch_no, 随访线: b.line_code, 出厂日: isoDate(b.ship_date),
    入组日: isoDate(b.enroll_date), 到账日: isoDate(b.record_date), 版本数: b.version_count,
  }));
  const outcomeRows = d.outcomes.map(o => ({
    批次号: o.batch_no, 动作: ACTIONS[o.action] || o.action,
    结局: o.outcome ? (OUTCOMES[o.outcome] || o.outcome) : '—',
    发生日: isoDate(o.event_date), 失败原因: o.reason || '—',
    到账日: isoDate(o.record_date), 操作者: o.actor,
  }));

  return heading('RECORDS / 02', '批次与结局录入', '所有录入与更正均为 append-only 版本；按查账日 as-of 可见，历史曲线不被改写。') +
    lineForm + batchForm + outcomeForm +
    `<h2>批次最新版本（共 ${d.batches.length} 批）</h2>` + table(batchRows) +
    `<h2>结局版本流水（最近 ${d.outcomes.length} 条）</h2>` + table(outcomeRows);
}
