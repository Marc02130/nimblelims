import { apiErrorText } from '../utils/apiErrorText';

describe('apiErrorText', () => {
  it('renders a 422 list as one sentence without the loc or Value error prefix', () => {
    const err = {
      response: {
        data: {
          detail: [
            {
              type: 'value_error',
              loc: ['body', 'results', 0, 'entry_date'],
              msg: 'Value error, Entry date cannot be in the future',
              input: '2026-10-19',
              ctx: { error: {} },
            },
            {
              type: 'value_error',
              loc: ['body', 'results', 0, 'entry_date'],
              msg: 'Value error, Entry date cannot be in the future',
              input: '2026-10-19',
              ctx: { error: {} },
            },
          ],
        },
      },
    };

    expect(apiErrorText(err, 'Failed to save results')).toBe(
      'Entry date cannot be in the future'
    );
  });

  it('keeps a string detail and a message object', () => {
    expect(apiErrorText({ response: { data: { detail: 'API Error' } } }, 'fallback')).toBe(
      'API Error'
    );
    expect(
      apiErrorText(
        { response: { data: { detail: { message: 'Date cannot be in the future' } } } },
        'fallback'
      )
    ).toBe('Date cannot be in the future');
  });
});
