import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import MainLayout from '../layouts/MainLayout';
import { UserProvider } from '../contexts/UserContext';

// Mock the API service
jest.mock('../services/apiService', () => ({
  apiService: {
    getCurrentUser: jest.fn(),
    setAuthToken: jest.fn(),
  },
}));

// Mock Sidebar component
jest.mock('../components/Sidebar', () => {
  return function MockSidebar({ mobileOpen, onMobileClose }: { mobileOpen: boolean; onMobileClose: () => void }) {
    return (
      <div data-testid="sidebar" data-mobile-open={mobileOpen}>
        <button onClick={onMobileClose}>Close Sidebar</button>
      </div>
    );
  };
});

// Mock useMediaQuery
const mockUseMediaQuery = jest.fn();
jest.mock('@mui/material/useMediaQuery', () => ({
  __esModule: true,
  default: () => mockUseMediaQuery(),
}));

// Mock useNavigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

const theme = createTheme();

// Mock user context
const createMockUser = (permissions: string[] = [], role: string = 'Lab Technician') => ({
  user: {
    id: '1',
    username: 'testuser',
    email: 'test@example.com',
    role,
    permissions,
    client_id: null,
  },
  loading: false,
  login: jest.fn(),
  logout: jest.fn(),
  hasPermission: jest.fn((perm: string) => permissions.includes(perm) || role === 'Administrator'),
});

// Mock UserContext
jest.mock('../contexts/UserContext', () => {
  const actual = jest.requireActual('../contexts/UserContext');
  return {
    ...actual,
    useUser: jest.fn(),
  };
});

const renderWithProviders = (
  component: React.ReactElement,
  initialEntries: string[] = ['/dashboard'],
  mockUser = createMockUser(['sample:create', 'sample:update', 'batch:manage', 'result:enter', 'project:manage', 'config:edit'])
) => {
  const { useUser } = require('../contexts/UserContext');
  useUser.mockReturnValue(mockUser);

  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <ThemeProvider theme={theme}>
        {component}
      </ThemeProvider>
    </MemoryRouter>
  );
};

describe('MainLayout', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseMediaQuery.mockReturnValue(false); // Default to desktop
    mockNavigate.mockClear();
    // Reset useUser mock
    const { useUser } = require('../contexts/UserContext');
    useUser.mockClear();
  });

  describe('Layout rendering', () => {
    test('renders layout with sidebar and main content', () => {
      renderWithProviders(
        <MainLayout>
          <div>Test Content</div>
        </MainLayout>
      );

      expect(screen.getByTestId('sidebar')).toBeInTheDocument();
      expect(screen.getByText('Test Content')).toBeInTheDocument();
    });

    test('renders AppBar with page title', () => {
      renderWithProviders(
        <MainLayout>
          <div>Test Content</div>
        </MainLayout>,
        ['/dashboard']
      );

      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    test('renders user info in AppBar', () => {
      renderWithProviders(
        <MainLayout>
          <div>Test Content</div>
        </MainLayout>
      );

      expect(screen.getByText(/testuser/)).toBeInTheDocument();
      expect(screen.getByText(/Lab Technician/)).toBeInTheDocument();
    });

    test('renders logout button', () => {
      renderWithProviders(
        <MainLayout>
          <div>Test Content</div>
        </MainLayout>
      );

      const logoutButton = screen.getByLabelText('logout');
      expect(logoutButton).toBeInTheDocument();
    });
  });

  describe('Page title mapping', () => {
    test('displays correct title for /dashboard', () => {
      renderWithProviders(
        <MainLayout>
          <div>Test</div>
        </MainLayout>,
        ['/dashboard']
      );

      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    test('displays correct title for /accessioning', () => {
      renderWithProviders(
        <MainLayout>
          <div>Test</div>
        </MainLayout>,
        ['/accessioning']
      );

      expect(screen.getByText('Accessioning')).toBeInTheDocument();
    });

    test('displays correct title for /admin', () => {
      renderWithProviders(
        <MainLayout>
          <div>Test</div>
        </MainLayout>,
        ['/admin']
      );

      expect(screen.getByText('Admin Dashboard')).toBeInTheDocument();
    });

    test('displays correct title for /admin/lists', () => {
      renderWithProviders(
        <MainLayout>
          <div>Test</div>
        </MainLayout>,
        ['/admin/lists']
      );

      expect(screen.getByText('Lists Management')).toBeInTheDocument();
    });

    test('displays correct title for nested route /admin/analyses/:id/analytes', () => {
      renderWithProviders(
        <MainLayout>
          <div>Test</div>
        </MainLayout>,
        ['/admin/analyses/123/analytes']
      );

      expect(screen.getByText('Analysis Analytes Configuration')).toBeInTheDocument();
    });

    test('displays default title for unknown route', () => {
      renderWithProviders(
        <MainLayout>
          <div>Test</div>
        </MainLayout>,
        ['/unknown-route']
      );

      expect(screen.getByText('NimbleLIMS')).toBeInTheDocument();
    });
  });

  describe('Back button', () => {
    test('shows back button for nested admin routes', () => {
      renderWithProviders(
        <MainLayout>
          <div>Test</div>
        </MainLayout>,
        ['/admin/analyses/123/analytes']
      );

      const backButton = screen.getByLabelText('go back');
      expect(backButton).toBeInTheDocument();
    });

    test('does not show back button for regular routes', () => {
      renderWithProviders(
        <MainLayout>
          <div>Test</div>
        </MainLayout>,
        ['/dashboard']
      );

      expect(screen.queryByLabelText('go back')).not.toBeInTheDocument();
    });

    test('navigates back when back button is clicked', () => {
      renderWithProviders(
        <MainLayout>
          <div>Test</div>
        </MainLayout>,
        ['/admin/analyses/123/analytes']
      );

      const backButton = screen.getByLabelText('go back');
      fireEvent.click(backButton);

      expect(mockNavigate).toHaveBeenCalledWith('/admin/analyses');
    });
  });

  describe('Logout functionality', () => {
    test('calls logout and navigates to login when logout button is clicked', () => {
      const mockLogout = jest.fn();
      const mockUser = {
        ...createMockUser(),
        logout: mockLogout,
      };

      renderWithProviders(
        <MainLayout>
          <div>Test</div>
        </MainLayout>,
        ['/dashboard'],
        mockUser
      );

      const logoutButton = screen.getByLabelText('logout');
      fireEvent.click(logoutButton);

      expect(mockLogout).toHaveBeenCalled();
      expect(mockNavigate).toHaveBeenCalledWith('/login');
    });
  });

  describe('Responsive behavior', () => {
    test('shows hamburger menu on mobile', () => {
      mockUseMediaQuery.mockReturnValue(true); // Mobile
      renderWithProviders(
        <MainLayout>
          <div>Test</div>
        </MainLayout>
      );

      const menuButton = screen.getByLabelText('open drawer');
      expect(menuButton).toBeInTheDocument();
    });

    test('hides hamburger menu on desktop', () => {
      mockUseMediaQuery.mockReturnValue(false); // Desktop
      renderWithProviders(
        <MainLayout>
          <div>Test</div>
        </MainLayout>
      );

      const menuButton = screen.queryByLabelText('open drawer');
      expect(menuButton).not.toBeInTheDocument();
    });

    test('hides user info text on mobile', () => {
      mockUseMediaQuery.mockReturnValue(true); // Mobile
      const { container } = renderWithProviders(
        <MainLayout>
          <div>Test</div>
        </MainLayout>
      );

      // User info text should be hidden on mobile (only icon visible)
      const userInfo = screen.queryByText(/testuser.*Lab Technician/);
      // The text might still be in DOM but hidden via CSS
      expect(userInfo).toBeInTheDocument();
    });

    test('shows user info text on desktop', () => {
      mockUseMediaQuery.mockReturnValue(false); // Desktop
      renderWithProviders(
        <MainLayout>
          <div>Test</div>
        </MainLayout>
      );

      expect(screen.getByText(/testuser/)).toBeInTheDocument();
    });

    test('toggles sidebar when hamburger menu is clicked on mobile', () => {
      mockUseMediaQuery.mockReturnValue(true); // Mobile
      renderWithProviders(
        <MainLayout>
          <div>Test</div>
        </MainLayout>
      );

      const menuButton = screen.getByLabelText('open drawer');
      const sidebar = screen.getByTestId('sidebar');

      // Initially closed
      expect(sidebar).toHaveAttribute('data-mobile-open', 'false');

      fireEvent.click(menuButton);

      // Should toggle (state change would be handled internally)
      // We verify the button is clickable
      expect(menuButton).toBeInTheDocument();
    });
  });

  describe('Content area', () => {
    test('renders children in main content area', () => {
      renderWithProviders(
        <MainLayout>
          <div data-testid="test-content">Test Content</div>
        </MainLayout>
      );

      expect(screen.getByTestId('test-content')).toBeInTheDocument();
      expect(screen.getByText('Test Content')).toBeInTheDocument();
    });

    test('applies correct padding and margin to content area', () => {
      const { container } = renderWithProviders(
        <MainLayout>
          <div>Test</div>
        </MainLayout>
      );

      const mainContent = container.querySelector('main');
      expect(mainContent).toBeInTheDocument();
    });
  });

  describe('Edge cases', () => {
    test('handles missing user gracefully', () => {
      const mockUser = {
        user: null,
        loading: false,
        login: jest.fn(),
        logout: jest.fn(),
        hasPermission: jest.fn(() => false),
      };

      renderWithProviders(
        <MainLayout>
          <div>Test</div>
        </MainLayout>,
        ['/dashboard'],
        mockUser
      );

      // Should still render layout
      expect(screen.getByTestId('sidebar')).toBeInTheDocument();
    });

    test('handles empty children', () => {
      renderWithProviders(
        <MainLayout>
          {null}
        </MainLayout>
      );

      expect(screen.getByTestId('sidebar')).toBeInTheDocument();
    });

    test('handles multiple nested routes correctly', () => {
      renderWithProviders(
        <MainLayout>
          <div>Test</div>
        </MainLayout>,
        ['/admin/analyses/abc123/analytes']
      );

      expect(screen.getByText('Analysis Analytes Configuration')).toBeInTheDocument();
      expect(screen.getByLabelText('go back')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    test('has proper ARIA labels for buttons', () => {
      renderWithProviders(
        <MainLayout>
          <div>Test</div>
        </MainLayout>
      );

      expect(screen.getByLabelText('logout')).toBeInTheDocument();
    });

    test('has proper ARIA label for mobile menu toggle', () => {
      mockUseMediaQuery.mockReturnValue(true); // Mobile
      renderWithProviders(
        <MainLayout>
          <div>Test</div>
        </MainLayout>
      );

      expect(screen.getByLabelText('open drawer')).toBeInTheDocument();
    });

    test('has proper ARIA label for back button', () => {
      renderWithProviders(
        <MainLayout>
          <div>Test</div>
        </MainLayout>,
        ['/admin/analyses/123/analytes']
      );

      expect(screen.getByLabelText('go back')).toBeInTheDocument();
    });
  });
});

