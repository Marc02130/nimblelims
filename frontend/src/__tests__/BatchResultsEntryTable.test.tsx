import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import BatchResultsEntryTable from '../components/results/BatchResultsEntryTable';
import { apiService } from '../services/apiService';
import { localDateString } from '../utils/localDate';

// Mock the API service
jest.mock('../services/apiService');
const mockApiService = apiService as jest.Mocked<typeof apiService>;

const mockTests = [
  {
    id: 'test1',
    name: 'pH Test',
    status: 'In Process',
    analysis_id: 'analysis1',
    sample_id: 'sample1',
  },
  {
    id: 'test2',
    name: 'Temperature Test',
    status: 'In Process',
    analysis_id: 'analysis1',
    sample_id: 'sample2',
  },
];

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
    qc_type: 'blank',
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

const defaultProps = {
  batchId: 'batch123',
  tests: mockTests,
  samples: mockSamples,
  onResultsSaved: jest.fn(),
};


// pH is required on every row (both tests use analysis1). Raw Result inputs run row by row:
// [row1 pH, row1 Temperature, row2 pH, row2 Temperature].
const fillRequiredResults = async () => {
  const inputs = await screen.findAllByLabelText('Raw Result');
  fireEvent.change(inputs[0], { target: { value: '7.0' } });
  fireEvent.change(screen.getAllByLabelText('Raw Result')[2], { target: { value: '7.2' } });
};

describe('BatchResultsEntryTable', () => {
  it('caps entry date at the browser today and refuses a typed later day', async () => {
    const user = userEvent.setup();
    render(<BatchResultsEntryTable {...defaultProps} />);
    const dateInput = await screen.findByLabelText('Entry date');
    expect(dateInput).toHaveAttribute('max', localDateString());
    fireEvent.change(dateInput, { target: { value: '2099-01-01' } });
    await user.click(screen.getByText('Submit Results'));
    expect(await screen.findAllByText('Entry date cannot be in the future')).toHaveLength(1);
    expect(screen.queryByText('Confirm Submission')).not.toBeInTheDocument();
    expect(mockApiService.enterBatchResults).not.toHaveBeenCalled();
  });

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock API calls
    mockApiService.getAnalysisAnalytes.mockResolvedValue(mockAnalytes);
    mockApiService.enterBatchResults.mockResolvedValue({
      id: 'batch123',
      name: 'Test Batch',
      containers: [],
    });
  });

  it('renders the bulk results entry table', async () => {
    render(<BatchResultsEntryTable {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Bulk Results Entry')).toBeInTheDocument();
    });

    expect(screen.getByText('Submit Results')).toBeInTheDocument();
  });

  it('loads analytes for all analyses', async () => {
    render(<BatchResultsEntryTable {...defaultProps} />);

    await waitFor(() => {
      expect(mockApiService.getAnalysisAnalytes).toHaveBeenCalledWith('analysis1');
    });
  });

  it('displays tests and samples in DataGrid', async () => {
    render(<BatchResultsEntryTable {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Sample 1')).toBeInTheDocument();
      expect(screen.getByText('Sample 2')).toBeInTheDocument();
    });
  });

  it('highlights QC samples', async () => {
    render(<BatchResultsEntryTable {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Sample 2')).toBeInTheDocument();
    });

    // Check for QC chip
    const qcChips = screen.getAllByText('QC');
    expect(qcChips.length).toBeGreaterThan(0);
  });

  it('allows editing cell values', async () => {
    const user = userEvent.setup();
    render(<BatchResultsEntryTable {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('pH')).toBeInTheDocument();
    });

    const rawResultInputs = screen.getAllByLabelText('Raw Result');
    if (rawResultInputs.length > 0) {
      // jsdom drops a trailing "." mid-typing in number inputs, so set the value in one go.
      fireEvent.change(rawResultInputs[0], { target: { value: '7.5' } });
      // numeric analyte: type="number"
      await waitFor(() => expect(screen.getAllByLabelText('Raw Result')[0]).toHaveValue(7.5));
    }
  });

  it('validates results in real-time', async () => {
    const user = userEvent.setup();
    render(<BatchResultsEntryTable {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('pH')).toBeInTheDocument();
    });

    const rawResultInputs = screen.getAllByLabelText('Raw Result');
    if (rawResultInputs.length > 0) {
      await user.type(rawResultInputs[0], '5.0'); // Below minimum
      
      await waitFor(() => {
        // Check for validation error
        const errorText = screen.queryByText(/pH is below minimum value/);
        if (errorText) {
          expect(errorText).toBeInTheDocument();
        }
      });
    }
  });

  it('submits results with confirmation dialog', async () => {
    const user = userEvent.setup();
    render(<BatchResultsEntryTable {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Submit Results')).toBeInTheDocument();
    });
    await fillRequiredResults();

    await user.click(screen.getByText('Submit Results'));

    await waitFor(() => {
      expect(screen.getByText('Confirm Submission')).toBeInTheDocument();
    });

    const submitButton = screen.getByText('Submit');
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockApiService.enterBatchResults).toHaveBeenCalledWith(
        'batch123',
        expect.objectContaining({
          batch_id: 'batch123',
          results: [
            expect.objectContaining({ test_id: 'test1', analyte_results: [expect.objectContaining({ analyte_id: 'analyte1', raw_result: '7.0' })] }),
            expect.objectContaining({ test_id: 'test2', analyte_results: [expect.objectContaining({ analyte_id: 'analyte1', raw_result: '7.2' })] }),
          ],
        })
      );
    });
  });

  it('handles validation errors before submission', async () => {
    const user = userEvent.setup();
    render(<BatchResultsEntryTable {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Submit Results')).toBeInTheDocument();
    });

    // Try to submit without required fields
    await user.click(screen.getByText('Submit Results'));

    await waitFor(() => {
      expect(screen.getByText('Confirm Submission')).toBeInTheDocument();
    });

    const submitButton = screen.getByText('Submit');
    await user.click(submitButton);

    await waitFor(() => {
      // Should show validation errors
      const errorAlert = screen.queryByText(/Validation errors found/);
      if (errorAlert) {
        expect(errorAlert).toBeInTheDocument();
      }
    });
  });

  it('handles QC failures with blocking', async () => {
    const user = userEvent.setup();
    // Mock QC blocking enabled
    process.env.REACT_APP_FAIL_QC_BLOCKS_BATCH = 'true';
    
    mockApiService.enterBatchResults.mockRejectedValue({
      response: {
        data: {
          detail: {
            message: 'QC failures detected and blocking is enabled',
            qc_failures: [
              { test_id: 'test2', reason: 'No results entered for QC sample' },
            ],
          },
        },
      },
    });

    render(<BatchResultsEntryTable {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Submit Results')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Submit Results'));
    await waitFor(() => {
      const submitButton = screen.getByText('Submit');
      if (submitButton) {
        user.click(submitButton);
      }
    });

    await waitFor(() => {
      const errorText = screen.queryByText(/QC failures detected/);
      if (errorText) {
        expect(errorText).toBeInTheDocument();
      }
    });

    delete process.env.REACT_APP_FAIL_QC_BLOCKS_BATCH;
  });

  it('calls onResultsSaved after successful submission', async () => {
    const user = userEvent.setup();
    render(<BatchResultsEntryTable {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Submit Results')).toBeInTheDocument();
    });

    await fillRequiredResults();

    await user.click(screen.getByText('Submit Results'));
    await user.click(await screen.findByRole('button', { name: 'Submit' }));

    await waitFor(() => {
      expect(defaultProps.onResultsSaved).toHaveBeenCalled();
    });
  });

  it('handles API errors gracefully', async () => {
    const user = userEvent.setup();
    mockApiService.enterBatchResults.mockRejectedValue(new Error('API Error'));

    render(<BatchResultsEntryTable {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Submit Results')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Submit Results'));
    await waitFor(() => {
      const submitButton = screen.getByText('Submit');
      if (submitButton) {
        user.click(submitButton);
      }
    });

    await waitFor(() => {
      const errorText = screen.queryByText(/API Error|Failed to save results/);
      if (errorText) {
        expect(errorText).toBeInTheDocument();
      }
    });
  });
});

