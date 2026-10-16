import React from 'react';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import SchemaLayouts from '../pages/admin/schema/SchemaLayouts';
import { apiService } from '../services/apiService';
import * as UserContext from '../contexts/UserContext';

jest.mock('../services/apiService', () => ({
  ...jest.requireActual('../services/apiService'),
  apiService: {
    getCurrentUser: () => Promise.reject(new Error('no session')),
    getRoles: jest.fn(),
    getSchemaTables: jest.fn(),
    getSchemaColumns: jest.fn(),
    getSchemaLayout: jest.fn(),
    putSchemaLayout: jest.fn(),
  },
}));

const api = apiService as jest.Mocked<typeof apiService>;

const columns = Array.from({ length: 40 }, (_, i) => ({
  id: `col-${i}`,
  display_name: `Field ${i}`,
  status: 'active',
}));

beforeEach(() => {
  jest.spyOn(UserContext, 'useUser').mockReturnValue({
    hasPermission: () => true,
  } as unknown as ReturnType<typeof UserContext.useUser>);
  api.getRoles.mockResolvedValue([{ id: 'role-1', name: 'Lab Technician' }]);
  api.getSchemaTables.mockResolvedValue([
    { id: 'table-samples', physical_name: 'samples', display_name: 'Samples' },
  ]);
  api.getSchemaColumns.mockResolvedValue(columns);
  api.getSchemaLayout.mockResolvedValue({
    fields: [
      { column_id: 'col-0', display_name: 'Field 0', sort_order: 0 },
      { column_id: 'col-1', display_name: 'Field 1', sort_order: 1 },
    ],
  });
});

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={['/admin/schema/layouts']}>
      <SchemaLayouts />
    </MemoryRouter>,
  );

const scrollStyle = (element: HTMLElement) => window.getComputedStyle(element);

describe('SchemaLayouts', () => {
  it('should scroll the available list and the layout editor', async () => {
    renderPage();

    expect(await screen.findByRole('button', { name: 'Field 39' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Field 0' })).toBeInTheDocument();

    const available = screen.getByTestId('schema-layout-available');
    const editor = screen.getByTestId('schema-layout-editor');

    expect(within(available).getByRole('button', { name: 'Field 39' })).toBeInTheDocument();
    expect(within(available).queryByRole('button', { name: 'Field 0' })).toBeNull();
    expect(within(editor).getByRole('button', { name: 'Field 0' })).toBeInTheDocument();
    expect(within(editor).queryByRole('button', { name: 'Field 39' })).toBeNull();

    for (const region of [available, editor]) {
      const regionStyle = scrollStyle(region);
      const columnStyle = scrollStyle(region.parentElement as HTMLElement);
      expect(regionStyle.overflowY).toBe('auto');
      expect(regionStyle.minHeight).toBe('0px');
      expect(columnStyle.minHeight).toBe('0px');
      expect(columnStyle.overflowY).toBe('hidden');
    }

    const rowStyle = scrollStyle(available.parentElement?.parentElement as HTMLElement);
    expect(rowStyle.minHeight).toBe('0px');
    expect(rowStyle.overflowY).toBe('hidden');
  });

  it('should move a field between the list and the editor', async () => {
    renderPage();
    const available = await screen.findByTestId('schema-layout-available');
    fireEvent.click(within(available).getByRole('button', { name: 'Field 2' }));

    const editor = screen.getByTestId('schema-layout-editor');
    expect(within(editor).getByRole('button', { name: 'Field 2' })).toBeInTheDocument();
    expect(within(available).queryByRole('button', { name: 'Field 2' })).toBeNull();
  });
});
