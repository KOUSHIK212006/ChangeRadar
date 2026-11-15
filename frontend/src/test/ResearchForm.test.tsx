import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { ResearchForm } from '../components/research/ResearchForm';

const queryClient = new QueryClient();

describe('ResearchForm Component', () => {
  it('renders target name input and submit button', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ResearchForm />
        </BrowserRouter>
      </QueryClientProvider>
    );

    expect(screen.getByLabelText(/Target Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Entity Classification/i)).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Launch Research Run/i })
    ).toBeInTheDocument();
  });

  it('allows switching ownership boundary between Personal and Workspace', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ResearchForm />
        </BrowserRouter>
      </QueryClientProvider>
    );

    const personalBtn = screen.getByRole('button', { name: /Personal/i });
    const workspaceBtn = screen.getByRole('button', { name: /Workspace/i });

    expect(personalBtn).toBeInTheDocument();
    expect(workspaceBtn).toBeInTheDocument();

    fireEvent.click(workspaceBtn);
    expect(workspaceBtn).toHaveClass('text-status-info');
  });

  it('supports adding and typing dynamic questions', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ResearchForm />
        </BrowserRouter>
      </QueryClientProvider>
    );

    const addQuestionBtn = screen.getByRole('button', { name: /Add Question/i });
    fireEvent.click(addQuestionBtn);

    const inputs = screen.getAllByPlaceholderText(/Any updates on executive departures/i);
    expect(inputs.length).toBe(2);

    fireEvent.change(inputs[0], { target: { value: 'What about APAC sales?' } });
    expect(inputs[0]).toHaveValue('What about APAC sales?');
  });
});

