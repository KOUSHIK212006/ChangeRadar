import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Badge } from '../components/common/Badge';

describe('Badge Component', () => {
  it('renders SUPPORTED evidence badge with readable label', () => {
    render(<Badge type="evidence" value="SUPPORTED" />);
    expect(screen.getByText('Supported')).toBeInTheDocument();
  });

  it('renders CONTRADICTED evidence badge with readable label and title', () => {
    render(<Badge type="evidence" value="CONTRADICTED" />);
    expect(screen.getByText('Contradicted')).toBeInTheDocument();
    expect(
      screen.getByTitle('Direct evidence refutes or contradicts this claim')
    ).toBeInTheDocument();
  });

  it('renders INSUFFICIENT evidence badge with non-color label', () => {
    render(<Badge type="evidence" value="INSUFFICIENT" />);
    expect(screen.getByText('Insufficient Evidence')).toBeInTheDocument();
  });

  it('renders job status badges', () => {
    render(<Badge type="job" value="RUNNING" />);
    expect(screen.getByText('Running')).toBeInTheDocument();

    render(<Badge type="job" value="COMPLETED" />);
    expect(screen.getByText('Completed')).toBeInTheDocument();
  });

  it('renders scope badges correctly', () => {
    render(<Badge type="scope" value="PERSONAL" />);
    expect(screen.getByText('Personal Scope')).toBeInTheDocument();

    render(<Badge type="scope" value="WORKSPACE" />);
    expect(screen.getByText('Workspace Scope')).toBeInTheDocument();
  });
});

