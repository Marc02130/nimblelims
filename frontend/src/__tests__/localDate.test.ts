import { formatCalendarDate, formatCalendarDay, localDateString, parseCalendarDate } from '../utils/localDate';

describe('localDateString', () => {
  test.each([
    ['2026-10-19T00:00:00Z', '8:00 PM EDT'],
    ['2026-10-19T01:30:00Z', '9:30 PM EDT'],
    ['2026-10-19T03:59:00Z', '11:59 PM EDT'],
  ])('keeps the lab date at %s (%s)', (instant) => {
    const evening = new Date(instant);
    expect(evening.toISOString().slice(0, 10)).toBe('2026-10-19');
    expect(localDateString(evening, 'America/New_York')).toBe('2026-10-18');
  });

  test('rolls over at midnight on the lab clock', () => {
    expect(localDateString(new Date('2026-10-19T04:00:00Z'), 'America/New_York')).toBe('2026-10-19');
  });

  test("defaults to the browser's own calendar date", () => {
    const now = new Date(2026, 0, 5, 9, 0);
    expect(localDateString(now)).toBe('2026-01-05');
  });
});

describe('calendar form values', () => {
  test('parses a date-only string as that local calendar day', () => {
    const parsed = parseCalendarDate('2026-10-19');
    expect(parsed).not.toBeNull();
    expect(parsed?.getFullYear()).toBe(2026);
    expect(parsed?.getMonth()).toBe(9);
    expect(parsed?.getDate()).toBe(19);
    expect(new Date('2026-10-19').getUTCHours()).toBe(0);
  });

  test('submits the picker day without shifting through UTC', () => {
    const picked = new Date(2026, 9, 19, 0, 0, 0);
    expect(formatCalendarDate(picked)).toBe('2026-10-19');
  });

  test('displays a date-only lab day on that calendar day', () => {
    const parsed = parseCalendarDate('2026-10-19');
    expect(parsed?.getFullYear()).toBe(2026);
    expect(parsed?.getMonth()).toBe(9);
    expect(parsed?.getDate()).toBe(19);
    expect(formatCalendarDay('2026-10-19')).toBe(parsed?.toLocaleDateString());
    expect(formatCalendarDay('2026-10-19T00:00:00')).toBe(parsed?.toLocaleDateString());
    const utcMidnight = new Date('2026-10-19T00:00:00Z').toLocaleDateString();
    if (utcMidnight !== parsed?.toLocaleDateString()) {
      expect(formatCalendarDay('2026-10-19')).not.toBe(utcMidnight);
    }
  });
});
