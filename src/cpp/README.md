# Cryptography Module (C++/WASM)

## Overview

This module provides **ChaCha20-Poly1305** authenticated encryption for the DeadDrop frontend, compiled to WebAssembly using Emscripten.

## Why ChaCha20-Poly1305?

- **AEAD (Authenticated Encryption with Associated Data)**: Provides both confidentiality and integrity
- **Constant-time**: Prevents timing side-channel attacks
- **Modern**: Recommended by IETF (RFC 8439), used in TLS 1.3
- **Performance**: Fast on all platforms (no need for AES-NI hardware support)
- **Large nonce space**: 24-byte nonces (XChaCha20) prevent reuse issues

## Why Monocypher?

- **Audited**: Third-party security audit completed (2018)
- **Minimal**: ~2,000 lines of code, easy to review
- **WASM-friendly**: No external dependencies, pure C99
- **Public Domain**: CC0 license (no attribution required)
- **Battle-tested**: Used in production by multiple projects

## Build Instructions

### Prerequisites

1. Install Emscripten SDK:
```bash
git clone https://github.com/emscripten-core/emsdk.git
cd emsdk
./emsdk install latest
./emsdk activate latest
source ./emsdk_env.sh
```

2. Verify installation:
```bash
emcc --version
# Should output: emcc (Emscripten gcc/clang-like replacement) 3.x.x
```

### Compilation

```bash
cd src/cpp
make
```

This generates:
- `../web/public/crypto.js` - Emscripten glue code
- `../web/public/crypto.wasm` - WebAssembly binary

### Clean Build

```bash
make clean
```

## API Reference

### `encrypt_file(plaintext, plaintext_len, key, output) -> int`

Encrypts data using ChaCha20-Poly1305.

**Parameters:**
- `plaintext`: Pointer to plaintext data (JS-allocated)
- `plaintext_len`: Length of plaintext in bytes
- `key`: Pointer to 32-byte encryption key
- `output`: Pointer to output buffer (must be `plaintext_len + 40` bytes)

**Returns:**
- Output length (`plaintext_len + 40`) on success
- `-1` on error

**Output Format:**
```
[24-byte nonce][ciphertext][16-byte MAC]
```

### `decrypt_file(encrypted, encrypted_len, key, plaintext) -> int`

Decrypts and verifies data.

**Parameters:**
- `encrypted`: Pointer to encrypted blob (nonce + ciphertext + MAC)
- `encrypted_len`: Total length of encrypted data
- `key`: Pointer to 32-byte decryption key
- `plaintext`: Pointer to output buffer (must be `encrypted_len - 40` bytes)

**Returns:**
- Plaintext length on success
- `-1` on MAC verification failure (wrong key or corrupted data)

## Security Considerations

### Nonce Generation
- Uses browser's `crypto.getRandomValues()` via Emscripten binding
- 24-byte nonces (XChaCha20) provide 2^192 security margin
- Nonces are prepended to ciphertext (needed for decryption)

### Memory Safety
- All memory allocated by JavaScript (WASM doesn't allocate)
- Sensitive data wiped using `crypto_wipe()` (Monocypher utility)
- No dynamic allocation in C++ code (prevents memory leaks)

### Authentication
- Poly1305 MAC provides 128-bit authentication strength
- Constant-time MAC verification (prevents timing attacks)
- Tampering or wrong key results in `-1` return (no plaintext output)

## Testing (Optional)

To verify the module works, create a minimal HTML test:

```html
<!DOCTYPE html>
<html>
<head><title>WASM Crypto Test</title></head>
<body>
<script src="crypto.js"></script>
<script>
createCryptoModule().then(Module => {
    // Generate test data
    const plaintext = new Uint8Array([72, 101, 108, 108, 111]); // "Hello"
    const key = crypto.getRandomValues(new Uint8Array(32));
    
    // Allocate WASM memory
    const ptPtr = Module._malloc(plaintext.length);
    const keyPtr = Module._malloc(32);
    const outPtr = Module._malloc(plaintext.length + 40);
    
    // Copy to WASM heap
    Module.HEAP8.set(plaintext, ptPtr);
    Module.HEAP8.set(key, keyPtr);
    
    // Encrypt
    const encLen = Module._encrypt_file(ptPtr, plaintext.length, keyPtr, outPtr);
    console.log('Encrypted length:', encLen);
    
    // Decrypt
    const decPtr = Module._malloc(plaintext.length);
    const decLen = Module._decrypt_file(outPtr, encLen, keyPtr, decPtr);
    console.log('Decrypted length:', decLen);
    
    // Verify
    const decrypted = new Uint8Array(Module.HEAP8.buffer, decPtr, decLen);
    console.log('Match:', JSON.stringify([...plaintext]) === JSON.stringify([...decrypted]));
    
    // Free memory
    Module._free(ptPtr);
    Module._free(keyPtr);
    Module._free(outPtr);
    Module._free(decPtr);
});
</script>
</body>
</html>
```

## Interview Talking Points

1. **"Why not OpenSSL?"**
   - "OpenSSL has complex dependencies that bloat WASM binaries. Monocypher is a single-file, audited library perfect for browser environments."

2. **"How do you prevent memory leaks?"**
   - "All memory is allocated by JavaScript using `_malloc()` and freed with `_free()` in try-finally blocks. The C++ code never allocates memory, preventing leaks."

3. **"What if someone tampers with the ciphertext?"**
   - "Poly1305 MAC verification happens in constant-time. If the MAC doesn't match, `decrypt_file()` returns -1 without outputting any plaintext."

4. **"Why XChaCha20 instead of regular ChaCha20?"**
   - "XChaCha20 uses 24-byte nonces instead of 12-byte, providing a much larger nonce space. This virtually eliminates the risk of nonce reuse, even with random generation."

## License

The Monocypher library is **Public Domain (CC0)**. The DeadDrop wrapper code is licensed under **MIT** (see root LICENSE file).
