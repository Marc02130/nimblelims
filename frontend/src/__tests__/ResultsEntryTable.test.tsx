import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ResultsEntryTable from '../components/results/ResultsEntryTable';
import { apiService } from '../services/apiService';
import { localDateString } from '../utils/localDate';

// Mock the API service
jest.mock('../services/apiService');
const mockApiService = apiService as jest.Mocked<typeof apiService>;

// The table checks workflow:execute via useUser (needs a provider). Plain fn: survives resetMocks.
jest.mock('../contexts/UserContext', () => ({
  useUser: () => ({
    user: { id: 'u1', username: 'tech', role: 'Lab Technician', permissions: ['result:enter'] },
    hasPermission: (perm: string) => perm === 'result:enter',
  }),
}));

const mockSamples = [
  {
    id: 'sample1',
    name: 'Sample 1',
    container_id: 'container1',
    row: 1,
    column: 1,
  },
  {
    id: 'sample2',
    name: 'Sample 2',
    container_id: 'container2',
    row: 1,
    column: 2,
  },
];

const mockAnalytes = [
  {
    id: 'analyte1',
    name: 'pH',
    data_type: 'numeric',
    high_value: 8.5,
    low_value: 6.5,
    significant_figures: 2,
    is_required: true,
    default_value: '7.0',
    reported_name: 'pH',
    display_order: 1,
  },
  {
    id: 'analyte2',
    name: 'Temperature',
    data_type: 'numeric',
    high_value: 25,
    low_value: 20,
    significant_figures: 1,
    is_required: false,
    default_value: '',
    reported_name: 'Temperature (°C)',
    display_order: 2,
  },
];

const mockQualifiers = [
  { id: 'qual1', name: '<' },
  { id: 'qual2', name: '>' },
  { id: 'qual3', name: 'ND' },
];

const defaultProps = {
  batchId: 'batch123',
  testId: 'test123',
  samples: mockSamples,
  onResultsSaved: jest.fn(),
};

describe('ResultsEntryTable', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock API calls
    mockApiService.getAnalysisAnalytes.mockResolvedValue(mockAnalytes);
    mockApiService.getListEntries.mockResolvedValue(mockQualifiers);
  });

  it('renders the results entry table', async () => {
    render(<ResultsEntryTable {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Results Entry')).toBeInTheDocument();
    });

    expect(screen.getByText('Save Results')).toBeInTheDocument();
  });

  it('loads analytes and displays them in the table', async () => {
    render(<ResultsEntryTable {...defaultProps} />);

    await waitFor(() => {
      // Without a test object the testId is used (legacy callers).
      expect(mockApiService.getAnalysisAnalytes).toHaveBeenCalledWith('test123');
    });

    expect(await screen.findByText('pH')).toBeInTheDocument();
    expect(screen.getByText('Temperature (°C)')).toBeInTheDocument();
  });

  it("loads analytes by the test's analysis id when the test is given", async () => {
    render(<ResultsEntryTable {...defaultProps} test={{ id: 'test123', sample_id: 'sample1', analysis_id: 'analysis9' }} />);

    await waitFor(() => {
      expect(mockApiService.getAnalysisAnalytes).toHaveBeenCalledWith('analysis9');
    });
  });

  it('displays samples and their positions', async () => {
    render(<ResultsEntryTable {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Sample 1')).toBeInTheDocument();
      expect(screen.getByText('Sample 2')).toBeInTheDocument();
    });

    expect(screen.getByText('1,1')).toBeInTheDocument();
    expect(screen.getByText('1,2')).toBeInTheDocument();
  });

  it('shows required field indicators', async () => {
    render(<ResultsEntryTable {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('pH')).toBeInTheDocument();
    });

    expect(screen.getByText('Required')).toBeInTheDocument();
  });

  it('handles result input changes', async () => {
    const user = userEvent.setup();
    render(<ResultsEntryTable {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('pH')).toBeInTheDocument();
    });

    const rawResultInputs = screen.getAllByLabelText('Raw Result');
    await user.clear(rawResultInputs[0]); // pH defaults to 7.0
    // jsdom drops a trailing "." mid-typing in number inputs, so set the value in one go.
    fireEvent.change(rawResultInputs[0], { target: { value: '7.5' } });

    await waitFor(() => expect(screen.getAllByLabelText('Raw Result')[0]).toHaveValue(7.5));
  });

  it('validates numeric results', async () => {
    const user = userEvent.setup();
    render(<ResultsEntryTable {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('pH')).toBeInTheDocument();
    });

    const rawResultInputs = screen.getAllByLabelText('Raw Result');
    fireEvent.change(rawResultInputs[0], { target: { value: '5.0' } }); // Below minimum

    await user.click(screen.getByText('Save Results'));
    expect(mockApiService.enterBatchResults).not.toHaveBeenCalled();

    await waitFor(() => {
      // Shown inline under the field and in the save error alert.
      expect(screen.getAllByText(/pH is below minimum value/).length).toBeGreaterThanOrEqual(2);
    });
  });

  it('saves results successfully', async () => {
    const user = userEvent.setup();
    mockApiService.enterBatchResults.mockResolvedValue([]);

    render(<ResultsEntryTable {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('pH')).toBeInTheDocument();
    });

    const rawResultInputs = screen.getAllByLabelText('Raw Result');
    fireEvent.change(rawResultInputs[0], { target: { value: '7.0' } });

    await user.click(screen.getByText('Save Results'));

    await waitFor(() => {
      expect(mockApiService.enterBatchResults).toHaveBeenCalledWith(
        'batch123',
        {
          batch_id: 'batch123',
          results: [
            {
              test_id: 'test123',
              entry_date: localDateString(),
              // pH entered; Temperature left blank (not sent)
              analyte_results: [
                { analyte_id: 'analyte1', raw_result: '7.0', reported_result: null, qualifiers: null },
              ],
            },
          ],
        }
      );
    });

    expect(defaultProps.onResultsSaved).toHaveBeenCalled();
  });

  it('caps entry date at the browser today and shows the API sentence', async () => {
    const user = userEvent.setup();
    mockApiService.enterBatchResults.mockRejectedValue({
      response: {
        data: {
          detail: [{ loc: ['body', 'results', 0, 'entry_date'], msg: 'Entry date cannot be in the future' }],
        },
      },
    });

    render(<ResultsEntryTable {...defaultProps} />);

    expect(await screen.findByLabelText('Entry date')).toHaveAttribute('max', localDateString());
    await user.click(screen.getByText('Save Results'));

    expect(await screen.findByText('results.0.entry_date: Entry date cannot be in the future')).toBeInTheDocument();
  });

  it('handles API errors gracefully', async () => {
    const user = userEvent.setup();
    mockApiService.enterBatchResults.mockRejectedValue({ response: { data: { detail: 'API Error' } } });

    render(<ResultsEntryTable {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('pH')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Save Results'));

    await waitFor(() => {
      expect(screen.getByText('API Error')).toBeInTheDocument();
    });
  });

  it('shows loading state during save', async () => {
    const user = userEvent.setup();
    mockApiService.enterBatchResults.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));

    render(<ResultsEntryTable {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Save Results')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Save Results'));

    expect(screen.getByText('Save Results')).toBeDisabled();
  });

  it('loads qualifiers and displays them in dropdown', async () => {
    render(<ResultsEntryTable {...defaultProps} />);

    await waitFor(() => {
      expect(mockApiService.getListEntries).toHaveBeenCalledWith('qualifiers');
    });

    // Check if qualifier dropdowns are present
    const qualifierSelects = await screen.findAllByRole('combobox', { name: 'Qualifiers' });
    expect(qualifierSelects.length).toBeGreaterThan(0);
  });
});
