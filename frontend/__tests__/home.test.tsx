import { render, screen } from '@testing-library/react';
import Home from '../app/page';

describe('Home', () => {
  it('renders Summrise button', () => {
    render(<Home />);
    expect(screen.getByRole('button', { name: /summrise/i })).toBeInTheDocument();
  });
});
