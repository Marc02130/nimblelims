import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import Login from '../pages/Login';
import { UserProvider } from '../contexts/UserContext';

// Mock the API service
jest.mock('../services/apiService', () => ({
  apiService: {
    login: jest.fn(),
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

describe('Login', () => {
  beforeEach(() => {
    // Mock API responses
    const { apiService } = require('../services/apiService');
    apiService.login.mockResolvedValue({
      token: 'mock-token',
      user: {
        id: '1',
        username: 'testuser',
        email: 'test@example.com',
        role: 'Lab Technician',
        permissions: ['sample:create'],
      },
    });
  });

  test('renders login form', () => {
    renderWithProviders(<Login />);
    
    expect(screen.getByText('LIMS Login')).toBeInTheDocument();
    expect(screen.getByText('Laboratory Information Management System')).toBeInTheDocument();
    expect(screen.getByLabelText('Username')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByText('Sign In')).toBeInTheDocument();
  });

  test('validates required fields', async () => {
    renderWithProviders(<Login />);
    
    const submitButton = screen.getByText('Sign In');
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('Username is required')).toBeInTheDocument();
      expect(screen.getByText('Password is required')).toBeInTheDocument();
    });
  });

  test('submits form with valid credentials', async () => {
    renderWithProviders(<Login />);
    
    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'testuser' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'password' } });
    
    const submitButton = screen.getByText('Sign In');
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      const { apiService } = require('../services/apiService');
      expect(apiService.login).toHaveBeenCalledWith('testuser', 'password');
    });
  });

  test('shows error message on login failure', async () => {
    const { apiService } = require('../services/apiService');
    apiService.login.mockRejectedValue(new Error('Invalid credentials'));
    
    renderWithProviders(<Login />);
    
    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'testuser' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'wrongpassword' } });
    
    const submitButton = screen.getByText('Sign In');
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('Login failed')).toBeInTheDocument();
    });
  });

  test('disables submit button while loading', async () => {
    const { apiService } = require('../services/apiService');
    apiService.login.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));
    
    renderWithProviders(<Login />);
    
    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'testuser' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'password' } });
    
    const submitButton = screen.getByText('Sign In');
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(submitButton).toBeDisabled();
    });
  });
});
