export async function request(path, method = 'GET', data) {
  const token = JSON.parse(localStorage.getItem('session') || 'null')?.token;
  const r = await fetch('/api' + path, {
    method,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: 'Bearer ' + token } : {}) },
    ...(data ? { body: JSON.stringify(data) } : {}),
  });
  if (!r.ok) {
    let e = await r.json();
    throw Error(typeof e.detail === 'string' ? e.detail : JSON.stringify(e.detail));
  }
  return r.json();
}
