/**
 * TypeScript definitions for WASM crypto module
 */

export interface CryptoModule {
  _malloc(size: number): number;
  _free(ptr: number): void;
  _encrypt_file(
    plaintext: number,
    plaintextLen: number,
    key: number,
    output: number
  ): number;
  _decrypt_file(
    encrypted: number,
    encryptedLen: number,
    key: number,
    output: number
  ): number;
  HEAP8: Int8Array;
}

export type CreateCryptoModule = () => Promise<CryptoModule>;
