/** Pages that stay up with no session. A 401 here must not navigate away. */
export function isPublicAuthPath(pathname: string): boolean {
  return (
    pathname === '/' ||
    pathname === '/login' ||
    pathname === '/forgot-password' ||
    pathname === '/reset-password'
  );
}
