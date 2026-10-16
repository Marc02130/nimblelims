import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SampleForm from '../components/samples/SampleForm';

jest.mock('../services/apiService', () => ({
  apiService: {
    getCustomAttributeConfigs: jest.fn().mockResolvedValue({ configs: [] }),
  },
}));
jest.mock('../contexts/UserContext', () => ({
  useUser: () => ({ hasPermission: () => true }),
}));

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
