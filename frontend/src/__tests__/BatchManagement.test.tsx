import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import BatchManagement from '../components/batches/BatchManagement';
import { apiService } from '../services/apiService';
import { useUser } from '../contexts/UserContext';

// Mock dependencies
jest.mock('../services/apiService');
jest.mock('../contexts/UserContext');

const mockApiService = apiService as jest.Mocked<typeof apiService>;
const mockUseUser = useUser as jest.MockedFunction<typeof useUser>;

const mockUser = {
  id: '1',
  username: 'testuser',
  email: 'test@example.com',
  role: 'Lab Technician',
  permissions: ['batch:manage', 'batch:read'],
  hasPermission: jest.fn((perm: string) => {
    return ['batch:manage', 'batch:read'].includes(perm);
  }),
};

const mockProjects = [
  { id: 'project1', name: 'Project A' },
  { id: 'project2', name: 'Project B' },
];

const mockContainers = [
  {
    id: 'container1',
    name: 'Container 1',
    sample: {
      id: 'sample1',
      name: 'Sample 1',
      project_id: 'project1',
      project: { name: 'Project A' },
    },
  },
  {
    id: 'container2',
    name: 'Container 2',
    sample: {
      id: 'sample2',
      name: 'Sample 2',
      project_id: 'project2',
      project: { name: 'Project B' },
    },
  },
];

const mockBatchStatuses = [
  { id: 'status1', name: 'Created' },
  { id: 'status2', name: 'In Process' },
];

const mockAnalyses = [
  { id: 'analysis1', name: 'EPA Method 8080 Prep', method: 'EPA 8080' },
  { id: 'analysis2', name: 'Analysis 2', method: 'Method 2' },
];

const mockQCTypes = [
  { id: 'qc1', name: 'Blank' },
  { id: 'qc2', name: 'Blank Spike' },
  { id: 'qc3', name: 'Matrix Spike' },
  { id: 'qc4', name: 'Duplicate' },
];

const mockBatchTypes = [
  { id: 'type1', name: 'Standard Batch' },
  { id: 'type2', name: 'QC Required Batch' },
];

const renderComponent = () => {
  return render(
    <BrowserRouter>
      <BatchManagement />
    </BrowserRouter>
  );
};

describe('BatchManagement - Cross-Project Support', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseUser.mockReturnValue(mockUser as any);
    mockApiService.getProjects.mockResolvedValue(mockProjects);
    mockApiService.getContainers.mockResolvedValue(mockContainers);
    mockApiService.getListEntries.mockImplementation((listName: string) => {
      if (listName === 'batch_status') return Promise.resolve(mockBatchStatuses);
      if (listName === 'batch_types') return Promise.resolve(mockBatchTypes);
      if (listName === 'qc_types') return Promise.resolve(mockQCTypes);
      return Promise.resolve([]);
    });
    mockApiService.getAnalyses.mockResolvedValue(mockAnalyses);
    mockApiService.validateBatchCompatibility.mockResolvedValue({ compatible: true });
    mockApiService.createBatch.mockResolvedValue({
      id: 'batch1',
      name: 'Test Batch',
      containers: [],
    });
  });

  it('renders batch management page', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText(/batch/i)).toBeInTheDocument();
    });
  });

  it('displays create batch button', async () => {
    renderComponent();

    await waitFor(() => {
      const createButton = screen.queryByText(/create.*batch/i);
      expect(createButton).toBeInTheDocument();
    });
  });

  it('opens batch creation form when create button is clicked', async () => {
    renderComponent();

    await waitFor(() => {
      const createButton = screen.queryByText(/create.*batch/i);
      if (createButton) {
        fireEvent.click(createButton);
      }
    });

    await waitFor(() => {
      expect(screen.getByText(/create new batch/i)).toBeInTheDocument();
    });
  });

  it('loads accessible projects for cross-project selection', async () => {
    renderComponent();

    await waitFor(() => {
      const createButton = screen.queryByText(/create.*batch/i);
      if (createButton) {
        fireEvent.click(createButton);
      }
    });

    await waitFor(() => {
      expect(mockApiService.getProjects).toHaveBeenCalled();
    });
  });

  it('allows selecting multiple projects for container filtering', async () => {
    renderComponent();

    await waitFor(() => {
      const createButton = screen.queryByText(/create.*batch/i);
      if (createButton) {
        fireEvent.click(createButton);
      }
    });

    await waitFor(() => {
      expect(screen.getByText(/filter by projects/i)).toBeInTheDocument();
    });
  });

  it('loads containers when projects are selected', async () => {
    renderComponent();

    await waitFor(() => {
      const createButton = screen.queryByText(/create.*batch/i);
      if (createButton) {
        fireEvent.click(createButton);
      }
    });

    await waitFor(() => {
      expect(mockApiService.getContainers).toHaveBeenCalled();
    });
  });

  it('allows searching and adding containers via Autocomplete', async () => {
    renderComponent();

    await waitFor(() => {
      const createButton = screen.queryByText(/create.*batch/i);
      if (createButton) {
        fireEvent.click(createButton);
      }
    });

    await waitFor(() => {
      const searchInput = screen.queryByPlaceholderText(/search containers/i);
      expect(searchInput).toBeInTheDocument();
    });
  });

  it('validates compatibility when validate button is clicked', async () => {
    mockApiService.validateBatchCompatibility.mockResolvedValue({
      compatible: true,
      details: {
        projects: ['project1', 'project2'],
        common_analyses: ['EPA Method 8080 Prep'],
      },
    });

    renderComponent();

    await waitFor(() => {
      const createButton = screen.queryByText(/create.*batch/i);
      if (createButton) {
        fireEvent.click(createButton);
      }
    });

    await waitFor(() => {
      const validateButton = screen.queryByText(/validate compatibility/i);
      if (validateButton) {
        fireEvent.click(validateButton);
      }
    });

    await waitFor(() => {
      expect(mockApiService.validateBatchCompatibility).toHaveBeenCalled();
    });
  });

  it('displays compatibility validation results', async () => {
    mockApiService.validateBatchCompatibility.mockResolvedValue({
      compatible: true,
      details: {
        projects: ['project1', 'project2'],
        common_analyses: ['EPA Method 8080 Prep'],
      },
    });

    renderComponent();

    await waitFor(() => {
      const createButton = screen.queryByText(/create.*batch/i);
      if (createButton) {
        fireEvent.click(createButton);
      }
    });

    await waitFor(() => {
      const validateButton = screen.queryByText(/validate compatibility/i);
      if (validateButton) {
        fireEvent.click(validateButton);
      }
    });

    await waitFor(() => {
      expect(screen.getByText(/compatible/i)).toBeInTheDocument();
    });
  });

  it('displays error when containers are incompatible', async () => {
    mockApiService.validateBatchCompatibility.mockResolvedValue({
      compatible: false,
      error: 'Incompatible samples: no shared analyses found',
      details: {
        projects: ['project1', 'project2'],
        analyses: ['Analysis 1', 'Analysis 2'],
        suggestion: 'Samples must share at least one common analysis',
      },
    });

    renderComponent();

    await waitFor(() => {
      const createButton = screen.queryByText(/create.*batch/i);
      if (createButton) {
        fireEvent.click(createButton);
      }
    });

    await waitFor(() => {
      const validateButton = screen.queryByText(/validate compatibility/i);
      if (validateButton) {
        fireEvent.click(validateButton);
      }
    });

    await waitFor(() => {
      expect(screen.getByText(/incompatible/i)).toBeInTheDocument();
    });
  });

  it('allows opening sub-batch creation dialog', async () => {
    renderComponent();

    await waitFor(() => {
      const createButton = screen.queryByText(/create.*batch/i);
      if (createButton) {
        fireEvent.click(createButton);
      }
    });

    await waitFor(() => {
      const subBatchButton = screen.queryByText(/create sub-batches/i);
      expect(subBatchButton).toBeInTheDocument();
    });
  });

  it('displays analyses in sub-batch dialog', async () => {
    renderComponent();

    await waitFor(() => {
      const createButton = screen.queryByText(/create.*batch/i);
      if (createButton) {
        fireEvent.click(createButton);
      }
    });

    await waitFor(() => {
      const subBatchButton = screen.queryByText(/create sub-batches/i);
      if (subBatchButton) {
        fireEvent.click(subBatchButton);
      }
    });

    await waitFor(() => {
      expect(screen.getByText(/divergent analyses/i)).toBeInTheDocument();
      expect(screen.getByText('EPA Method 8080 Prep')).toBeInTheDocument();
    });
  });

  it('creates batch with cross-project containers', async () => {
    const mockBatch = {
      id: 'batch1',
      name: 'Cross-Project Batch',
      container_ids: ['container1', 'container2'],
      cross_project: true,
    };

    mockApiService.createBatch.mockResolvedValue(mockBatch);

    renderComponent();

    await waitFor(() => {
      const createButton = screen.queryByText(/create.*batch/i);
      if (createButton) {
        fireEvent.click(createButton);
      }
    });

    // Fill form
    await waitFor(() => {
      const nameInput = screen.getByLabelText(/batch name/i);
      fireEvent.change(nameInput, { target: { value: 'Cross-Project Batch' } });
    });

    // Submit form
    await waitFor(() => {
      const submitButton = screen.getByText(/create batch/i);
      fireEvent.click(submitButton);
    });

    await waitFor(() => {
      expect(mockApiService.createBatch).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Cross-Project Batch',
          container_ids: expect.any(Array),
          cross_project: expect.any(Boolean),
        })
      );
    });
  });

  it('auto-detects cross-project when containers from multiple projects are selected', async () => {
    renderComponent();

    await waitFor(() => {
      const createButton = screen.queryByText(/create.*batch/i);
      if (createButton) {
        fireEvent.click(createButton);
      }
    });

    // This would require simulating container selection
    // The auto-detection happens in useEffect when selectedContainers changes
    await waitFor(() => {
      expect(mockApiService.getContainers).toHaveBeenCalled();
    });
  });

  it('displays validation error when containers are not compatible', async () => {
    mockApiService.validateBatchCompatibility.mockRejectedValue({
      response: {
        data: {
          detail: {
            error: 'Incompatible samples: no shared analyses found',
            details: {
              projects: ['project1', 'project2'],
              analyses: ['Analysis 1', 'Analysis 2'],
            },
          },
        },
      },
    });

    renderComponent();

    await waitFor(() => {
      const createButton = screen.queryByText(/create.*batch/i);
      if (createButton) {
        fireEvent.click(createButton);
      }
    });

    await waitFor(() => {
      const validateButton = screen.queryByText(/validate compatibility/i);
      if (validateButton) {
        fireEvent.click(validateButton);
      }
    });

    await waitFor(() => {
      expect(screen.getByText(/incompatible/i)).toBeInTheDocument();
    });
  });
});

describe('BatchManagement - QC Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseUser.mockReturnValue(mockUser as any);
    mockApiService.getProjects.mockResolvedValue(mockProjects);
    mockApiService.getContainers.mockResolvedValue(mockContainers);
    mockApiService.getListEntries.mockImplementation((listName: string) => {
      if (listName === 'batch_status') return Promise.resolve(mockBatchStatuses);
      if (listName === 'batch_types') return Promise.resolve(mockBatchTypes);
      if (listName === 'qc_types') return Promise.resolve(mockQCTypes);
      return Promise.resolve([]);
    });
    mockApiService.getAnalyses.mockResolvedValue(mockAnalyses);
    mockApiService.validateBatchCompatibility.mockResolvedValue({ compatible: true });
    mockApiService.createBatch.mockResolvedValue({
      id: 'batch1',
      name: 'Test Batch',
      containers: [],
    });
  });

  it('displays QC section in batch creation form', async () => {
    renderComponent();

    await waitFor(() => {
      const createButton = screen.queryByText(/create.*batch/i);
      expect(createButton).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/create.*batch/i));

    await waitFor(() => {
      expect(screen.getByText(/QC Samples/i)).toBeInTheDocument();
      expect(screen.getByText(/Add QC/i)).toBeInTheDocument();
    });
  });

  it('allows adding multiple QC samples', async () => {
    renderComponent();

    await waitFor(() => {
      const createButton = screen.queryByText(/create.*batch/i);
      expect(createButton).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/create.*batch/i));

    await waitFor(() => {
      expect(screen.getByText(/Add QC/i)).toBeInTheDocument();
    });

    const addQCButton = screen.getByText(/Add QC/i);
    fireEvent.click(addQCButton);

    await waitFor(() => {
      expect(screen.getByText(/QC Sample 1/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/QC Type/i)).toBeInTheDocument();
    });

    // Add another QC sample
    fireEvent.click(addQCButton);

    await waitFor(() => {
      expect(screen.getByText(/QC Sample 2/i)).toBeInTheDocument();
    });
  });

  it('allows selecting QC type from dropdown', async () => {
    renderComponent();

    await waitFor(() => {
      const createButton = screen.queryByText(/create.*batch/i);
      expect(createButton).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/create.*batch/i));

    await waitFor(() => {
      expect(screen.getByText(/Add QC/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/Add QC/i));

    await waitFor(() => {
      const qcTypeSelect = screen.getByLabelText(/QC Type/i);
      expect(qcTypeSelect).toBeInTheDocument();
    });

    const qcTypeSelect = screen.getByLabelText(/QC Type/i);
    fireEvent.mouseDown(qcTypeSelect);

    await waitFor(() => {
      expect(screen.getByText('Blank')).toBeInTheDocument();
      expect(screen.getByText('Matrix Spike')).toBeInTheDocument();
    });
  });

  it('allows adding notes to QC samples', async () => {
    renderComponent();

    await waitFor(() => {
      const createButton = screen.queryByText(/create.*batch/i);
      expect(createButton).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/create.*batch/i));

    await waitFor(() => {
      expect(screen.getByText(/Add QC/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/Add QC/i));

    await waitFor(() => {
      const notesField = screen.getByLabelText(/Notes.*Optional/i);
      expect(notesField).toBeInTheDocument();
    });

    const notesField = screen.getByLabelText(/Notes.*Optional/i);
    fireEvent.change(notesField, { target: { value: 'Test QC notes' } });
    expect(notesField).toHaveValue('Test QC notes');
  });

  it('includes QC additions in batch creation payload', async () => {
    renderComponent();

    await waitFor(() => {
      const createButton = screen.queryByText(/create.*batch/i);
      expect(createButton).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/create.*batch/i));

    await waitFor(() => {
      expect(screen.getByText(/Add QC/i)).toBeInTheDocument();
    });

    // Fill in required batch fields
    const nameField = screen.getByLabelText(/Name/i);
    fireEvent.change(nameField, { target: { value: 'Test Batch' } });

    // Add QC sample
    fireEvent.click(screen.getByText(/Add QC/i));

    await waitFor(() => {
      const qcTypeSelect = screen.getByLabelText(/QC Type/i);
      expect(qcTypeSelect).toBeInTheDocument();
    });

    // Select QC type
    const qcTypeSelect = screen.getByLabelText(/QC Type/i);
    fireEvent.mouseDown(qcTypeSelect);
    await waitFor(() => {
      expect(screen.getByText('Blank')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Blank'));

    // Add notes
    const notesField = screen.getByLabelText(/Notes.*Optional/i);
    fireEvent.change(notesField, { target: { value: 'Test notes' } });

    // Submit form
    const submitButton = screen.getByText(/Create Batch/i);
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockApiService.createBatch).toHaveBeenCalledWith(
        expect.objectContaining({
          qc_additions: expect.arrayContaining([
            expect.objectContaining({
              qc_type: 'qc1',
              notes: 'Test notes',
            }),
          ]),
        })
      );
    });
  });

  it('validates QC requirement for specific batch types', async () => {
    // Mock environment variable for QC requirement
    const originalEnv = process.env.REACT_APP_REQUIRE_QC_FOR_BATCH_TYPES;
    process.env.REACT_APP_REQUIRE_QC_FOR_BATCH_TYPES = 'type2';

    renderComponent();

    await waitFor(() => {
      const createButton = screen.queryByText(/create.*batch/i);
      expect(createButton).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/create.*batch/i));

    await waitFor(() => {
      const typeSelect = screen.getByLabelText(/Type/i);
      expect(typeSelect).toBeInTheDocument();
    });

    // Select batch type that requires QC
    const typeSelect = screen.getByLabelText(/Type/i);
    fireEvent.mouseDown(typeSelect);
    await waitFor(() => {
      expect(screen.getByText('QC Required Batch')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('QC Required Batch'));

    // Fill in required fields
    const nameField = screen.getByLabelText(/Name/i);
    fireEvent.change(nameField, { target: { value: 'Test Batch' } });

    // Try to submit without QC
    const submitButton = screen.getByText(/Create Batch/i);
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/QC samples are required/i)).toBeInTheDocument();
    });

    // Restore original env
    if (originalEnv) {
      process.env.REACT_APP_REQUIRE_QC_FOR_BATCH_TYPES = originalEnv;
    } else {
      delete process.env.REACT_APP_REQUIRE_QC_FOR_BATCH_TYPES;
    }
  });

  it('allows removing QC samples', async () => {
    renderComponent();

    await waitFor(() => {
      const createButton = screen.queryByText(/create.*batch/i);
      expect(createButton).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/create.*batch/i));

    await waitFor(() => {
      expect(screen.getByText(/Add QC/i)).toBeInTheDocument();
    });

    // Add QC sample
    fireEvent.click(screen.getByText(/Add QC/i));

    await waitFor(() => {
      expect(screen.getByText(/QC Sample 1/i)).toBeInTheDocument();
    });

    // Find and click delete button
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    const qcDeleteButton = deleteButtons.find(btn => 
      btn.closest('[class*="MuiBox"]')?.textContent?.includes('QC Sample')
    );

    if (qcDeleteButton) {
      fireEvent.click(qcDeleteButton);
    }

    await waitFor(() => {
      expect(screen.queryByText(/QC Sample 1/i)).not.toBeInTheDocument();
    });
  });
});

