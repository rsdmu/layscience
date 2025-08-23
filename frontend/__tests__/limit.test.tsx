import { render, screen } from '@testing-library/react';
import Summarize from '../components/Summarize';

describe('Summarize limit', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('shows create account button when limit reached', () => {
    localStorage.setItem('testCount', '5');
    render(<Summarize />);
    expect(screen.getByText(/test limit reached/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /create account/i })).toBeInTheDocument();
  });
});
