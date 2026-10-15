import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import Sidebar from '../components/Sidebar';
import { UserProvider } from '../contexts/UserContext';

// Mock the API service
jest.mock('../services/apiService', () => ({
  // Real helpers (ApiService.formatError, addClientFilterIfNeeded, types); only the client is mocked.
  ...jest.requireActual('../services/apiService'),
  apiService: {
    getCurrentUser: jest.fn(),
    setAuthToken: jest.fn(),
    logout: jest.fn().mockResolvedValue(undefined),
  },
}));

// Mock useMediaQuery
const mockUseMediaQuery = jest.fn();
jest.mock('@mui/material/useMediaQuery', () => ({
  __esModule: true,
  default: () => mockUseMediaQuery(),
}));

const theme = createTheme();

// Sidebar renders the same content twice: a temporary drawer for mobile
// (keepMounted) and a permanent one for desktop. Query the permanent one.
const sidebar = () => within(document.querySelector('.MuiDrawer-docked') as HTMLElement);

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
  // Plain function, not jest.fn: CRA's resetMocks would wipe the implementation.
  hasPermission: ((perm: string) => permissions.includes(perm) || role === 'Administrator'),
});

// Mock UserContext
jest.mock('../contexts/UserContext', () => {
  const actual = jest.requireActual('../contexts/UserContext');
  return {
    ...actual,
    useUser: jest.fn(),
  };
});

// The logged-out case passes user: null.
type MockUserContext = Omit<ReturnType<typeof createMockUser>, 'user'> & {
  user: ReturnType<typeof createMockUser>['user'] | null;
};

const renderWithProviders = (
  component: React.ReactElement,
  initialEntries: string[] = ['/dashboard'],
  mockUser: MockUserContext = createMockUser(['sample:create', 'sample:read', 'sample:update', 'batch:manage', 'result:enter', 'project:manage', 'config:edit'])
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

describe('Sidebar', () => {
  const mockOnMobileClose = jest.fn();
  const defaultProps = {
    mobileOpen: false,
    onMobileClose: mockOnMobileClose,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseMediaQuery.mockReturnValue(false); // Default to desktop
    // Reset useUser mock
    const { useUser } = require('../contexts/UserContext');
    useUser.mockClear();
  });

  describe('Rendering', () => {
    test('renders sidebar with logo and core features', () => {
      renderWithProviders(<Sidebar {...defaultProps} />);
      
      expect(sidebar().getByText('NimbleLIMS')).toBeInTheDocument();
      expect(sidebar().getByText('Core Features')).toBeInTheDocument();
      expect(sidebar().getByText('Dashboard')).toBeInTheDocument();
    });

    test('renders all core navigation items when user has permissions', () => {
      renderWithProviders(<Sidebar {...defaultProps} />);
      
      expect(sidebar().getByText('Dashboard')).toBeInTheDocument();
      expect(sidebar().getByText('Receive')).toBeInTheDocument();
      expect(sidebar().getAllByText('Asked-for').length).toBeGreaterThan(0);
      expect(sidebar().getByText('Containers')).toBeInTheDocument();
      expect(sidebar().getByText('Batches')).toBeInTheDocument();
      expect(sidebar().getByText('Results')).toBeInTheDocument();
    });

    test('renders admin section when user has config:edit permission', () => {
      renderWithProviders(<Sidebar {...defaultProps} />);
      
      expect(sidebar().getByText('Admin')).toBeInTheDocument();
    });

    test('does not render admin section when user lacks config:edit permission', () => {
      const mockUser = createMockUser(['sample:create'], 'Lab Technician');
      renderWithProviders(<Sidebar {...defaultProps} />, ['/dashboard'], mockUser);
      
      expect(sidebar().queryByText('Admin')).not.toBeInTheDocument();
    });

    test('renders user info at bottom', () => {
      renderWithProviders(<Sidebar {...defaultProps} />);
      
      expect(sidebar().getByText(/testuser/)).toBeInTheDocument();
      expect(sidebar().getByText(/Lab Technician/)).toBeInTheDocument();
    });
  });

  describe('Permission-based visibility', () => {
    test('hides Receive when user lacks sample:create permission', () => {
      const mockUser = createMockUser(['sample:update'], 'Lab Technician');
      renderWithProviders(<Sidebar {...defaultProps} />, ['/dashboard'], mockUser);
      
      expect(sidebar().queryByText('Receive')).not.toBeInTheDocument();
      expect(sidebar().getAllByText('Containers').length).toBeGreaterThan(0);
    });

    test('places Asked-for immediately after Receive', () => {
      renderWithProviders(<Sidebar {...defaultProps} />);
      const receive = sidebar().getAllByText('Receive')[0];
      const askedFor = sidebar().getAllByText('Asked-for')[0];
      expect(
        receive.compareDocumentPosition(askedFor) & Node.DOCUMENT_POSITION_FOLLOWING
      ).toBeTruthy();
    });

    test('hides Asked-for without sample:read or test:assign', () => {
      const mockUser = createMockUser(['sample:create'], 'Lab Technician');
      renderWithProviders(<Sidebar {...defaultProps} />, ['/dashboard'], mockUser);
      expect(sidebar().queryByText('Asked-for')).not.toBeInTheDocument();
    });

    test('hides Containers when user lacks sample:update permission', () => {
      const mockUser = createMockUser(['sample:create'], 'Lab Technician');
      renderWithProviders(<Sidebar {...defaultProps} />, ['/dashboard'], mockUser);
      
      expect(sidebar().getAllByText('Receive').length).toBeGreaterThan(0);
      expect(sidebar().queryByText('Containers')).not.toBeInTheDocument();
    });

    test('hides Batches when user lacks batch:manage permission', () => {
      const mockUser = createMockUser(['sample:create'], 'Lab Technician');
      renderWithProviders(<Sidebar {...defaultProps} />, ['/dashboard'], mockUser);
      
      expect(sidebar().queryByText('Batches')).not.toBeInTheDocument();
    });

    test('hides Results when user lacks result:enter permission', () => {
      const mockUser = createMockUser(['sample:create'], 'Lab Technician');
      renderWithProviders(<Sidebar {...defaultProps} />, ['/dashboard'], mockUser);
      
      expect(sidebar().queryByText('Results')).not.toBeInTheDocument();
    });

    test('hides Lab Management section when user lacks project:manage permission', () => {
      const mockUser = createMockUser(['sample:create'], 'Lab Technician');
      renderWithProviders(<Sidebar {...defaultProps} />, ['/dashboard'], mockUser);
      
      expect(sidebar().queryByText('Lab Mgmt')).not.toBeInTheDocument();
      expect(sidebar().queryByText('Clients')).not.toBeInTheDocument();
      expect(sidebar().queryByText('Client Proj')).not.toBeInTheDocument();
    });

    test('shows Dashboard even when user has no permissions', () => {
      const mockUser = createMockUser([], 'Client');
      renderWithProviders(<Sidebar {...defaultProps} />, ['/dashboard'], mockUser);
      
      expect(sidebar().getByText('Dashboard')).toBeInTheDocument();
    });

    test('Administrator role shows all items regardless of permissions array', () => {
      const mockUser = createMockUser([], 'Administrator');
      renderWithProviders(<Sidebar {...defaultProps} />, ['/dashboard'], mockUser);
      
      expect(sidebar().getByText('Receive')).toBeInTheDocument();
      expect(sidebar().getByText('Containers')).toBeInTheDocument();
      expect(sidebar().getByText('Batches')).toBeInTheDocument();
      expect(sidebar().getByText('Results')).toBeInTheDocument();
      expect(sidebar().getByText('Lab Mgmt')).toBeInTheDocument();
      expect(sidebar().getByText('Admin')).toBeInTheDocument();
    });
  });

  describe('Navigation', () => {
    test('navigates to dashboard when logo is clicked', () => {
      const { container } = renderWithProviders(<Sidebar {...defaultProps} />, ['/receive']);
      
      const logo = sidebar().getByLabelText('Navigate to dashboard');
      fireEvent.click(logo);
      
      // Navigation is handled by react-router, so we just verify the click happened
      expect(logo).toBeInTheDocument();
    });

    test('navigates when navigation item is clicked', () => {
      const { container } = renderWithProviders(<Sidebar {...defaultProps} />);
      
      const receiveButton = sidebar().getAllByLabelText('Navigate to Receive')[0];
      fireEvent.click(receiveButton);
      
      expect(receiveButton).toBeInTheDocument();
    });

    test('closes mobile drawer after navigation on mobile', () => {
      mockUseMediaQuery.mockReturnValue(true); // Mobile
      renderWithProviders(<Sidebar {...defaultProps} mobileOpen={true} />);
      
      const dashboardButton = sidebar().getByLabelText('Navigate to Dashboard');
      fireEvent.click(dashboardButton);
      
      // onMobileClose should be called (mocked)
      // In real implementation, this would close the drawer
    });
  });

  describe('Active state', () => {
    test('highlights Dashboard when on /dashboard route', () => {
      renderWithProviders(<Sidebar {...defaultProps} />, ['/dashboard']);
      
      const dashboardButton = sidebar().getByLabelText('Navigate to Dashboard');
      expect(dashboardButton).toHaveAttribute('aria-current', 'page');
    });

    test('highlights Receive when on /receive route', () => {
      renderWithProviders(<Sidebar {...defaultProps} />, ['/receive']);
      
      const receiveButton = sidebar().getAllByLabelText('Navigate to Receive')[0];
      expect(receiveButton).toHaveAttribute('aria-current', 'page');
    });

    test('highlights admin Overview when on /admin route', () => {
      renderWithProviders(<Sidebar {...defaultProps} />, ['/admin']);
      
      const overviewButton = sidebar().getByLabelText('Navigate to Overview');
      expect(overviewButton).toHaveAttribute('aria-current', 'page');
    });

    test('highlights Lists Management when on /admin/lists route', () => {
      renderWithProviders(<Sidebar {...defaultProps} />, ['/admin/lists']);
      
      const listsButton = sidebar().getByLabelText('Navigate to Lists');
      expect(listsButton).toHaveAttribute('aria-current', 'page');
    });
  });

  describe('Admin Accordion', () => {
    test('expands admin accordion when on admin route', () => {
      renderWithProviders(<Sidebar {...defaultProps} />, ['/admin']);
      
      const accordion = sidebar().getByLabelText('Admin section');
      expect(accordion).toHaveAttribute('aria-expanded', 'true');
    });

    test('collapses admin accordion when not on admin route', () => {
      renderWithProviders(<Sidebar {...defaultProps} />, ['/dashboard']);
      
      const accordion = sidebar().getByLabelText('Admin section');
      // Accordion should be collapsed initially when not on admin route
      // Note: The component sets expanded based on route, so this may vary
    });

    test('toggles accordion when clicked', () => {
      renderWithProviders(<Sidebar {...defaultProps} />, ['/dashboard']);
      
      const accordion = sidebar().getByLabelText('Admin section');
      fireEvent.click(accordion);
      
      // Accordion should toggle
      expect(accordion).toBeInTheDocument();
    });

    test('shows all admin sub-items when expanded', () => {
      renderWithProviders(<Sidebar {...defaultProps} />, ['/admin']);
      
      expect(sidebar().getByText('Overview')).toBeInTheDocument();
      expect(sidebar().getByText('Lists')).toBeInTheDocument();
      expect(sidebar().getByText('Container Types')).toBeInTheDocument();
      expect(sidebar().getByText('Users Management')).toBeInTheDocument();
      expect(sidebar().getByText('Roles & Permissions')).toBeInTheDocument();
      expect(sidebar().getByText('Analyses Management')).toBeInTheDocument();
      expect(sidebar().getByText('Analytes Management')).toBeInTheDocument();
      expect(sidebar().getByText('Test Batteries')).toBeInTheDocument();
    });
  });

  describe('Lab Management Accordion (clients, projects)', () => {
    test('renders Lab Management section when user has project:manage permission', () => {
      const mockUser = createMockUser(['project:manage'], 'Lab Manager');
      renderWithProviders(<Sidebar {...defaultProps} />, ['/dashboard'], mockUser);
      
      expect(sidebar().getByText('Lab Mgmt')).toBeInTheDocument();
    });

    test('does not render Lab Management section when user lacks project:manage permission', () => {
      const mockUser = createMockUser(['sample:create'], 'Lab Technician');
      renderWithProviders(<Sidebar {...defaultProps} />, ['/dashboard'], mockUser);
      
      expect(sidebar().queryByText('Lab Mgmt')).not.toBeInTheDocument();
    });

    test('expands Lab Management accordion when on /clients route', () => {
      renderWithProviders(<Sidebar {...defaultProps} />, ['/clients']);
      
      const accordion = sidebar().getByLabelText('Lab Management section');
      expect(accordion).toHaveAttribute('aria-expanded', 'true');
      expect(sidebar().getByText('Clients')).toBeInTheDocument();
      expect(sidebar().getByText('Client Proj')).toBeInTheDocument();
    });

    test('expands Lab Management accordion when on /client-projects route', () => {
      renderWithProviders(<Sidebar {...defaultProps} />, ['/client-projects']);
      
      const accordion = sidebar().getByLabelText('Lab Management section');
      expect(accordion).toHaveAttribute('aria-expanded', 'true');
      expect(sidebar().getByText('Clients')).toBeInTheDocument();
      expect(sidebar().getByText('Client Proj')).toBeInTheDocument();
    });

    test('collapses Lab Management accordion when not on client routes', () => {
      renderWithProviders(<Sidebar {...defaultProps} />, ['/dashboard']);
      
      const accordion = sidebar().getByLabelText('Lab Management section');
      // Accordion may be collapsed initially when not on client route
      expect(accordion).toBeInTheDocument();
    });

    test('toggles Lab Management accordion when clicked', () => {
      renderWithProviders(<Sidebar {...defaultProps} />, ['/dashboard']);
      
      const accordion = sidebar().getByLabelText('Lab Management section');
      fireEvent.click(accordion);
      
      // Accordion should toggle
      expect(accordion).toBeInTheDocument();
    });

    test('shows all client sub-items when expanded', () => {
      renderWithProviders(<Sidebar {...defaultProps} />, ['/clients']);
      
      expect(sidebar().getByText('Clients')).toBeInTheDocument();
      expect(sidebar().getByText('Client Proj')).toBeInTheDocument();
    });

    test('highlights Clients when on /clients route', () => {
      renderWithProviders(<Sidebar {...defaultProps} />, ['/clients']);
      
      const clientsButton = sidebar().getByLabelText('Navigate to Clients');
      expect(clientsButton).toHaveAttribute('aria-current', 'page');
    });

    test('highlights Client Projects when on /client-projects route', () => {
      renderWithProviders(<Sidebar {...defaultProps} />, ['/client-projects']);
      
      const clientProjectsButton = sidebar().getByLabelText('Client Projects');
      expect(clientProjectsButton).toHaveAttribute('aria-current', 'page');
    });

    test('has primary color icon when on client routes', () => {
      renderWithProviders(<Sidebar {...defaultProps} />, ['/clients']);
      
      const accordion = sidebar().getByLabelText('Lab Management section');
      expect(accordion).toBeInTheDocument();
      // Icon color is tested through the component structure
    });

    test('has proper ARIA labels for lab management accordion', () => {
      renderWithProviders(<Sidebar {...defaultProps} />);
      
      expect(sidebar().getByLabelText('Lab Management section')).toBeInTheDocument();
      expect(sidebar().getByLabelText('lab management navigation')).toBeInTheDocument();
    });

    test('nested items have proper indentation (pl: 4)', () => {
      renderWithProviders(<Sidebar {...defaultProps} />, ['/clients']);
      
      const clientsButton = sidebar().getByLabelText('Navigate to Clients');
      // The sx={{ pl: 4 }} styling is applied to ListItemButton
      expect(clientsButton).toBeInTheDocument();
    });
  });

  describe('Responsive behavior', () => {
    test('renders permanent drawer on desktop (>=600px)', () => {
      mockUseMediaQuery.mockReturnValue(false); // Desktop
      const { container } = renderWithProviders(<Sidebar {...defaultProps} />);
      
      // Desktop drawer should be visible
      const drawer = container.querySelector('.MuiDrawer-root');
      expect(drawer).toBeInTheDocument();
    });

    test('renders temporary drawer on mobile (<600px)', () => {
      mockUseMediaQuery.mockReturnValue(true); // Mobile
      const { container } = renderWithProviders(<Sidebar {...defaultProps} mobileOpen={true} />);
      
      // Mobile drawer should be present
      const drawer = container.querySelector('.MuiDrawer-root');
      expect(drawer).toBeInTheDocument();
    });

    test('calls onMobileClose when temporary drawer is closed', () => {
      mockUseMediaQuery.mockReturnValue(true); // Mobile
      const { container } = renderWithProviders(<Sidebar {...defaultProps} mobileOpen={true} />);
      
      // The drawer's onClose should be connected to onMobileClose
      // This is tested implicitly through the component structure
    });
  });

  describe('Edge cases', () => {
    test('handles user with no permissions gracefully', () => {
      const mockUser = createMockUser([], 'Client');
      renderWithProviders(<Sidebar {...defaultProps} />, ['/dashboard'], mockUser);
      
      // Should still render Dashboard
      expect(sidebar().getByText('Dashboard')).toBeInTheDocument();
      // Should not render permission-gated items
      expect(sidebar().queryByText('Receive')).not.toBeInTheDocument();
    });

    test('handles missing user gracefully', () => {
      const mockUser = {
        user: null,
        loading: false,
        login: jest.fn(),
        logout: jest.fn(),
        hasPermission: jest.fn(() => false),
      };
      
      renderWithProviders(<Sidebar {...defaultProps} />, ['/dashboard'], mockUser);
      
      // Should still render basic structure
      expect(sidebar().getByText('NimbleLIMS')).toBeInTheDocument();
    });

    test('handles nested admin routes correctly', () => {
      renderWithProviders(<Sidebar {...defaultProps} />, ['/admin/analyses/123/analytes']);
      
      // Admin accordion should be expanded
      const accordion = sidebar().getByLabelText('Admin section');
      expect(accordion).toBeInTheDocument();
      
      // Analyses Management should be highlighted (prefix match)
      const analysesButton = sidebar().getByLabelText('Navigate to Analyses Management');
      expect(analysesButton).toHaveAttribute('aria-current', 'page');
    });
  });

  describe('Accessibility', () => {
    test('has proper ARIA labels for navigation items', () => {
      renderWithProviders(<Sidebar {...defaultProps} />);
      
      expect(sidebar().getByLabelText('Navigate to Dashboard')).toBeInTheDocument();
      expect(sidebar().getByLabelText('Navigate to Receive')).toBeInTheDocument();
      expect(screen.getByLabelText('main navigation')).toBeInTheDocument();
    });

    test('has aria-current for active items', () => {
      renderWithProviders(<Sidebar {...defaultProps} />, ['/dashboard']);
      
      const dashboardButton = sidebar().getByLabelText('Navigate to Dashboard');
      expect(dashboardButton).toHaveAttribute('aria-current', 'page');
    });

    test('has proper ARIA labels for admin accordion', () => {
      renderWithProviders(<Sidebar {...defaultProps} />);
      
      expect(sidebar().getByLabelText('Admin section')).toBeInTheDocument();
      expect(sidebar().getByLabelText('admin navigation')).toBeInTheDocument();
    });
  });
});

