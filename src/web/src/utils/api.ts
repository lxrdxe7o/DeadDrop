/**
 * API client for backend communication
 *
 * Features:
 * - Automatic retry with exponential backoff
 * - Timeout handling
 * - Request ID tracking
 * - Comprehensive error handling
 * - Type-safe error responses
 */

import { API_BASE_URL } from './constants';

export interface UploadResponse {
  id: string;
  expires_at: string;
}

export interface ErrorResponse {
  error: string;
  details?: unknown;
}

export class APIError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public requestId?: string,
    public details?: unknown
  ) {
    super(message);
    this.name = 'APIError';
  }
}

export class NetworkError extends Error {
  constructor(message: string, public cause?: Error) {
    super(message);
    this.name = 'NetworkError';
  }
}

export class TimeoutError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'TimeoutError';
  }
}

/**
 * Configuration for API requests
 */
interface RequestConfig {
  timeout?: number;
  maxRetries?: number;
  retryDelay?: number;
}

const DEFAULT_CONFIG: RequestConfig = {
  timeout: 30000, // 30 seconds
  maxRetries: 3,
  retryDelay: 1000, // 1 second base delay
};

/**
 * Sleep utility for retry delays
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Fetch with timeout support
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeout: number
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new TimeoutError(`Request timed out after ${timeout}ms`);
    }
    throw error;
  }
}

/**
 * Retry wrapper with exponential backoff
 */
async function withRetry<T>(
  fn: () => Promise<T>,
  config: RequestConfig = {}
): Promise<T> {
  const { maxRetries = DEFAULT_CONFIG.maxRetries!, retryDelay = DEFAULT_CONFIG.retryDelay! } = config;

  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;

      // Don't retry on client errors (4xx) or successful responses
      if (error instanceof APIError && error.statusCode && error.statusCode < 500) {
        throw error;
      }

      // Don't retry on last attempt
      if (attempt === maxRetries) {
        break;
      }

      // Exponential backoff: delay * (2 ** attempt)
      const delay = retryDelay * Math.pow(2, attempt);
      console.warn(`Request failed (attempt ${attempt + 1}/${maxRetries + 1}), retrying in ${delay}ms...`, error);
      await sleep(delay);
    }
  }

  throw lastError || new Error('Request failed after retries');
}

/**
 * Upload encrypted file to backend.
 *
 * Features:
 * - Automatic retry on network errors
 * - Timeout handling
 * - Request ID tracking
 * - Detailed error messages
 *
 * @param encryptedData - Encrypted file blob
 * @param filename - Original filename
 * @param ttl - Time to live in seconds
 * @param maxDownloads - Maximum download count (1-5)
 * @param config - Optional request configuration
 * @returns Upload response with file ID and expiration
 * @throws APIError, NetworkError, or TimeoutError
 */
export async function uploadFile(
  encryptedData: Uint8Array,
  filename: string,
  ttl: number,
  maxDownloads: number,
  config: RequestConfig = {}
): Promise<UploadResponse> {
  const { timeout = DEFAULT_CONFIG.timeout! } = config;

  return withRetry(async () => {
    const formData = new FormData();
    formData.append('file', new Blob([new Uint8Array(encryptedData)]), `${filename}.enc`);
    formData.append('filename', filename);
    formData.append('ttl', ttl.toString());
    formData.append('max_downloads', maxDownloads.toString());

    let response: Response;
    try {
      response = await fetchWithTimeout(
        `${API_BASE_URL}/upload`,
        {
          method: 'POST',
          body: formData,
        },
        timeout
      );
    } catch (error) {
      if (error instanceof TimeoutError) {
        throw error;
      }
      throw new NetworkError(
        'Network error during upload',
        error as Error
      );
    }

    // Extract request ID from response headers
    const requestId = response.headers.get('X-Request-ID');

    if (!response.ok) {
      let errorMessage = 'Upload failed';
      let errorDetails: unknown = undefined;

      try {
        const errorData: ErrorResponse = await response.json();
        errorMessage = errorData.error || errorMessage;
        errorDetails = errorData.details;
      } catch {
        // Failed to parse error response, use status text
        errorMessage = response.statusText || errorMessage;
      }

      throw new APIError(
        errorMessage,
        response.status,
        requestId || undefined,
        errorDetails
      );
    }

    return response.json();
  }, config);
}

/**
 * Download encrypted file from backend.
 *
 * Features:
 * - Automatic retry on network errors
 * - Timeout handling
 * - Request ID tracking
 * - User-friendly error messages
 *
 * @param fileId - File UUID
 * @param config - Optional request configuration
 * @returns Encrypted file blob
 * @throws APIError, NetworkError, or TimeoutError
 */
export async function downloadFile(
  fileId: string,
  config: RequestConfig = {}
): Promise<Uint8Array> {
  const { timeout = DEFAULT_CONFIG.timeout! } = config;

  return withRetry(async () => {
    let response: Response;
    try {
      response = await fetchWithTimeout(
        `${API_BASE_URL}/download/${fileId}`,
        { method: 'GET' },
        timeout
      );
    } catch (error) {
      if (error instanceof TimeoutError) {
        throw error;
      }
      throw new NetworkError(
        'Network error during download',
        error as Error
      );
    }

    // Extract request ID from response headers
    const requestId = response.headers.get('X-Request-ID');

    if (!response.ok) {
      let errorMessage = 'Download failed';
      let errorDetails: unknown = undefined;

      if (response.status === 404) {
        errorMessage = 'File unavailable (expired, deleted, or invalid link)';
      } else {
        try {
          const errorData: ErrorResponse = await response.json();
          errorMessage = errorData.error || errorMessage;
          errorDetails = errorData.details;
        } catch {
          errorMessage = response.statusText || errorMessage;
        }
      }

      throw new APIError(
        errorMessage,
        response.status,
        requestId || undefined,
        errorDetails
      );
    }

    const arrayBuffer = await response.arrayBuffer();
    return new Uint8Array(arrayBuffer);
  }, config);
}

/**
 * Get error message from any error type
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof APIError) {
    return error.message;
  }
  if (error instanceof NetworkError) {
    return 'Network error. Please check your connection and try again.';
  }
  if (error instanceof TimeoutError) {
    return 'Request timed out. Please try again.';
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'An unexpected error occurred';
}
