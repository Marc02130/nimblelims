/**
 * A calendar date as YYYY-MM-DD on the browser's clock (or the given IANA zone).
 * Never toISOString(), which is UTC and is already tomorrow on an evening west of UTC.
 */
export const localDateString = (now: Date = new Date(), timeZone?: string): string => {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(now);
  const part = (type: string) => parts.find((item) => item.type === type)?.value ?? '';
  return `${part('year')}-${part('month')}-${part('day')}`;
};

/** YYYY-MM-DD prefix of a stored date, or '' when there is nothing to show. */
export const calendarDateInput = (value: unknown): string => {
  if (value instanceof Date) {
    if (Number.isNaN(value.getTime())) return '';
    return localDateString(value);
  }
  if (typeof value !== 'string' || value === '') return '';
  const match = /^(\d{4}-\d{2}-\d{2})/.exec(value);
  return match ? match[1] : '';
};

/** A picker Date for a calendar day. `new Date("YYYY-MM-DD")` is UTC midnight. */
export const parseCalendarDate = (value: unknown): Date | null => {
  const day = calendarDateInput(value);
  if (day === '') return null;
  const [year, month, date] = day.split('-').map(Number);
  if (!year || !month || !date) return null;
  return new Date(year, month - 1, date);
};

/** The picker day as YYYY-MM-DD. Never `toISOString()`. */
export const formatCalendarDate = (value: Date | null | undefined): string | null => {
  if (value == null || Number.isNaN(value.getTime())) return null;
  return localDateString(value);
};

/** Locale label for a lab-day API value. A date-only string stays on that civil day. */
export const formatCalendarDay = (value: unknown): string => {
  const parsed = parseCalendarDate(value);
  if (parsed === null) return '';
  return parsed.toLocaleDateString();
};

const HAS_OFFSET = /(?:Z|[+-]\d{2}:\d{2})$/;

/**
 * An instant in the browser's local zone.
 * A value with no offset is UTC wall time (the API used to omit Z).
 * Calendar dates do not belong here.
 */
export const formatInstant = (value: unknown): string => {
  if (value === null || value === undefined || value === '') return '';
  const raw = value instanceof Date ? value.toISOString() : String(value).trim();
  if (raw === '') return '';
  const hasTime = raw.includes('T') || raw.includes(' ');
  const normalized = HAS_OFFSET.test(raw) || !hasTime ? raw : `${raw.replace(' ', 'T')}Z`;
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) return '';
  return parsed.toLocaleString();
};
