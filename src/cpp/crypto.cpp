/**
 * DeadDrop Cryptography Module
 * 
 * Provides ChaCha20-Poly1305 AEAD encryption/decryption via WebAssembly.
 * Compiled with Emscripten to run in browser environments.
 * 
 * Security Features:
 * - Authenticated Encryption with Associated Data (AEAD)
 * - Constant-time operations (prevents timing attacks)
 * - 256-bit keys (ChaCha20)
 * - 128-bit authentication tags (Poly1305)
 * - 24-byte nonces (XChaCha20 variant for larger nonce space)
 */

#include <cstdint>
#include <cstring>
#include <emscripten/emscripten.h>

extern "C" {
    #include "monocypher.h"
}

/**
 * Encrypts file data using XChaCha20-Poly1305 AEAD
 * 
 * Memory Layout:
 *   Input:  [plaintext]
 *   Output: [24-byte nonce][ciphertext][16-byte MAC]
 * 
 * @param plaintext     Pointer to plaintext data (allocated by JS)
 * @param plaintext_len Length of plaintext in bytes
 * @param key           Pointer to 32-byte encryption key (allocated by JS)
 * @param output        Pointer to output buffer (must be plaintext_len + 40 bytes)
 * @return              Total output length (plaintext_len + 40), or -1 on error
 * 
 * Note: Nonce is generated using Emscripten's binding to crypto.getRandomValues()
 */
extern "C" {
    EMSCRIPTEN_KEEPALIVE
    int encrypt_file(
        const uint8_t* plaintext,
        size_t plaintext_len,
        const uint8_t* key,
        uint8_t* output
    ) {
        // Input validation
        if (!plaintext || !key || !output || plaintext_len == 0) {
            return -1;
        }

        // Generate random 24-byte nonce for XChaCha20
        // Note: Emscripten provides EM_JS binding to crypto.getRandomValues()
        uint8_t nonce[24];
        
        // Use Emscripten's random number generator (secure in browser context)
        EM_ASM({
            var noncePtr = $0;
            var nonceArray = new Uint8Array(Module.HEAP8.buffer, noncePtr, 24);
            crypto.getRandomValues(nonceArray);
        }, nonce);

        // Output buffer layout: [nonce | ciphertext | mac]
        uint8_t* nonce_out = output;
        uint8_t* ciphertext = output + 24;
        uint8_t* mac = output + 24 + plaintext_len;

        // Copy nonce to output (needed for decryption)
        std::memcpy(nonce_out, nonce, 24);

        // Perform authenticated encryption
        // crypto_aead_lock: ChaCha20 encryption + Poly1305 MAC
        crypto_aead_lock(
            mac,            // 16-byte MAC output
            ciphertext,     // Ciphertext output (same size as plaintext)
            key,            // 32-byte encryption key
            nonce,          // 24-byte nonce
            nullptr,        // No additional authenticated data (AAD)
            0,              // AAD length
            plaintext,      // Input plaintext
            plaintext_len   // Plaintext length
        );

        // Securely wipe nonce from stack (defense in depth)
        crypto_wipe(nonce, sizeof(nonce));

        return static_cast<int>(plaintext_len + 40);
    }

    /**
     * Decrypts file data using XChaCha20-Poly1305 AEAD
     * 
     * Memory Layout:
     *   Input:  [24-byte nonce][ciphertext][16-byte MAC]
     *   Output: [plaintext]
     * 
     * @param encrypted     Pointer to encrypted blob (nonce + ciphertext + MAC)
     * @param encrypted_len Total length of encrypted blob
     * @param key           Pointer to 32-byte decryption key
     * @param plaintext     Pointer to output buffer (must be encrypted_len - 40 bytes)
     * @return              Plaintext length on success, -1 on MAC verification failure
     * 
     * Security Note: Returns -1 on authentication failure (constant-time comparison)
     */
    EMSCRIPTEN_KEEPALIVE
    int decrypt_file(
        const uint8_t* encrypted,
        size_t encrypted_len,
        const uint8_t* key,
        uint8_t* plaintext
    ) {
        // Input validation
        if (!encrypted || !key || !plaintext || encrypted_len < 40) {
            return -1;
        }

        const size_t plaintext_len = encrypted_len - 40;

        // Parse input buffer: [nonce | ciphertext | mac]
        const uint8_t* nonce = encrypted;
        const uint8_t* ciphertext = encrypted + 24;
        const uint8_t* mac = encrypted + 24 + plaintext_len;

        // Perform authenticated decryption
        // crypto_aead_unlock: ChaCha20 decryption + Poly1305 MAC verification
        // Returns 0 on success, -1 if MAC verification fails (constant-time)
        int result = crypto_aead_unlock(
            plaintext,      // Plaintext output
            mac,            // 16-byte MAC to verify
            key,            // 32-byte decryption key
            nonce,          // 24-byte nonce
            nullptr,        // No AAD
            0,              // AAD length
            ciphertext,     // Input ciphertext
            plaintext_len   // Ciphertext length
        );

        // Return plaintext length on success, -1 on authentication failure
        return (result == 0) ? static_cast<int>(plaintext_len) : -1;
    }
}
