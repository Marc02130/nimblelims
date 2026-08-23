import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AliquotPlanEditor from '../components/experiments/AliquotPlanEditor';
import { apiService } from '../services/apiService';

jest.mock('../services/apiService', () => ({
  apiService: {
    getAliquotPlan: jest.fn(),
    getDestSampleTypes: jest.fn(),
    saveAliquotPlan: jest.fn(),
    executeAliquotPlan: jest.fn(),
  },
}));
const mockApiService = apiService as jest.Mocked<typeof apiService>;

const BLOOD_ID = '11111111-1111-4111-8111-111111111111';
const PLASMA_ID = '22222222-2222-4222-8222-222222222222';
const DNA_ID = '33333333-3333-4333-8333-333333333333';
const SAMPLE_ONE_ID = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const SAMPLE_TWO_ID = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';

describe('<AliquotPlanEditor />', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockApiService.saveAliquotPlan.mockResolvedValue({ line_count: 1 });
    mockApiService.executeAliquotPlan.mockResolvedValue({
      success_count: 1,
      error_count: 0,
    });
  });

  it('should load catalog options and send the selected destination type on save', async () => {
    const user = userEvent.setup();
    mockApiService.getAliquotPlan
      .mockResolvedValueOnce({
        lines: [
          {
            method: 'by_mass',
            source_sample_id: SAMPLE_ONE_ID,
            amount: 5,
          },
        ],
      })
      .mockResolvedValueOnce({ lines: [] });
    mockApiService.getDestSampleTypes.mockResolvedValue({
      source_sample_type: { id: BLOOD_ID, name: 'Blood' },
      operation: 'aliquot',
      options: [{ id: DNA_ID, name: 'DNA' }],
    });

    render(
      <AliquotPlanEditor
        entryId="entry-1"
        sampleIds={[SAMPLE_ONE_ID]}
      />,
    );

    const destSelect = await screen.findByRole('combobox', {
      name: 'Dest sample type, line 1',
    });
    await waitFor(() => expect(destSelect).not.toHaveAttribute('aria-disabled', 'true'));
    await user.click(destSelect);

    const listbox = await screen.findByRole('listbox');
    expect(within(listbox).getByText('Same as parent.')).toBeInTheDocument();
    await user.click(within(listbox).getByText('DNA'));
    await user.click(screen.getByRole('button', { name: 'Save plan' }));

    await waitFor(() => {
      expect(mockApiService.saveAliquotPlan).toHaveBeenCalledWith(
        'entry-1',
        expect.arrayContaining([
          expect.objectContaining({
            source_sample_id: SAMPLE_ONE_ID,
            dest_sample_type: DNA_ID,
          }),
        ]),
      );
    });
  });

  it('should refuse destination choices when a pool contains mixed source types', async () => {
    mockApiService.getAliquotPlan.mockResolvedValue({
      lines: [
        {
          method: 'by_mass',
          source_sample_id: SAMPLE_ONE_ID,
          amount: 5,
          pool_group: 'pool-a',
        },
        {
          method: 'by_mass',
          source_sample_id: SAMPLE_TWO_ID,
          amount: 5,
          pool_group: 'pool-a',
        },
      ],
    });
    mockApiService.getDestSampleTypes.mockImplementation(async (sampleId: string) => ({
      source_sample_type:
        sampleId === SAMPLE_ONE_ID
          ? { id: BLOOD_ID, name: 'Blood' }
          : { id: PLASMA_ID, name: 'Plasma' },
      operation: 'pool',
      options: [],
    }));

    render(
      <AliquotPlanEditor
        entryId="entry-1"
        sampleIds={[SAMPLE_ONE_ID, SAMPLE_TWO_ID]}
      />,
    );

    expect(
      await screen.findByText(
        'Pool “pool-a” has mixed source sample types (Blood and Plasma). Use one source sample type per pool.',
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('combobox', { name: 'Dest sample type, line 1' }),
    ).toHaveAttribute('aria-disabled', 'true');
    expect(
      screen.getByRole('combobox', { name: 'Dest sample type, line 2' }),
    ).toHaveAttribute('aria-disabled', 'true');
  });
});
