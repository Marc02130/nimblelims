import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ContainerForm from '../components/containers/ContainerForm';

describe('ContainerForm zero values', () => {
  it('keeps an amount and concentration of 0', async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn();
    render(
      <ContainerForm
        container={{
          name: 'Tube',
          type_id: 'type-1',
          amount: 0,
          concentration: 0,
        }}
        lookupData={{
          containerTypes: [{ id: 'type-1', name: 'Tube', material: 'Plastic', dimensions: '1x1' }],
          units: [],
        }}
        onSubmit={onSubmit}
        onCancel={jest.fn()}
      />
    );

    expect(screen.getByRole('spinbutton', { name: /^Amount/ })).toHaveValue(0);
    expect(screen.getByRole('spinbutton', { name: /^Concentration/ })).toHaveValue(0);

    await user.click(screen.getByRole('button', { name: 'Update' }));
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ amount: 0, concentration: 0 })
    );
  });
});
