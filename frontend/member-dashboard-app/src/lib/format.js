export function classNames(...values) {
  return values.filter(Boolean).join(" ");
}

export function formatCount(value, fallback = "0") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

export function fileSize(bytes) {
  const value = Number(bytes || 0);
  if (!value) return "0 KB";
  if (value < 1024 * 1024) return `${Math.max(1, Math.round(value / 1024))} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}
