/**
 * Turn a FastAPI/axios error into a string safe for a React text node.
 * Validation 422 bodies are arrays of { type, loc, msg, input, ctx }.
 * Render the messages as text, once each, without the loc prefix or the
 * pydantic "Value error," prefix. Refusals that carry detail.message show
 * that sentence.
 */
const readableMessage = (msg: unknown): string | null => {
  if (typeof msg !== 'string') return null;
  const stripped = msg.replace(/^Value error,\s*/i, '').trim();
  return stripped === '' ? null : stripped;
};

export const apiErrorText = (err: any, fallback: string): string => {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const seen = new Set<string>();
    const parts: string[] = [];
    detail.forEach((item: any) => {
      const text = typeof item === 'string' ? item : readableMessage(item?.msg);
      if (text === null || seen.has(text)) return;
      seen.add(text);
      parts.push(text);
    });
    return parts.join('; ') || fallback;
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
