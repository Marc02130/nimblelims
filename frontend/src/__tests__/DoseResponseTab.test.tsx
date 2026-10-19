import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import DoseResponseTab from '../pages/DoseResponse/DoseResponseTab';
import { apiService } from '../services/apiService';
import { formatInstant } from '../utils/localDate';

jest.mock('../services/apiService');
const mockApiService = apiService as jest.Mocked<typeof apiService>;

const summaryBase = {
  run_id: 'run-1',
  fit_in_progress: false,
  total: 1,
  by_category: { SIGMOID: 1 },
  by_review_status: { pending: 1 },
};

describe('DoseResponseTab last fit', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the last fit in local time', async () => {
    mockApiService.getDoseResponseSummary.mockResolvedValue({
      ...summaryBase,
      last_fit_at: '2026-10-18T23:23:00Z',
    });

    render(
      <BrowserRouter>
        <DoseResponseTab runId="run-1" runStatus="complete" />
      </BrowserRouter>,
    );

    expect(
      await screen.findByText(`Last fit: ${formatInstant('2026-10-18T23:23:00Z')}`),
    ).toBeInTheDocument();
    expect(screen.queryByText('Last fit: —')).not.toBeInTheDocument();
  });

  it('renders an em dash when the run has no fit', async () => {
    mockApiService.getDoseResponseSummary.mockResolvedValue({
      ...summaryBase,
      total: 0,
      by_category: {},
      by_review_status: {},
      last_fit_at: null,
    });

    render(
      <BrowserRouter>
        <DoseResponseTab runId="run-1" runStatus="complete" />
      </BrowserRouter>,
    );

    expect(await screen.findByText('Last fit: —')).toBeInTheDocument();
  });
});
