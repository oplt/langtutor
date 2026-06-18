export function clamp01(x: number) {
  return Math.max(0, Math.min(1, x));
}

// Map raw value into 0..100 using a min/max range
export function scoreFromRange(raw: number, min: number, max: number, invert = false) {
  if (!Number.isFinite(raw)) return null;
  if (!Number.isFinite(min) || !Number.isFinite(max) || max <= min) return null;
  const t = clamp01((raw - min) / (max - min));
  const v = invert ? (1 - t) : t;
  return Math.round(v * 100);
}
