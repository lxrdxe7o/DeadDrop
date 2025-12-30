# Troubleshooting Guide

## WASM Module Loading Issues

### Error: "TypeError: e is not a function"

**Problem**: The WASM crypto module isn't loading correctly in the browser.

**Solution Applied**:
1. Changed from ES6 module import to script tag loading
2. Exposed `createCryptoModule` to `window` object globally
3. Added `<script src="/crypto.js"></script>` to index.html

**Verify Fix**:
```javascript
// In browser console:
console.log(typeof window.createCryptoModule);
// Should output: "function"
```

### Error: "WASM module not initialized"

**Cause**: The `initCrypto()` function wasn't called before trying to encrypt/decrypt.

**Solution**: The React app automatically calls `initCrypto()` via the `useCrypto` hook on startup.

**Verify**:
Check that the App component shows "Loading cryptography module..." before rendering content.

---

## Backend Issues

### Error: "error parsing value for field 'cors_origins'"

**Problem**: Pydantic Settings couldn't parse comma-separated CORS origins.

**Solution**: Added `@field_validator` to parse comma-separated string into list.

**Code**:
```python
@field_validator('cors_origins', mode='before')
@classmethod
def parse_cors_origins(cls, v):
    if isinstance(v, str):
        return [origin.strip() for origin in v.split(',')]
    return v
```

### Error: "Connection refused" to Redis

**Problem**: Redis container not running or not accessible.

**Solution**:
```bash
# Check if Redis is running
docker-compose ps

# Restart Redis
docker-compose restart redis

# Check logs
docker-compose logs redis
```

---

## TypeScript Build Issues

### Error: "Type 'Uint8Array<ArrayBufferLike>' is not assignable to type 'BlobPart'"

**Problem**: TypeScript strict mode detected incompatible types between Uint8Array and Blob constructor.

**Solution**: Wrap Uint8Array in a new constructor to ensure correct type:
```typescript
// Instead of:
new Blob([encryptedData])

// Use:
new Blob([new Uint8Array(encryptedData)])
```

---

## Emscripten Compilation Issues

### Error: "invalid argument '-std=c++20' not allowed with 'C'"

**Problem**: Trying to compile C code (monocypher.c) with C++ flags.

**Solution**: Split compilation into separate C and C++ steps in Makefile:
```makefile
# Compile C file
$(EMCC) -O3 -c monocypher.c -o /tmp/monocypher.o

# Compile C++ file
$(EMXX) -O3 -std=c++20 -c crypto.cpp -o /tmp/crypto.o

# Link together
$(EMXX) $(FLAGS) /tmp/monocypher.o /tmp/crypto.o -o crypto.js
```

---

## Docker Issues

### Error: "Docker Compose requires buildx plugin"

**Cause**: Warning from newer Docker Compose versions.

**Solution**: Ignore this warning - it doesn't affect functionality. Or install buildx:
```bash
docker buildx install
```

### Error: Container keeps restarting

**Check logs**:
```bash
docker-compose logs -f backend
```

**Common causes**:
1. Python import errors (check requirements.txt)
2. Redis connection failures (check REDIS_URL)
3. Port conflicts (change ports in docker-compose.yml)

---

## Frontend Issues

### Blank page in browser

**Check**:
1. Open DevTools (F12) → Console tab
2. Look for JavaScript errors
3. Verify crypto.js loaded: Network tab should show 200 for /crypto.js

**Common causes**:
1. WASM module failed to load (check console errors)
2. API backend not running (check http://localhost:8000/api/v1/health)
3. CORS errors (check backend CORS_ORIGINS setting)

### Upload fails with network error

**Check**:
1. Backend is running: `curl http://localhost:8000/api/v1/health`
2. CORS is configured correctly
3. File size is under 50MB

### Download fails / file won't decrypt

**Check**:
1. URL contains both `?id=UUID` and `#KEY` parts
2. Key wasn't truncated when copying link
3. File hasn't expired or reached download limit
4. Browser console for decryption errors

---

## Testing the System

### Manual Test Flow

1. **Backend Health Check**:
```bash
curl http://localhost:8000/api/v1/health
# Expected: {"status":"healthy","version":"1.0.0","service":"DeadDrop"}
```

2. **Frontend Access**:
```bash
curl -I http://localhost:3000/
# Expected: HTTP/1.0 200 OK
```

3. **WASM Module Check** (in browser console):
```javascript
typeof window.createCryptoModule
// Expected: "function"

await window.createCryptoModule()
// Expected: Object with _encrypt_file, _decrypt_file, etc.
```

4. **Full Upload/Download Flow**:
   - Open http://localhost:3000
   - Select a small test file
   - Click Upload
   - Copy share link
   - Open link in new tab
   - File should download and decrypt

### API Testing with curl

**Upload a file**:
```bash
echo "test content" > test.txt

# Encrypt it first (would need crypto.js, skip for API test)
# For testing, just upload plain text:
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@test.txt" \
  -F "filename=test.txt" \
  -F "ttl=3600" \
  -F "max_downloads=1"
```

**Expected response**:
```json
{
  "id": "some-uuid-here",
  "expires_at": "2025-12-31T..."
}
```

---

## Performance Issues

### Slow encryption/decryption

**Causes**:
1. Large files (> 10MB) take time to process in browser
2. Old/slow computer
3. Browser running many tabs

**Solutions**:
- Keep files under 50MB (current limit)
- Close unnecessary browser tabs
- Use modern browser (Chrome/Firefox/Edge)

### High memory usage

**Cause**: WASM allocates memory for encryption

**Solution**: Memory is freed after operation completes. If issues persist:
1. Refresh browser page
2. Reduce file size
3. Close and reopen browser

---

## Getting Help

### Collect Debug Information

```bash
# System info
docker-compose ps
docker-compose logs backend --tail=50
curl http://localhost:8000/api/v1/health

# WASM files
ls -lh src/web/dist/*.{js,wasm}

# Frontend build
ls -lh src/web/dist/
```

### Common Commands

```bash
# Restart everything
docker-compose restart

# Rebuild backend
docker-compose up -d --build backend

# View live logs
docker-compose logs -f

# Stop everything
docker-compose down

# Nuclear option (clean restart)
docker-compose down -v
docker-compose up -d --build
```

---

## Security Considerations

### Never commit .env files

The `.env` file may contain secrets. It's already in `.gitignore`.

### Verify zero-knowledge

In browser DevTools → Network tab:
1. Upload a file
2. Find the POST request to /api/v1/upload
3. Check request payload
4. Verify the encryption key is NOT in the request

The key should only be in the URL fragment (after `#`).

---

## Production Deployment Issues

### SSL/HTTPS not working

**Cause**: Caddy needs proper DNS configuration

**Solution**:
1. Point your domain to the server IP
2. Update Caddyfile with your domain
3. Ensure ports 80 and 443 are open
4. Caddy will automatically get SSL cert from Let's Encrypt

### Rate limiting too strict

**Problem**: Users blocked after few uploads

**Solution**: Edit Caddyfile:
```caddy
rate_limit {
    zone upload {
        key {remote_host}
        events 100  # Increase from 10
        window 1h
    }
}
```

Then restart:
```bash
docker-compose -f docker-compose.prod.yml restart caddy
```

---

For more help, check:
- README.md - Full documentation
- PROJECT_SUMMARY.md - Architecture details
- QUICKSTART.md - Setup guide
- DEPLOYMENT.md - Production deployment
