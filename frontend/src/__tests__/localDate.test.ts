import { localDateString } from '../utils/localDate';

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
