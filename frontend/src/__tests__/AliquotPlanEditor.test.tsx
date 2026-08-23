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

  it('saves a separate entry method, default type, and line override', async () => {
    const user = userEvent.setup();
    mockApiService.getAliquotPlan
      .mockResolvedValueOnce({
        method: 'aliquot_by_target_amount',
        default_dest_sample_type: null,
        line_count: 0,
        lines: [
          {
            source_sample_id: SAMPLE_ONE_ID,
            target_amount: 5,
            inherit_entry_dest_sample_type: true,
          },
        ],
      })
      .mockResolvedValueOnce({
        method: 'aliquot_by_target_amount',
        default_dest_sample_type: DNA_ID,
        line_count: 1,
        lines: [],
      });
    mockApiService.getDestSampleTypes.mockResolvedValue({
      source_sample_type: { id: BLOOD_ID, name: 'Blood' },
      operation: 'aliquot',
      options: [{ id: DNA_ID, name: 'DNA' }],
    });

    render(<AliquotPlanEditor entryId="entry-1" sampleIds={[SAMPLE_ONE_ID]} />);

    const methodSelect = await screen.findByRole('combobox', {
      name: 'Aliquot or pool method',
    });
    expect(methodSelect).toHaveTextContent('Aliquot — by target amount');

    const defaultSelect = screen.getByRole('combobox', {
      name: 'Default dest sample type',
    });
    await waitFor(() => expect(defaultSelect).not.toHaveAttribute('aria-disabled', 'true'));
    await user.click(defaultSelect);
    await user.click(within(await screen.findByRole('listbox')).getByText('DNA'));

    const lineSelect = screen.getByRole('combobox', {
      name: 'Dest sample type, line 1',
    });
    await user.click(lineSelect);
    const lineOptions = await screen.findByRole('listbox');
    expect(within(lineOptions).getByText('Same as parent.')).toBeInTheDocument();
    await user.click(within(lineOptions).getByText('DNA'));
    await user.click(screen.getByRole('button', { name: 'Save plan' }));

    await waitFor(() => {
      expect(mockApiService.saveAliquotPlan).toHaveBeenCalledWith('entry-1', {
        method: 'aliquot_by_target_amount',
        default_dest_sample_type: DNA_ID,
        lines: [
          expect.objectContaining({
            source_sample_id: SAMPLE_ONE_ID,
            dest_sample_type: DNA_ID,
            inherit_entry_dest_sample_type: false,
          }),
        ],
      });
    });
  });

  it('locks the concrete method after persisted lines exist', async () => {
    mockApiService.getAliquotPlan.mockResolvedValue({
      method: 'aliquot_by_volume',
      default_dest_sample_type: null,
      line_count: 1,
      lines: [
        {
          source_sample_id: SAMPLE_ONE_ID,
          volume: 1,
          inherit_entry_dest_sample_type: true,
        },
      ],
    });
    mockApiService.getDestSampleTypes.mockResolvedValue({
      source_sample_type: { id: BLOOD_ID, name: 'Blood' },
      operation: 'aliquot',
      options: [],
    });

    render(<AliquotPlanEditor entryId="entry-1" sampleIds={[SAMPLE_ONE_ID]} />);

    expect(
      await screen.findByText(
        'Method is locked after lines exist. Cancel the experiment to change it.',
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('combobox', { name: 'Aliquot or pool method' }),
    ).toHaveAttribute('aria-disabled', 'true');
  });

  it('refuses destination choices when a pool contains mixed source types', async () => {
    mockApiService.getAliquotPlan.mockResolvedValue({
      method: 'pool_by_target_amount_per_source',
      default_dest_sample_type: null,
      line_count: 2,
      lines: [
        {
          source_sample_id: SAMPLE_ONE_ID,
          target_amount: 5,
          pool_group: 'pool-a',
          inherit_entry_dest_sample_type: true,
        },
        {
          source_sample_id: SAMPLE_TWO_ID,
          target_amount: 5,
          pool_group: 'pool-a',
          inherit_entry_dest_sample_type: true,
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
