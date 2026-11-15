import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { researchService } from '../services/researchService';
import {
  CreateSessionPayload,
  OwnershipScope,
  StressTestSubmissionPayload,
  ResearchJobStatus,
} from '../types/research';

const POLL_INTERVAL = Number(import.meta.env.VITE_POLL_INTERVAL_MS || 3000);

export const useSessions = (scope?: OwnershipScope) => {
  return useQuery({
    queryKey: ['sessions', scope],
    queryFn: () => researchService.getSessions(scope),
  });
};

export const useSession = (sessionId: string) => {
  return useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => researchService.getSession(sessionId),
    enabled: Boolean(sessionId),
  });
};

export const useJobStatus = (jobId?: string, isJobActive: boolean = true) => {
  return useQuery({
    queryKey: ['job', jobId],
    queryFn: () => researchService.getJobStatus(jobId!),
    enabled: Boolean(jobId) && isJobActive,
    refetchInterval: (query) => {
      const status: ResearchJobStatus | undefined = query.state.data?.status;
      const isTerminal =
        status === 'COMPLETED' ||
        status === 'PARTIAL' ||
        status === 'FAILED' ||
        status === 'CANCELLED';
      if (isTerminal) return false;
      return POLL_INTERVAL;
    },
  });
};

export const useBriefing = (sessionId: string, enabled: boolean = true) => {
  return useQuery({
    queryKey: ['briefing', sessionId],
    queryFn: () => researchService.getBriefing(sessionId),
    enabled: Boolean(sessionId) && enabled,
  });
};

export const useDashboardMetrics = () => {
  return useQuery({
    queryKey: ['dashboardMetrics'],
    queryFn: () => researchService.getDashboardMetrics(),
  });
};

export const useCreateSession = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateSessionPayload) => researchService.createSession(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboardMetrics'] });
    },
  });
};

export const useMarkReviewed = (sessionId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => researchService.markReviewed(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      queryClient.invalidateQueries({ queryKey: ['briefing', sessionId] });
    },
  });
};

export const useStressTest = (sessionId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: StressTestSubmissionPayload) =>
      researchService.submitStressTest(sessionId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['briefing', sessionId] });
    },
  });
};

