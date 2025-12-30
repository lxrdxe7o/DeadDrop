/**
 * React hook for WASM module initialization
 */

import { useEffect, useState } from 'react';
import { initCrypto } from '../utils/crypto';

interface UseCryptoResult {
  isReady: boolean;
  error: string | null;
}

/**
 * Initialize WASM cryptography module on app startup.
 * 
 * @returns Object with isReady flag and error message
 */
export function useCrypto(): UseCryptoResult {
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    initCrypto()
      .then(() => setIsReady(true))
      .catch((err) => setError(err instanceof Error ? err.message : 'Unknown error'));
  }, []);
  
  return { isReady, error };
}
