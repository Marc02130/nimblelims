import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import BatchResultsView from '../components/results/BatchResultsView';
import { apiService } from '../services/apiService';
import { localDateString } from '../utils/localDate';

jest.mock('../services/apiService');
const mockApiService = apiService as jest.Mocked<typeof apiService>;

jest.mock('../contexts/UserContext', () => ({
  useUser: () => ({
    user: { id: 'u1', username: 'tech', role: 'Lab Technician', permissions: ['result:enter'] },
    hasPermission: (perm: string) => perm === 'result:enter',
  }),
}));

const batchId = 'batch-1';

describe('BatchResultsView', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockApiService.getBatch.mockResolvedValue({
      id: batchId,
      name: 'BATCH-RESULTS-001',
      description: 'Evening run',
      status: 'In Process',
    });
    mockApiService.getBatchContainers.mockResolvedValue([
      {
        id: 'container-1',
        row: 1,
        column: 2,
        contents: [
          {
            sample_id: 'sample-1',
            sample_name: 'Sample A',
            qc_type: null,
            sample: { qc_type: null },
          },
        ],
      },
    ]);
    mockApiService.getTestsByBatch.mockResolvedValue([
      {
        id: 'test-1',
        name: 'Potency',
        status: 'In Analysis',
        analysis_id: 'analysis-1',
        sample_id: 'sample-1',
      },
    ]);
    mockApiService.getAnalysisAnalytes.mockResolvedValue([
      {
        id: 'analyte-1',
        name: 'pH',
        data_type: 'numeric',
        is_required: true,
        default_value: '7.0',
        reported_name: 'pH',
        display_order: 1,
      },
    ]);
    mockApiService.getListEntries.mockResolvedValue([]);
    mockApiService.getCustomAttributeConfigs.mockResolvedValue({ configs: [] });
    mockApiService.enterBatchResults.mockResolvedValue({});
  });

  it('loads the batch and submits results through POST /results/batch', async () => {
    const user = userEvent.setup();
    render(<BatchResultsView batchId={batchId} />);

    expect(await screen.findByText('BATCH-RESULTS-001')).toBeInTheDocument();
    expect(screen.getByText('Sample A')).toBeInTheDocument();
    expect(mockApiService.getBatchContainers).toHaveBeenCalledWith(batchId);
    expect(mockApiService.getTestsByBatch).toHaveBeenCalledWith(batchId);
    expect(await screen.findByText('pH')).toBeInTheDocument();
    expect(mockApiService.getAnalysisAnalytes).toHaveBeenCalledWith('analysis-1');

    fireEvent.change(screen.getByLabelText('Raw Result'), { target: { value: '7.2' } });
    await user.click(screen.getByText('Save Results'));

    await waitFor(() => {
      expect(mockApiService.enterBatchResults).toHaveBeenCalledWith(batchId, {
        batch_id: batchId,
        results: [
          {
            test_id: 'test-1',
            entry_date: localDateString(),
            analyte_results: [
              {
                analyte_id: 'analyte-1',
                raw_result: '7.2',
                reported_result: null,
                qualifiers: null,
              },
            ],
          },
        ],
      });
    });
  });
});
