import { render, screen, fireEvent } from '@testing-library/react';
import Summarize from '../components/Summarize';

describe('Recent summaries sidebar', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('deduplicates summaries from storage', () => {
    const dupes = [
      { id: '1', title: 'Title', content: 'A' },
      { id: '1', title: 'Title', content: 'A' },
    ];
    localStorage.setItem('summaries', JSON.stringify(dupes));
    render(<Summarize />);
    expect(screen.getAllByRole('button', { name: 'Title' })).toHaveLength(1);
  });

  it('allows deleting a summary', () => {
    const data = [{ id: '1', title: 'Title', content: 'A' }];
    localStorage.setItem('summaries', JSON.stringify(data));
    render(<Summarize />);
    fireEvent.click(screen.getByRole('button', { name: /delete summary/i }));
    expect(screen.queryByRole('button', { name: 'Title' })).not.toBeInTheDocument();
    expect(localStorage.getItem('summaries')).toBe('[]');
  });
});
