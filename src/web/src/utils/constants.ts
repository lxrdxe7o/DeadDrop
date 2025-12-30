/**
 * Application constants
 */

export const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB in bytes

export const TTL_OPTIONS = [
  { value: 3600, label: '1 hour' },
  { value: 86400, label: '1 day' },
  { value: 259200, label: '3 days' },
] as const;

export const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';
