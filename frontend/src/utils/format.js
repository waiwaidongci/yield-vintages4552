export const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[c]));

export const pct = v => (v == null ? '—' : (v * 100).toFixed(2) + '%');
export const int = v => (v == null ? '—' : Number(v).toLocaleString('zh-CN'));
export const dayText = v => (v == null ? '—' : '第' + v + '天');
export const isoDate = v => v ? String(v).slice(0, 10) : '—';
export const time = v => new Date(v * 1000).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });
export const fmt = v => typeof v === 'number' ? int(v) : esc(typeof v === 'object' ? JSON.stringify(v) : v);
