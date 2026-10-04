import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import ForgotPassword from '../pages/ForgotPassword';
import ResetPassword from '../pages/ResetPassword';

jest.mock('../services/apiService', () => ({
  apiService: {
    requestPasswordReset: jest.fn(),
    confirmPasswordReset: jest.fn(),
  },
}));

const theme = createTheme();

const renderAt = (path: string, element: React.ReactElement) => {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <ThemeProvider theme={theme}>{element}</ThemeProvider>
    </MemoryRouter>
  );
};

describe('password reset pages', () => {
  beforeEach(() => {
    const { apiService } = require('../services/apiService');
    apiService.requestPasswordReset.mockReset();
    apiService.confirmPasswordReset.mockReset();
  });

  test('forgot password shows the server message and does not say the account exists', async () => {
    const { apiService } = require('../services/apiService');
    apiService.requestPasswordReset.mockResolvedValue({
      message: 'If an account exists for that email, we sent a reset link. The link expires in 60 minutes and works once.',
    });
    renderAt('/forgot-password', <ForgotPassword />);
    fireEvent.change(screen.getByRole('textbox', { name: /email/i }), {
      target: { value: 'person@example.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Send reset link' }));
    await waitFor(() => {
      expect(apiService.requestPasswordReset).toHaveBeenCalledWith('person@example.com');
    });
    expect(screen.getByText(/If an account exists for that email/)).toBeInTheDocument();
  });

  test('reset page without a token does not ask for a password', () => {
    renderAt('/reset-password', <ResetPassword />);
    expect(screen.getByText('This reset link is invalid or has expired.')).toBeInTheDocument();
    expect(screen.queryByLabelText(/new password/i)).not.toBeInTheDocument();
  });

  test('reset page submits the token from the link hash', async () => {
    const { apiService } = require('../services/apiService');
    apiService.confirmPasswordReset.mockResolvedValue({
      message: 'Password updated. Sign in with your new password.',
    });
    renderAt('/reset-password#token=abc123token', <ResetPassword />);
    fireEvent.change(screen.getByLabelText(/^New password/i), { target: { value: 'ResetPass123!x' } });
    fireEvent.change(screen.getByLabelText(/^Confirm new password/i), { target: { value: 'ResetPass123!x' } });
    fireEvent.click(screen.getByRole('button', { name: 'Update password' }));
    await waitFor(() => {
      expect(apiService.confirmPasswordReset).toHaveBeenCalledWith('abc123token', 'ResetPass123!x');
    });
    expect(screen.getByText(/Password updated/)).toBeInTheDocument();
  });
});
