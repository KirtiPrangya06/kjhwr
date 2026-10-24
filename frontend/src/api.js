// Same-origin by default (Vite proxy in dev, serverless functions on Vercel).
const BASE = import.meta.env.VITE_API_URL || "";

async function get(path, params = {}) {
  const res = await fetch(`${BASE}${path}?${new URLSearchParams(params)}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export const api = {
  config: () => get("/api/config"),
  forecast: (deliveryDate, cutoff) => get("/api/forecast", { delivery_date: deliveryDate, cutoff }),
  metrics: (cutoff) => get("/api/metrics", { cutoff }),
  horizon: () => get("/api/horizon"),
  sensitivity: () => get("/api/cutoff-sensitivity"),
};
