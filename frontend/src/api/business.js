import { request } from './client.js';

export const loadAll = async () => Object.fromEntries(await Promise.all([
  ['lines', '/lines'], ['batches', '/batches'], ['outcomes', '/outcomes'],
  ['jobs', '/audits/jobs'], ['logs', '/audits/logs'],
].map(async ([k, p]) => [k, await request(p)])));

export const createLine = data => request('/lines', 'POST', { data });
export const saveBatch = data => request('/batches', 'POST', { data });
export const registerOutcome = (action, data) => request('/outcomes/' + action, 'POST', { data });
export const enqueueAudit = audit_date => request('/audits/jobs', 'POST', { audit_date });
export const retryAudit = id => request(`/audits/jobs/${id}/retry`, 'POST', {});
export const loadCurves = id => request(`/audits/jobs/${id}/curves`);
export const loadReasons = id => request(`/audits/jobs/${id}/reasons`);
