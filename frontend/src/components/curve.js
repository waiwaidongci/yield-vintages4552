import { esc, pct, int, isoDate } from '../utils/format.js';

// 纯 SVG 双曲线：累计返修风险（旧朱）与累计报废风险（黛蓝）
export function lineChart(rows) {
  if (!rows.length) return '<p class="empty">该线暂无寿命表点。</p>';
  const W = 640, H = 240, P = 42;
  const maxDay = Math.max(...rows.map(r => r.day), 1);
  const x = day => P + (day / maxDay) * (W - 2 * P);
  const y = v => H - P - v * (H - 2 * P);
  const path = key => rows.map((r, i) => `${i ? 'L' : 'M'}${x(r.day).toFixed(1)},${y(r[key]).toFixed(1)}`).join(' ');
  const grid = [0, 0.25, 0.5, 0.75, 1].map(v =>
    `<line x1="${P}" y1="${y(v)}" x2="${W - P}" y2="${y(v)}" class="grid"/>
     <text x="${P - 6}" y="${y(v) + 4}" text-anchor="end" class="axis">${v * 100}%</text>`).join('');
  const ticks = [0, Math.round(maxDay / 2), maxDay].map(t =>
    `<text x="${x(t)}" y="${H - P + 18}" text-anchor="middle" class="axis">${t}天</text>`).join('');
  return `<svg viewBox="0 0 ${W} ${H}" class="chart" role="img" aria-label="累计风险曲线">
    ${grid}${ticks}
    <path d="${path('cif_repair')}" class="curve repair"/>
    <path d="${path('cif_scrap')}" class="curve scrap"/>
    <circle cx="${W - P + 8}" cy="${y(rows[rows.length - 1].cif_repair)}" r="4" class="dot repair"/>
    <circle cx="${W - P + 8}" cy="${y(rows[rows.length - 1].cif_scrap)}" r="4" class="dot scrap"/>
  </svg><p class="legend"><i class="swatch repair"></i>累计返修风险　<i class="swatch scrap"></i>累计报废风险</p>`;
}

export function curveBlock(lineCode, lineName, points) {
  const last = points[points.length - 1];
  return `<article class="curve-card"><div class="curve-head"><h3>${esc(lineCode)} ${esc(lineName || '')}</h3>
    <span>末端返修 ${pct(last?.cif_repair)} · 报废 ${pct(last?.cif_scrap)} · 仍在随访 ${pct(last?.survival)}</span></div>
    ${lineChart(points)}
    <details><summary>寿命表明细（出厂后天数 / 在险批数 / 事件数 / 累计风险）</summary>
    <div class="table-wrap"><table><thead><tr>
    <th>出厂后天数</th><th>在险批数</th><th>返修</th><th>报废</th><th>随访结束</th>
    <th>累计返修风险</th><th>累计报废风险</th><th>仍在随访</th></tr></thead><tbody>
    ${points.map(r => `<tr><td>第${r.day}天</td><td>${int(r.n_risk)}</td><td>${int(r.n_repair)}</td><td>${int(r.n_scrap)}</td>
    <td>${int(r.n_censor)}</td><td>${pct(r.cif_repair)}</td><td>${pct(r.cif_scrap)}</td><td>${pct(r.survival)}</td></tr>`).join('')}
    </tbody></table></div></details></article>`;
}
