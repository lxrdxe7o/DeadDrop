/**
 * API client for backend communication
 */

import { API_BASE_URL } from './constants';

export interface UploadResponse {
  id: string;
  expires_at: string;
}

export interface ErrorResponse {
  error: string;
}

/**
 * Upload encrypted file to backend.
 * 
 * @param encryptedData - Encrypted file blob
 * @param filename - Original filename
 * @param ttl - Time to live in seconds
 * @param maxDownloads - Maximum download count (1-5)
 * @returns Upload response with file ID and expiration
 * @throws Error if upload fails
 */
export async function uploadFile(
  encryptedData: Uint8Array,
  filename: string,
  ttl: number,
  maxDownloads: number
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', new Blob([encryptedData]), `${filename}.enc`);
  formData.append('filename', filename);
  formData.append('ttl', ttl.toString());
  formData.append('max_downloads', maxDownloads.toString());
  
  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: 'POST',
    body: formData,
  });
  
  if (!response.ok) {
    const error: ErrorResponse = await response.json();
    throw new Error(error.error || 'Upload failed');
  }
  
  return response.json();
}

/**
 * Download encrypted file from backend.
 * 
 * @param fileId - File UUID
 * @returns Encrypted file blob
 * @throws Error if download fails
 */
export async function downloadFile(fileId: string): Promise<Uint8Array> {
  const response = await fetch(`${API_BASE_URL}/download/${fileId}`);
  
  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('File unavailable (expired, deleted, or invalid link)');
    }
    const error: ErrorResponse = await response.json();
    throw new Error(error.error || 'Download failed');
  }
  
  const arrayBuffer = await response.arrayBuffer();
  return new Uint8Array(arrayBuffer);
}
