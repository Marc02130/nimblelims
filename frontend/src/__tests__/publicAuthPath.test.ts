import { isPublicAuthPath } from '../services/publicAuthPath';

describe('public auth paths', () => {
  test('a reset link is not sent to the login page', () => {
    expect(isPublicAuthPath('/reset-password')).toBe(true);
    expect(isPublicAuthPath('/forgot-password')).toBe(true);
    expect(isPublicAuthPath('/login')).toBe(true);
    expect(isPublicAuthPath('/')).toBe(true);
  });

  test('an expired session on a lab page still goes to login', () => {
    expect(isPublicAuthPath('/dashboard')).toBe(false);
    expect(isPublicAuthPath('/samples')).toBe(false);
  });
});
