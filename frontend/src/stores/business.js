import { loadAll } from '../api/business.js';

export const store = {
  session: JSON.parse(localStorage.getItem('session') || 'null'),
  data: { lines: [], batches: [], outcomes: [], jobs: [], logs: [] },
  selectedJob: null,
  curves: null,
  reasons: [],
};

export async function reload() {
  store.data = await loadAll();
  if (store.selectedJob && !store.data.jobs.some(j => j.id === store.selectedJob)) {
    store.selectedJob = null;
    store.curves = null;
  }
}

export function setSession(value) {
  store.session = value;
  if (value) localStorage.setItem('session', JSON.stringify(value));
  else localStorage.removeItem('session');
}
