import { render, screen } from '@testing-library/react';
import Home from '../app/page';

describe('Home', () => {
  it('renders Summarize button', () => {
    render(<Home />);
    expect(screen.getByRole('button', { name: /summarize/i })).toBeInTheDocument();
  });
});
