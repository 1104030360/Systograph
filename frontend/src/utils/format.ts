export function compactId(id: string): string {
  return id.replace(/^node:/, "").replace(/^component:/, "").replace(/^edge:/, "").replace(/^graph_edge:/, "");
}

export function formatValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "None";
  }

  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return JSON.stringify(value, null, 2);
}

export function titleCase(value: string): string {
  return value
    .replace(/[_:-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}
