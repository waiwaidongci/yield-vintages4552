import { fmt, esc } from '../../utils/format.js';
export function table(rows, cols) {
  if (!rows.length) return '<div class="empty">暂无记录。</div>';
  cols = cols || Object.keys(rows[0]);
  return '<div class="table-wrap"><table><thead><tr>' + cols.map(k => '<th>' + esc(k) + '</th>').join('') +
    '</tr></thead><tbody>' + rows.map(r => '<tr>' + cols.map(k => '<td>' + fmt(r[k]) + '</td>').join('') + '</tr>').join('') +
    '</tbody></table></div>';
}
