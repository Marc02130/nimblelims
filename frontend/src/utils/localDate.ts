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
