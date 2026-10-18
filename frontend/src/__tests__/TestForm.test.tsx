import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TestForm from '../components/tests/TestForm';
import { localDateString } from '../utils/localDate';

jest.mock('../services/apiService', () => ({
  apiService: {
    getCustomAttributeConfigs: jest.fn().mockResolvedValue({ configs: [] }),
  },
}));
jest.mock('../contexts/UserContext', () => ({
  useUser: () => ({ hasPermission: () => true }),
}));

const lookupData = {
  statuses: [{ id: 'status-1', name: 'In Process' }],
  users: [],
  analyses: [],
};

describe('TestForm dates', () => {
  it('caps test and review dates at the browser today', async () => {
    render(
      <TestForm
        test={{ id: 'test-1', name: 'Assay', status: 'status-1' }}
        lookupData={lookupData}
        onSubmit={jest.fn()}
        onCancel={jest.fn()}
      />
    );

    expect(await screen.findByLabelText('Test Date')).toHaveAttribute('max', localDateString());
    expect(screen.getByLabelText('Review Date')).toHaveAttribute('max', localDateString());
  });

  it('shows the API sentence when a date is refused', async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn().mockRejectedValue({
      response: {
        data: {
          detail: { message: 'Date cannot be in the future' },
        },
      },
    });
    render(
      <TestForm
        test={{ id: 'test-1', name: 'Assay', status: 'status-1' }}
        lookupData={lookupData}
        onSubmit={onSubmit}
        onCancel={jest.fn()}
      />
    );

    await user.click(await screen.findByRole('button', { name: 'Update test' }));
    expect(await screen.findByText('Date cannot be in the future')).toBeInTheDocument();
  });
});
