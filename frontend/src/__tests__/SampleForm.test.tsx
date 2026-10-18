import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SampleForm from '../components/samples/SampleForm';
import { apiService } from '../services/apiService';
import { localDateString } from '../utils/localDate';

jest.mock('../services/apiService', () => ({
  apiService: {
    getCustomAttributeConfigs: jest.fn().mockResolvedValue({ configs: [] }),
  },
}));
jest.mock('../contexts/UserContext', () => ({
  useUser: () => ({ hasPermission: () => true }),
}));

beforeEach(() => {
  (apiService.getCustomAttributeConfigs as jest.Mock).mockResolvedValue({ configs: [] });
});

describe('SampleForm temperature zero', () => {
  it('keeps a temperature of 0 and submits it', async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn().mockResolvedValue(undefined);
    render(
      <SampleForm
        sample={{ id: 'sample-1', name: 'Ice', temperature: 0 }}
        lookupData={{ sampleTypes: [], statuses: [], matrices: [], qcTypes: [], projects: [] }}
        onSubmit={onSubmit}
        onCancel={jest.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('spinbutton', { name: /Temperature/ })).toHaveValue(0);
    });

    await user.click(screen.getByRole('button', { name: 'Update sample' }));
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ temperature: 0 }));
    });
  });
});

describe('SampleForm dates', () => {
  const lookupData = { sampleTypes: [], statuses: [], matrices: [], qcTypes: [], projects: [] };

  it('caps received and report dates at the browser today and leaves due date open', async () => {
    render(
      <SampleForm
        sample={{ id: 'sample-1', name: 'Ice' }}
        lookupData={lookupData}
        onSubmit={jest.fn()}
        onCancel={jest.fn()}
      />
    );

    expect(await screen.findByLabelText('Received Date')).toHaveAttribute('max', localDateString());
    expect(screen.getByLabelText('Report Date')).toHaveAttribute('max', localDateString());
    const due = screen.getByRole('group', { name: 'Due Date' });
    expect(due.querySelector('input')).not.toHaveAttribute('max');
  });

  it('shows the API sentence when a date is refused', async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn().mockRejectedValue({
      response: {
        data: {
          detail: [{ loc: ['body', 'received_date'], msg: 'Date cannot be in the future' }],
        },
      },
    });
    render(
      <SampleForm
        sample={{ id: 'sample-1', name: 'Ice' }}
        lookupData={lookupData}
        onSubmit={onSubmit}
        onCancel={jest.fn()}
      />
    );

    await user.click(await screen.findByRole('button', { name: 'Update sample' }));
    expect(await screen.findByText('received_date: Date cannot be in the future')).toBeInTheDocument();
  });
});
