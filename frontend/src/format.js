const TZ = "Europe/London";
const timeFmt = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, hour: "2-digit", minute: "2-digit" });
const dayFmt = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, weekday: "short", day: "numeric", month: "short" });
const longDayFmt = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, weekday: "long", day: "numeric", month: "long" });

export const hhmm = (ms) => timeFmt.format(new Date(ms));
export const dayShort = (iso) => dayFmt.format(new Date(iso));
export const dayLong = (iso) => longDayFmt.format(new Date(iso));
export const mw = (v, digits = 0) =>
  v == null ? "–" : `${Number(v).toLocaleString("en-GB", { maximumFractionDigits: digits })} MW`;
export const num = (v, digits = 0) =>
  v == null ? "–" : Number(v).toLocaleString("en-GB", { maximumFractionDigits: digits });
export const pct = (v, digits = 1) => (v == null ? "–" : `${Number(v).toFixed(digits)}%`);

export function addDays(iso, n) {
  const d = new Date(`${iso}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}
