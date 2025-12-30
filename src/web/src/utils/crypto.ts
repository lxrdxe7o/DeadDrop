/**
 * WASM Cryptography Wrapper
 * 
 * Provides type-safe interface to the C++/WASM encryption module.
 * Implements strict memory management to prevent leaks.
 * 
 * Interview Talking Points:
 * - "I use try-finally blocks to ensure WASM memory is always freed"
 * - "The .slice() call creates an independent copy before freeing the pointer"
 * - "All memory is allocated by JS and passed to WASM, no C++ allocations"
 */

import type { CryptoModule } from '../types/crypto';

let wasmModule: CryptoModule | null = null;

/**
 * Initialize WASM cryptography module.
 * Must be called once before encrypt/decrypt operations.
 * 
 * @throws Error if initialization fails
 */
export async function initCrypto(): Promise<void> {
  if (wasmModule) {
    return; // Already initialized
  }
  
  try {
    // Load the Emscripten module from the global scope
    // The crypto.js file defines createCryptoModule globally
    // @ts-ignore - createCryptoModule is loaded from crypto.js script
    const createModule = window.createCryptoModule;
    
    if (!createModule) {
      throw new Error('createCryptoModule not found. Ensure crypto.js is loaded.');
    }
    
    wasmModule = await createModule();
  } catch (error) {
    throw new Error(`Failed to initialize crypto module: ${error}`);
  }
}

/**
 * Generate a cryptographically secure 256-bit key.
 * Uses browser's crypto.getRandomValues() API.
 * 
 * @returns 32-byte random key
 */
export function generateKey(): Uint8Array {
  return crypto.getRandomValues(new Uint8Array(32));
}

/**
 * Encrypt file data using ChaCha20-Poly1305.
 * 
 * Output format: [24-byte nonce][ciphertext][16-byte MAC]
 * 
 * @param fileData - Plaintext file bytes
 * @param key - 32-byte encryption key
 * @returns Encrypted blob (fileData.length + 40 bytes)
 * @throws Error if WASM not initialized or encryption fails
 */
export function encryptFile(fileData: Uint8Array, key: Uint8Array): Uint8Array {
  if (!wasmModule) {
    throw new Error('WASM module not initialized. Call initCrypto() first.');
  }
  
  if (key.length !== 32) {
    throw new Error('Key must be exactly 32 bytes (256 bits)');
  }
  
  let inputPtr = 0;
  let keyPtr = 0;
  let outputPtr = 0;
  
  try {
    // Allocate WASM memory
    inputPtr = wasmModule._malloc(fileData.length);
    keyPtr = wasmModule._malloc(32);
    outputPtr = wasmModule._malloc(fileData.length + 40); // +40 for nonce + MAC
    
    // Copy JavaScript ArrayBuffer → WASM heap
    wasmModule.HEAP8.set(fileData, inputPtr);
    wasmModule.HEAP8.set(key, keyPtr);
    
    // Call WASM encryption function
    const outputLen = wasmModule._encrypt_file(
      inputPtr,
      fileData.length,
      keyPtr,
      outputPtr
    );
    
    if (outputLen < 0) {
      throw new Error('Encryption failed (WASM returned error code)');
    }
    
    // Copy WASM heap → JavaScript ArrayBuffer
    // CRITICAL: Use .slice() to create independent copy before freeing memory
    const result = new Uint8Array(
      wasmModule.HEAP8.buffer,
      outputPtr,
      outputLen
    ).slice();
    
    return result;
    
  } finally {
    // CRITICAL: Always free memory, even if error occurs
    if (inputPtr) wasmModule._free(inputPtr);
    if (keyPtr) wasmModule._free(keyPtr);
    if (outputPtr) wasmModule._free(outputPtr);
  }
}

/**
 * Decrypt file data using ChaCha20-Poly1305.
 * 
 * Input format: [24-byte nonce][ciphertext][16-byte MAC]
 * 
 * @param encryptedData - Encrypted blob from encryptFile()
 * @param key - 32-byte decryption key (same as encryption key)
 * @returns Plaintext file bytes
 * @throws Error if decryption fails (wrong key or corrupted data)
 */
export function decryptFile(encryptedData: Uint8Array, key: Uint8Array): Uint8Array {
  if (!wasmModule) {
    throw new Error('WASM module not initialized');
  }
  
  if (key.length !== 32) {
    throw new Error('Key must be exactly 32 bytes');
  }
  
  if (encryptedData.length < 40) {
    throw new Error('Invalid encrypted data (too short - missing nonce/MAC)');
  }
  
  let inputPtr = 0;
  let keyPtr = 0;
  let outputPtr = 0;
  
  try {
    const plaintextLen = encryptedData.length - 40;
    
    // Allocate WASM memory
    inputPtr = wasmModule._malloc(encryptedData.length);
    keyPtr = wasmModule._malloc(32);
    outputPtr = wasmModule._malloc(plaintextLen);
    
    // Copy JS → WASM
    wasmModule.HEAP8.set(encryptedData, inputPtr);
    wasmModule.HEAP8.set(key, keyPtr);
    
    // Call WASM decryption function
    const resultLen = wasmModule._decrypt_file(
      inputPtr,
      encryptedData.length,
      keyPtr,
      outputPtr
    );
    
    if (resultLen < 0) {
      throw new Error('Decryption failed: Invalid key or corrupted file');
    }
    
    // Copy WASM → JS (with independent copy)
    const result = new Uint8Array(
      wasmModule.HEAP8.buffer,
      outputPtr,
      resultLen
    ).slice();
    
    return result;
    
  } finally {
    // Always free memory
    if (inputPtr) wasmModule._free(inputPtr);
    if (keyPtr) wasmModule._free(keyPtr);
    if (outputPtr) wasmModule._free(outputPtr);
  }
}

/**
 * Convert binary key to base64url for URL fragment.
 * 
 * Base64url is URL-safe (no +, /, or = characters).
 * 
 * @param key - 32-byte key
 * @returns Base64url-encoded string
 */
export function keyToBase64Url(key: Uint8Array): string {
  const base64 = btoa(String.fromCharCode(...key));
  return base64
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
}

/**
 * Convert base64url string back to binary key.
 * 
 * @param base64url - Base64url-encoded key from URL fragment
 * @returns 32-byte key
 * @throws Error if invalid base64url
 */
export function base64UrlToKey(base64url: string): Uint8Array {
  try {
    // Convert base64url → standard base64
    const base64 = base64url
      .replace(/-/g, '+')
      .replace(/_/g, '/');
    
    // Decode base64 → binary string
    const binaryString = atob(base64);
    
    // Convert binary string → Uint8Array
    return Uint8Array.from(binaryString, (c) => c.charCodeAt(0));
  } catch (error) {
    throw new Error(`Invalid base64url key: ${error}`);
  }
}
