import { heading } from '../components/common/header.js';
import { table } from '../components/common/table.js';
import { time } from '../utils/format.js';

export function logs(c, d) {
  const rows = d.logs.map(a => ({ 时间: time(a.at), 操作者: a.actor, 动作: a.action, 内容: a.detail }));
  return heading('PROCESS RECORD / 05', '过程留痕', '建档、批次版本、结局流水与查账任务均记录操作者与时间，支持事后追溯。') + table(rows);
}
