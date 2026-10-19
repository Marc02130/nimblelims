import * as Yup from 'yup';

/**
 * Same cap as the sample and test Yup guards. The date input's max attribute
 * does not block a typed value, so save checks it before posting.
 * An empty entry date is allowed (the server dates the row itself).
 */
export const entryDateRefusal = (value: string): string | null => {
  if (value === '') {
    return null;
  }
  try {
    Yup.date()
      .nullable()
      .max(new Date(), 'Entry date cannot be in the future')
      .validateSync(value);
    return null;
  } catch (err: unknown) {
    if (err instanceof Yup.ValidationError && typeof err.message === 'string') {
      return err.message;
    }
    return 'Entry date cannot be in the future';
  }
};
