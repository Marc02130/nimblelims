/**
 * Turn a FastAPI/axios error into a string safe for a React text node.
 * Validation 422 bodies are arrays of { type, loc, msg, input, ctx }.
 * Refusals that carry detail.message show that sentence.
 */
export const apiErrorText = (err: any, fallback: string): string => {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return (
      detail
        .map((item: any) => {
          if (typeof item === 'string') return item;
          if (item?.msg) {
            const loc = Array.isArray(item.loc)
              ? item.loc.filter((part: any) => part !== 'body' && part !== 'query').join('.')
              : '';
            return loc ? `${loc}: ${item.msg}` : item.msg;
          }
          return null;
        })
        .filter(Boolean)
        .join('; ') || fallback
    );
  }
  if (detail && typeof detail === 'object') {
    if (typeof detail.message === 'string') {
      const extra =
        Array.isArray(detail.errors) && detail.errors.length
          ? ` ${detail.errors.slice(0, 3).join('; ')}`
          : '';
      return `${detail.message}${extra}`;
    }
    try {
      return JSON.stringify(detail);
    } catch {
      return fallback;
    }
  }
  if (typeof err?.message === 'string' && err.message) return err.message;
  return fallback;
};
