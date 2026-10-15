import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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
  // Plain function, not jest.fn: CRA's resetMocks would wipe the implementation.
  hasPermission: ((perm: string) => {
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

const mockContainerTypes = [{ id: 'ct1', name: 'Vial' }];
const mockMatrixTypes = [{ id: 'm1', name: 'Water' }];

// Multi-step wizard flows with MUI Selects/Autocompletes are slow under jsdom.
jest.setTimeout(30000);

type User = ReturnType<typeof userEvent.setup>;

const renderComponent = () => {
  return render(
    <BrowserRouter>
      <BatchManagement />
    </BrowserRouter>
  );
};

const setupMocks = () => {
  jest.clearAllMocks();
  mockUseUser.mockReturnValue(mockUser as any);
  mockApiService.getProjects.mockResolvedValue(mockProjects);
  mockApiService.getContainers.mockResolvedValue(mockContainers);
  mockApiService.getListEntries.mockImplementation((listName: string) => {
    if (listName === 'batch_status') return Promise.resolve(mockBatchStatuses);
    if (listName === 'batch_types') return Promise.resolve(mockBatchTypes);
    if (listName === 'qc_types') return Promise.resolve(mockQCTypes);
    if (listName === 'matrix_types') return Promise.resolve(mockMatrixTypes);
    return Promise.resolve([]);
  });
  // /analyses is paginated: {analyses, total, ...}
  mockApiService.getAnalyses.mockResolvedValue({ analyses: mockAnalyses, total: 2, page: 1, size: 10, pages: 1 } as any);
  mockApiService.getContainerTypes.mockResolvedValue(mockContainerTypes as any);
  mockApiService.getBatches.mockResolvedValue([]);
  mockApiService.getEligibleSamples.mockResolvedValue({ samples: [], total: 0, page: 1, size: 100, pages: 0, warnings: [] } as any);
  mockApiService.validateBatchCompatibility.mockResolvedValue({ compatible: true } as any);
  mockApiService.createBatch.mockResolvedValue({ id: 'batch1', name: 'Test Batch', containers: [] } as any);
};

// The list view's "Create Batch" button opens the 4-step creation wizard.
const openCreateForm = async (user: User) => {
  await user.click(await screen.findByRole('button', { name: /create batch/i }));
  await screen.findByLabelText('Batch name');
};

// Step 1 (Batch Details): name is required; status defaults to "Created" once list entries load.
const fillDetailsAndNext = async (user: User, name = 'Test Batch') => {
  await user.type(screen.getByLabelText('Batch name'), name);
  const next = screen.getByRole('button', { name: 'Next' });
  await waitFor(() => expect(next).toBeEnabled());
  await user.click(next);
  await screen.findByText('Cross-Project Container Selection');
};

// Step 2: add containers through the "Search and Add Containers" autocomplete.
const addContainer = async (user: User, containerName: string) => {
  await user.click(screen.getByLabelText('Search containers'));
  const options = await screen.findAllByRole('option');
  const option = options.find((o) => o.textContent?.startsWith(containerName));
  expect(option).toBeDefined();
  await user.click(option as HTMLElement);
};

const addBothContainers = async (user: User) => {
  await waitFor(() => expect(mockApiService.getContainers).toHaveBeenCalled());
  await addContainer(user, 'Container 1');
  await addContainer(user, 'Container 2');
  await screen.findByText('Selected Containers (2)');
};

const goToQcStep = async (user: User) => {
  await openCreateForm(user);
  await fillDetailsAndNext(user);
  await user.click(screen.getByRole('button', { name: 'Next' }));
  await screen.findByRole('heading', { name: 'QC Samples' });
};

// MUI Select: open the listbox and pick an option.
const pickOption = async (user: User, combobox: HTMLElement, optionName: string) => {
  await user.click(combobox);
  const listbox = await screen.findByRole('listbox');
  await user.click(within(listbox).getByRole('option', { name: optionName }));
};

describe('BatchManagement - Cross-Project Support', () => {
  beforeEach(setupMocks);

  it('renders batch management page', async () => {
    renderComponent();

    expect(await screen.findByRole('heading', { name: /batches/i })).toBeInTheDocument();
  });

  it('displays create batch button', async () => {
    renderComponent();

    expect(await screen.findByRole('button', { name: /create batch/i })).toBeInTheDocument();
  });

  it('opens batch creation form when create button is clicked', async () => {
    const user = userEvent.setup({ delay: null });
    renderComponent();
    await openCreateForm(user);

    expect(screen.getAllByText(/create new batch/i).length).toBeGreaterThan(0);
    expect(screen.getByText('Batch Details')).toBeInTheDocument();
  });

  it('loads accessible projects for cross-project selection', async () => {
    const user = userEvent.setup({ delay: null });
    renderComponent();
    await openCreateForm(user);

    await waitFor(() => {
      expect(mockApiService.getProjects).toHaveBeenCalled();
    });
  });

  it('allows selecting multiple projects for container filtering', async () => {
    const user = userEvent.setup({ delay: null });
    renderComponent();
    await openCreateForm(user);
    await fillDetailsAndNext(user);

    // All accessible projects are pre-selected for cross-project batching.
    const projectsSelect = screen.getByRole('combobox', { name: /filter by projects/i });
    expect(within(projectsSelect).getByText('Project A')).toBeInTheDocument();
    expect(within(projectsSelect).getByText('Project B')).toBeInTheDocument();
  });

  it('loads containers when projects are selected', async () => {
    const user = userEvent.setup({ delay: null });
    renderComponent();
    await openCreateForm(user);

    await waitFor(() => {
      expect(mockApiService.getContainers).toHaveBeenCalledWith({ project_ids: ['project1', 'project2'] });
    });
  });

  it('allows searching and adding containers via Autocomplete', async () => {
    const user = userEvent.setup({ delay: null });
    renderComponent();
    await openCreateForm(user);
    await fillDetailsAndNext(user);

    expect(screen.getByPlaceholderText(/search containers/i)).toBeInTheDocument();
    await addBothContainers(user);
    expect(screen.getByText('Container 1 (Project A)')).toBeInTheDocument();
    expect(screen.getByText('Container 2 (Project B)')).toBeInTheDocument();
  });

  it('validates compatibility when validate button is clicked', async () => {
    mockApiService.validateBatchCompatibility.mockResolvedValue({
      compatible: true,
      details: {
        projects: ['project1', 'project2'],
        common_analyses: ['EPA Method 8080 Prep'],
      },
    } as any);

    const user = userEvent.setup({ delay: null });
    renderComponent();
    await openCreateForm(user);
    await fillDetailsAndNext(user);
    await addBothContainers(user);
    await user.click(screen.getByRole('button', { name: /validate compatibility/i }));

    await waitFor(() => {
      expect(mockApiService.validateBatchCompatibility).toHaveBeenCalledWith({
        container_ids: ['container1', 'container2'],
      });
    });
  });

  it('displays compatibility validation results', async () => {
    mockApiService.validateBatchCompatibility.mockResolvedValue({
      compatible: true,
      details: {
        projects: ['project1', 'project2'],
        common_analyses: ['EPA Method 8080 Prep'],
      },
    } as any);

    const user = userEvent.setup({ delay: null });
    renderComponent();
    await openCreateForm(user);
    await fillDetailsAndNext(user);
    await addBothContainers(user);
    await user.click(screen.getByRole('button', { name: /validate compatibility/i }));

    expect(await screen.findByText('Containers are compatible for cross-project batching')).toBeInTheDocument();
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
    } as any);

    const user = userEvent.setup({ delay: null });
    renderComponent();
    await openCreateForm(user);
    await fillDetailsAndNext(user);
    await addBothContainers(user);
    await user.click(screen.getByRole('button', { name: /validate compatibility/i }));

    expect(await screen.findByText(/Incompatible samples: no shared analyses found/)).toBeInTheDocument();
    expect(screen.getByText('Samples must share at least one common analysis')).toBeInTheDocument();
  });

  it('allows opening sub-batch creation dialog', async () => {
    const user = userEvent.setup({ delay: null });
    renderComponent();
    await openCreateForm(user);
    await fillDetailsAndNext(user);
    await addBothContainers(user);

    await user.click(screen.getByRole('button', { name: /create sub-batches/i }));
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
  });

  it('displays analyses in sub-batch dialog', async () => {
    const user = userEvent.setup({ delay: null });
    renderComponent();
    await openCreateForm(user);
    await fillDetailsAndNext(user);
    await addBothContainers(user);
    await user.click(screen.getByRole('button', { name: /create sub-batches/i }));

    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText(/divergent analyses/i)).toBeInTheDocument();
    expect(within(dialog).getByText('EPA Method 8080 Prep')).toBeInTheDocument();
  });

  it('creates batch with cross-project containers', async () => {
    mockApiService.createBatch.mockResolvedValue({
      id: 'batch1',
      name: 'Cross-Project Batch',
      container_ids: ['container1', 'container2'],
      cross_project: true,
    } as any);

    const user = userEvent.setup({ delay: null });
    renderComponent();
    await openCreateForm(user);
    await fillDetailsAndNext(user, 'Cross-Project Batch');
    await addBothContainers(user);
    await user.click(screen.getByRole('button', { name: 'Next' })); // -> QC
    await screen.findByRole('heading', { name: 'QC Samples' });
    await user.click(screen.getByRole('button', { name: 'Next' })); // -> Review
    await screen.findByText('Review Batch');
    await user.click(screen.getByRole('button', { name: 'Create Batch' }));

    await waitFor(() => {
      expect(mockApiService.createBatch).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Cross-Project Batch',
          container_ids: ['container1', 'container2'],
          cross_project: true,
        })
      );
    });
  });

  it('auto-detects cross-project when containers from multiple projects are selected', async () => {
    const user = userEvent.setup({ delay: null });
    renderComponent();
    await openCreateForm(user);
    await fillDetailsAndNext(user);
    await addBothContainers(user);

    expect(await screen.findByText(/Cross-project batch detected/)).toBeInTheDocument();
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

    const user = userEvent.setup({ delay: null });
    renderComponent();
    await openCreateForm(user);
    await fillDetailsAndNext(user);
    await addBothContainers(user);
    await user.click(screen.getByRole('button', { name: /validate compatibility/i }));

    expect(await screen.findByText('Incompatible samples: no shared analyses found')).toBeInTheDocument();
  });
});

describe('BatchManagement - QC Integration', () => {
  beforeEach(setupMocks);

  it('displays QC section in batch creation form', async () => {
    const user = userEvent.setup({ delay: null });
    renderComponent();
    await goToQcStep(user);

    expect(screen.getByRole('button', { name: /add qc/i })).toBeInTheDocument();
  });

  it('allows adding multiple QC samples', async () => {
    const user = userEvent.setup({ delay: null });
    renderComponent();
    await goToQcStep(user);

    const addQCButton = screen.getByRole('button', { name: /add qc/i });
    await user.click(addQCButton);
    expect(await screen.findByText('QC Sample 1')).toBeInTheDocument();
    expect(screen.getByLabelText('QC type for sample 1')).toBeInTheDocument();

    await user.click(addQCButton);
    expect(await screen.findByText('QC Sample 2')).toBeInTheDocument();
  });

  it('allows selecting QC type from dropdown', async () => {
    const user = userEvent.setup({ delay: null });
    renderComponent();
    await goToQcStep(user);
    await user.click(screen.getByRole('button', { name: /add qc/i }));

    await user.click(await screen.findByRole('combobox', { name: /^QC Type/ }));
    const listbox = await screen.findByRole('listbox');
    expect(within(listbox).getByRole('option', { name: 'Blank' })).toBeInTheDocument();
    expect(within(listbox).getByRole('option', { name: 'Matrix Spike' })).toBeInTheDocument();
  });

  it('allows adding notes to QC samples', async () => {
    const user = userEvent.setup({ delay: null });
    renderComponent();
    await goToQcStep(user);
    await user.click(screen.getByRole('button', { name: /add qc/i }));

    const notesField = await screen.findByLabelText('Notes for QC sample 1');
    await user.type(notesField, 'Test QC notes');
    expect(notesField).toHaveValue('Test QC notes');
  });

  it('includes QC additions in batch creation payload', async () => {
    const user = userEvent.setup({ delay: null });
    renderComponent();
    await goToQcStep(user);
    await user.click(screen.getByRole('button', { name: /add qc/i }));

    // QC type, container type and matrix are all required for a QC addition.
    await pickOption(user, await screen.findByRole('combobox', { name: /^QC Type/ }), 'Blank');
    await pickOption(user, screen.getByRole('combobox', { name: /^Container Type/ }), 'Vial');
    await pickOption(user, screen.getByRole('combobox', { name: /^Matrix/ }), 'Water');
    await user.type(screen.getByLabelText('Notes for QC sample 1'), 'Test notes');

    await user.click(screen.getByRole('button', { name: 'Next' }));
    await screen.findByText('Review Batch');
    await user.click(screen.getByRole('button', { name: 'Create Batch' }));

    await waitFor(() => {
      expect(mockApiService.createBatch).toHaveBeenCalledWith(
        expect.objectContaining({
          qc_additions: [
            { qc_type: 'qc1', container_type_id: 'ct1', matrix_id: 'm1', notes: 'Test notes' },
          ],
        })
      );
    });
  });

  it('validates QC requirement for specific batch types', async () => {
    // The QC requirement is read from the environment when the form mounts.
    const originalEnv = process.env.REACT_APP_REQUIRE_QC_FOR_BATCH_TYPES;
    process.env.REACT_APP_REQUIRE_QC_FOR_BATCH_TYPES = 'type2';

    try {
      const user = userEvent.setup({ delay: null });
      renderComponent();
      await openCreateForm(user);
      // Wait for list entries (the default "Created" status) before opening the type menu.
      await screen.findByText('Created');

      await pickOption(user, screen.getByRole('combobox', { name: /^Batch Type/ }), 'QC Required Batch');
      await fillDetailsAndNext(user);
      await user.click(screen.getByRole('button', { name: 'Next' })); // -> QC
      expect(await screen.findByText(/QC samples are required for batch type "QC Required Batch"/)).toBeInTheDocument();

      await user.click(screen.getByRole('button', { name: 'Next' })); // -> Review
      await screen.findByText('Review Batch');
      await user.click(screen.getByRole('button', { name: 'Create Batch' }));

      expect(await screen.findByText(/QC samples are required for this batch type/)).toBeInTheDocument();
      expect(mockApiService.createBatch).not.toHaveBeenCalled();
    } finally {
      if (originalEnv) {
        process.env.REACT_APP_REQUIRE_QC_FOR_BATCH_TYPES = originalEnv;
      } else {
        delete process.env.REACT_APP_REQUIRE_QC_FOR_BATCH_TYPES;
      }
    }
  });

  it('allows removing QC samples', async () => {
    const user = userEvent.setup({ delay: null });
    renderComponent();
    await goToQcStep(user);
    await user.click(screen.getByRole('button', { name: /add qc/i }));
    expect(await screen.findByText('QC Sample 1')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Remove QC sample 1' }));

    await waitFor(() => {
      expect(screen.queryByText('QC Sample 1')).not.toBeInTheDocument();
    });
  });
});
