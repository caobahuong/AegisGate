export interface ExtractedResult {
  dataRows: Record<string, unknown>[] | null;
  rowsAffected: number | null;
  columns: string[];
  raw: unknown;
}

export const parseResultSummary = (
  summary: Record<string, unknown> | string | null
): ExtractedResult => {
  if (!summary) return { dataRows: null, rowsAffected: null, columns: [], raw: null };
  let parsed: unknown = summary;
  if (typeof summary === "string") {
    try {
      parsed = JSON.parse(summary);
    } catch {
      return { dataRows: null, rowsAffected: null, columns: [], raw: summary };
    }
  }
  if (!parsed || typeof parsed !== "object") {
    return { dataRows: null, rowsAffected: null, columns: [], raw: parsed };
  }

  const pObj = parsed as Record<string, unknown>;
  const data = Array.isArray(pObj.data)
    ? (pObj.data as Record<string, unknown>[])
    : Array.isArray(parsed)
      ? (parsed as Record<string, unknown>[])
      : null;

  const rows = typeof pObj.rows_affected === "number" ? pObj.rows_affected : (data?.length ?? null);
  const cols = data && data.length > 0 && typeof data[0] === "object" ? Object.keys(data[0]) : [];

  return {
    dataRows: data,
    rowsAffected: rows,
    columns: cols,
    raw: parsed,
  };
};
