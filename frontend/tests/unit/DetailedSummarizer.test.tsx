import { act, fireEvent, render, screen } from '@testing-library/react';
import React from 'react';
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import DetailedSummarizer from '../../src/components/DetailedSummarizer';
import { apiClient } from '../../src/utils/api';

vi.mock('../../src/utils/api', () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

describe('DetailedSummarizer', () => {
  beforeEach(() => {
    vi.useFakeTimers();

    if (!HTMLElement.prototype.scrollIntoView) {
      HTMLElement.prototype.scrollIntoView = vi.fn();
    }
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('keeps previous summaries visible after generating a new one', async () => {
    vi.mocked(apiClient.post)
      .mockResolvedValueOnce({ data: { task_id: 'task-1' }, status: 200 })
      .mockResolvedValueOnce({ data: { task_id: 'task-2' }, status: 200 });
    vi.mocked(apiClient.get)
      .mockResolvedValueOnce({
        data: {
          status: 'done',
          result: {
            topic: 'biology',
            title: 'First Summary',
            summary: 'First summary body',
            chunks_used: 5,
            sections: [],
            references: [],
          },
        },
        status: 200,
      })
      .mockResolvedValueOnce({
        data: {
          status: 'done',
          result: {
            topic: 'chemistry',
            title: 'Second Summary',
            summary: 'Second summary body',
            chunks_used: 5,
            sections: [],
            references: [],
          },
        },
        status: 200,
      });

    render(<DetailedSummarizer />);

    fireEvent.change(screen.getByLabelText('Chat ID (Optional)'), { target: { value: '7' } });

    fireEvent.click(screen.getByRole('button', { name: 'Generate Summary' }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });

    expect(screen.getByText('First Summary')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Generate Summary' }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });

    expect(screen.getByText('First Summary')).toBeInTheDocument();
    expect(screen.getByText('Second Summary')).toBeInTheDocument();
  });
});