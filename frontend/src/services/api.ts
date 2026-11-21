import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

// Default mock mode setting from env, with runtime localStorage override capability
const getInitialMockMode = (): boolean => {
  const stored = localStorage.getItem('changeradar_use_mock');
  if (stored !== null) {
    return stored === 'true';
  }
  return import.meta.env.VITE_USE_MOCK_DATA === 'true';
};

let useMockDataState: boolean = getInitialMockMode();

export const isMockMode = (): boolean => useMockDataState;

export const setMockMode = (enabled: boolean): void => {
  useMockDataState = enabled;
  localStorage.setItem('changeradar_use_mock', String(enabled));
  window.dispatchEvent(new CustomEvent('changeradar:mockmode_changed', { detail: enabled }));
};

export const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 20000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

// Request interceptor: attach bearer token when auth is implemented with Krishank
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('changeradar_auth_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response interceptor: structured error reporting
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ message?: string; detail?: string }>) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      'An unexpected network error occurred.';
    return Promise.reject(new Error(message));
  }
);

