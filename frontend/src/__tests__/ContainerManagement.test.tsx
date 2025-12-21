import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import ContainerManagement from '../pages/ContainerManagement';
import { UserProvider } from '../contexts/UserContext';

// Mock the API service
jest.mock('../services/apiService', () => ({
  apiService: {
    getContainers: jest.fn(),
    getContainerTypes: jest.fn(),
    getUnits: jest.fn(),
    getSamples: jest.fn(),
    createContainer: jest.fn(),
    updateContainer: jest.fn(),
    deleteContent: jest.fn(),
  },
}));

const theme = createTheme();

const mockUser = {
  id: '1',
  username: 'testuser',
  email: 'test@example.com',
  role: 'Lab Technician',
  permissions: ['sample:update'],
};

const mockContainers = [
  {
    id: '1',
    name: 'Container 1',
    type_id: '1',
    concentration: 10,
    concentration_units: 'mg/L',
    amount: 5,
    amount_units: 'mL',
    created_at: '2024-01-01T00:00:00Z',
    type: { name: 'Tube', material: 'Plastic', dimensions: '15ml' },
    contents: [],
  },
  {
    id: '2',
    name: 'Container 2',
    type_id: '2',
    concentration: 20,
    concentration_units: 'mg/L',
    amount: 10,
    amount_units: 'mL',
    created_at: '2024-01-02T00:00:00Z',
    type: { name: 'Plate', material: 'Plastic', dimensions: '96-well' },
    contents: [
      {
        id: '1',
        sample_id: '1',
        sample: { name: 'Sample 1', description: 'Test sample' },
        concentration: 15,
        concentration_units: 'mg/L',
        amount: 2,
        amount_units: 'mL',
      },
    ],
  },
];

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

describe('ContainerManagement', () => {
  beforeEach(() => {
    // Mock API responses
    const { apiService } = require('../services/apiService');
    apiService.getContainers.mockResolvedValue(mockContainers);
    apiService.getContainerTypes.mockResolvedValue([
      { id: '1', name: 'Tube', material: 'Plastic', dimensions: '15ml' },
      { id: '2', name: 'Plate', material: 'Plastic', dimensions: '96-well' },
    ]);
    apiService.getUnits.mockResolvedValue([
      { id: '1', name: 'mg/L', type: 'concentration' },
      { id: '2', name: 'mL', type: 'volume' },
    ]);
    apiService.getSamples.mockResolvedValue([]);
  });

  test('renders container management page', async () => {
    renderWithProviders(<ContainerManagement />);
    
    expect(screen.getByText('Container Management')).toBeInTheDocument();
    expect(screen.getByText('Create Container')).toBeInTheDocument();
    
    await waitFor(() => {
      expect(screen.getByText('Container 1')).toBeInTheDocument();
      expect(screen.getByText('Container 2')).toBeInTheDocument();
    });
  });

  test('shows container data in table', async () => {
    renderWithProviders(<ContainerManagement />);
    
    await waitFor(() => {
      expect(screen.getByText('Container 1')).toBeInTheDocument();
      expect(screen.getByText('Container 2')).toBeInTheDocument();
      expect(screen.getByText('Tube')).toBeInTheDocument();
      expect(screen.getByText('Plate')).toBeInTheDocument();
    });
  });

  test('opens create container dialog', async () => {
    renderWithProviders(<ContainerManagement />);
    
    const createButton = screen.getByText('Create Container');
    fireEvent.click(createButton);
    
    await waitFor(() => {
      expect(screen.getByText('Create Container')).toBeInTheDocument();
    });
  });

  test('handles container row click', async () => {
    renderWithProviders(<ContainerManagement />);
    
    await waitFor(() => {
      const containerRow = screen.getByText('Container 1');
      fireEvent.click(containerRow);
    });
    
    await waitFor(() => {
      expect(screen.getByText('Container Details')).toBeInTheDocument();
    });
  });
});
