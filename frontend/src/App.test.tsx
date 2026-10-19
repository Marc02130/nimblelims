import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import App from './App';
import { UserProvider } from './contexts/UserContext';

// Mock the API service
jest.mock('./services/apiService', () => ({
  apiService: {
    getCurrentUser: jest.fn(),
    setAuthToken: jest.fn(),
    logout: jest.fn().mockResolvedValue(undefined),
    requestPasswordReset: jest.fn(),
    confirmPasswordReset: jest.fn(),
    updateLabSettings: jest.fn(),
  },
}));

const theme = createTheme();

const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      <ThemeProvider theme={theme}>
        <UserProvider>
          {component}
        </UserProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
};

describe('App', () => {
  test('renders login when user is not authenticated', async () => {
    // Mock no user
    const { apiService } = require('./services/apiService');
    apiService.getCurrentUser.mockRejectedValue(new Error('Not authenticated'));
    
    renderWithProviders(<App />);
    
    // The cookie-session probe (/auth/me) settles first, then the login page shows.
    expect(await screen.findByText('LIMS Login')).toBeInTheDocument();
  });

  test('renders dashboard when user is authenticated', async () => {
    // Mock authenticated user
    const { apiService } = require('./services/apiService');
    apiService.getCurrentUser.mockResolvedValue({
      id: '1',
      username: 'testuser',
      email: 'test@example.com',
      role: 'Lab Technician',
      permissions: ['sample:read'],
      timezone_configured: true,
    });
    
    renderWithProviders(<App />);
    
    // "Dashboard" is both the page heading and a sidebar item.
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument();
  });

  test('blocks a non-admin when the lab timezone is not set', async () => {
    const { apiService } = require('./services/apiService');
    apiService.getCurrentUser.mockResolvedValue({
      id: '1',
      username: 'tech',
      email: 'tech@example.com',
      role: 'Lab Technician',
      permissions: ['sample:read'],
      timezone_configured: false,
    });

    renderWithProviders(<App />);

    expect(
      await screen.findByText(/The lab timezone hasn't been set/i)
    ).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Dashboard' })).not.toBeInTheDocument();
  });

  test('sends an admin to timezone setup when the zone is not set', async () => {
    const { apiService } = require('./services/apiService');
    apiService.getCurrentUser.mockResolvedValue({
      id: '1',
      username: 'admin',
      email: 'admin@example.com',
      role: 'Administrator',
      permissions: ['config:edit'],
      timezone_configured: false,
    });

    renderWithProviders(<App />);

    expect(await screen.findByText('Set the lab timezone')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Dashboard' })).not.toBeInTheDocument();
  });

  test('admin setup saves a timezone and then opens the app', async () => {
    const { apiService } = require('./services/apiService');
    apiService.getCurrentUser.mockResolvedValue({
      id: '1',
      username: 'admin',
      email: 'admin@example.com',
      role: 'Administrator',
      permissions: ['sample:read', 'config:edit'],
      timezone_configured: false,
    });
    apiService.updateLabSettings.mockResolvedValue({
      timezone: 'America/New_York',
      timezone_configured: true,
    });

    renderWithProviders(<App />);
    expect(await screen.findByText('Set the lab timezone')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/IANA timezone/i), {
      target: { value: 'America/New_York' },
    });
    apiService.getCurrentUser.mockResolvedValue({
      id: '1',
      username: 'admin',
      email: 'admin@example.com',
      role: 'Administrator',
      permissions: ['sample:read', 'config:edit'],
      timezone_configured: true,
    });
    fireEvent.click(screen.getByRole('button', { name: 'Save timezone' }));

    await waitFor(() => {
      expect(apiService.updateLabSettings).toHaveBeenCalledWith({
        timezone: 'America/New_York',
      });
    });
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument();
  });
});
