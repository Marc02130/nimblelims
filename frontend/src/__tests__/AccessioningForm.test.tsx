import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import AccessioningForm from '../pages/AccessioningForm';
import { UserProvider } from '../contexts/UserContext';

// Mock the API service
jest.mock('../services/apiService', () => ({
  apiService: {
    getListEntries: jest.fn(),
    getProjects: jest.fn(),
    getAnalyses: jest.fn(),
    getContainerTypes: jest.fn(),
    getUnits: jest.fn(),
    createSample: jest.fn(),
    createContainer: jest.fn(),
    createContent: jest.fn(),
    createTest: jest.fn(),
  },
}));

const theme = createTheme();

const mockUser = {
  id: '1',
  username: 'testuser',
  email: 'test@example.com',
  role: 'Lab Technician',
  permissions: ['sample:create', 'test:assign'],
};

const mockLookupData = {
  sampleTypes: [
    { id: '1', name: 'Blood' },
    { id: '2', name: 'Urine' },
  ],
  statuses: [
    { id: '1', name: 'Received' },
    { id: '2', name: 'Available for Testing' },
  ],
  matrices: [
    { id: '1', name: 'Serum' },
    { id: '2', name: 'Plasma' },
  ],
  qcTypes: [
    { id: '1', name: 'Sample' },
    { id: '2', name: 'Control' },
  ],
  projects: [
    { id: '1', name: 'Project A' },
    { id: '2', name: 'Project B' },
  ],
  analyses: [
    { id: '1', name: 'Analysis A', method: 'Method A', turnaround_time: 1, cost: 100 },
    { id: '2', name: 'Analysis B', method: 'Method B', turnaround_time: 2, cost: 200 },
  ],
  containerTypes: [
    { id: '1', name: 'Tube', material: 'Plastic', dimensions: '15ml' },
    { id: '2', name: 'Plate', material: 'Plastic', dimensions: '96-well' },
  ],
  units: [
    { id: '1', name: 'mg/L', type: 'concentration' },
    { id: '2', name: 'mL', type: 'volume' },
  ],
};

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

describe('AccessioningForm', () => {
  beforeEach(() => {
    // Mock API responses
    const { apiService } = require('../services/apiService');
    apiService.getListEntries.mockResolvedValue([]);
    apiService.getProjects.mockResolvedValue([]);
    apiService.getAnalyses.mockResolvedValue([]);
    apiService.getContainerTypes.mockResolvedValue([]);
    apiService.getUnits.mockResolvedValue([]);
  });

  test('renders accessioning form with stepper', () => {
    renderWithProviders(<AccessioningForm />);
    
    expect(screen.getByText('Sample Accessioning')).toBeInTheDocument();
    expect(screen.getByText('Sample Details')).toBeInTheDocument();
    expect(screen.getByText('Test Assignment')).toBeInTheDocument();
    expect(screen.getByText('Review & Submit')).toBeInTheDocument();
  });

  test('shows sample details step initially', () => {
    renderWithProviders(<AccessioningForm />);
    
    expect(screen.getByLabelText('Sample Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Due Date')).toBeInTheDocument();
    expect(screen.getByLabelText('Received Date')).toBeInTheDocument();
  });

  test('validates required fields', async () => {
    renderWithProviders(<AccessioningForm />);
    
    const submitButton = screen.getByText('Next');
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('Sample name is required')).toBeInTheDocument();
    });
  });

  test('enables double entry validation toggle', () => {
    renderWithProviders(<AccessioningForm />);
    
    const doubleEntryToggle = screen.getByLabelText('Enable Double Entry Validation');
    expect(doubleEntryToggle).toBeInTheDocument();
    
    fireEvent.click(doubleEntryToggle);
    
    expect(screen.getByLabelText('Verify Sample Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Verify Sample Type')).toBeInTheDocument();
  });

  test('navigates to next step when valid', async () => {
    renderWithProviders(<AccessioningForm />);
    
    // Fill required fields
    fireEvent.change(screen.getByLabelText('Sample Name'), { target: { value: 'Test Sample' } });
    fireEvent.change(screen.getByLabelText('Due Date'), { target: { value: '2024-12-31' } });
    fireEvent.change(screen.getByLabelText('Received Date'), { target: { value: '2024-01-01' } });
    
    const nextButton = screen.getByText('Next');
    fireEvent.click(nextButton);
    
    await waitFor(() => {
      expect(screen.getByText('Test Assignment')).toBeInTheDocument();
    });
  });
});
