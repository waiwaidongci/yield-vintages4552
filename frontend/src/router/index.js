export const pages = [
  ['overview', '业务总览'],
  ['records', '批次与结局录入'],
  ['audits', '查账日与风险曲线'],
  ['reasons', '失败原因'],
  ['logs', '过程留痕'],
];
export const currentPage = () => location.hash.slice(1) || 'overview';
