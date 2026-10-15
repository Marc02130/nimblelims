import React from 'react';
import { render, screen } from '@testing-library/react';
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
    });
    
    renderWithProviders(<App />);
    
    // "Dashboard" is both the page heading and a sidebar item.
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument();
  });
});
