// Device tier and asset loading with progress. Phones get output/m/ (light textures).
export const QUERY = new URLSearchParams(location.search).get('q');
const coarse = typeof matchMedia === 'function' && matchMedia('(pointer: coarse)').matches;
const small = Math.min(screen.width, screen.height) < 900;
const lowMemory = navigator.deviceMemory && navigator.deviceMemory <= 4;
export const LITE = QUERY === 'lite' || (QUERY !== 'hq' && ((coarse && small) || !!lowMemory));
export const asset = path => (LITE ? 'm/' : '') + path;

export async function fetchBuffer(url, onProgress) {
  const res = await fetch(url);
  if (!res.ok) throw new Error('HTTP ' + res.status + ' ' + url);
  const total = +res.headers.get('content-length') || 0;
  if (!res.body || !res.body.getReader) return res.arrayBuffer();
  const reader = res.body.getReader(); const chunks = []; let got = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value); got += value.length; onProgress?.(got, total);
  }
  const out = new Uint8Array(got); let o = 0;
  for (const c of chunks) { out.set(c, o); o += c.length; }
  return out.buffer;
}
export const mb = n => (n / 1048576).toFixed(1);
