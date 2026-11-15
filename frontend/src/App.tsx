import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppLayout } from './components/layout/AppLayout';
import { Dashboard } from './pages/Dashboard';
import { NewResearch } from './pages/NewResearch';
import { ResearchDetails } from './pages/ResearchDetails';
import { EvidenceLedger } from './pages/EvidenceLedger';
import { StressTestPage } from './pages/StressTestPage';
import { ResearchHistory } from './pages/ResearchHistory';
import { NotFound } from './pages/NotFound';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 1000 * 30, // 30 seconds
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="new" element={<NewResearch />} />
            <Route path="research/:id" element={<ResearchDetails />} />
            <Route path="evidence" element={<EvidenceLedger />} />
            <Route path="stress-test" element={<StressTestPage />} />
            <Route path="history" element={<ResearchHistory />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;

