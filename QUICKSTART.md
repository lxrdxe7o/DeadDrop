# DeadDrop - Quick Start Guide

## 5-Minute Setup (For Demo/Interview)

### Prerequisites Check
```bash
# Verify Docker is installed
docker --version
docker-compose --version

# Verify Node.js is installed (for frontend build)
node --version  # Should be 20+
npm --version
```

---

## Option 1: Backend Only (No WASM compilation needed)

If you don't have Emscripten installed, you can run just the backend to demonstrate the API:

```bash
# Start backend + Redis
docker-compose up -d

# Access API documentation
open http://localhost:8000/api/docs

# Test health endpoint
curl http://localhost:8000/api/v1/health
```

**What you can demo:**
- FastAPI auto-generated API docs (Swagger UI)
- Structured logging output
- Redis TTL management
- Upload/download endpoints (via curl/Postman)

---

## Option 2: Full Stack (With WASM)

### Step 1: Install Emscripten (5 minutes)

```bash
# Clone Emscripten SDK
git clone https://github.com/emscripten-core/emsdk.git
cd emsdk

# Install and activate
./emsdk install latest
./emsdk activate latest
source ./emsdk_env.sh

# Verify installation
emcc --version
```

### Step 2: Build WASM Module (1 minute)

```bash
cd /path/to/DeadDrop/src/cpp
make
```

**Expected output:**
```
✓ WASM module compiled to ../web/public/crypto.js
✓ Generated files: crypto.js, crypto.wasm
```

### Step 3: Build Frontend (2 minutes)

```bash
cd ../web
npm install
npm run build
```

### Step 4: Start All Services (1 minute)

```bash
cd ../..
docker-compose up -d
```

### Step 5: Test the Application

**Upload a file:**
1. Open http://localhost:3000
2. Select any file (< 50MB)
3. Choose expiration: 1 hour / 1 day / 3 days
4. Set max downloads: 1-5
5. Click "Upload"
6. Copy the shareable link

**Download the file:**
1. Open the shareable link in a new tab
2. File automatically decrypts and downloads

**Verify zero-knowledge:**
1. Open browser DevTools (F12)
2. Go to Network tab
3. Upload a file
4. Inspect the `/api/v1/upload` request
5. ✅ Key is NOT in the request (it's after the `#` in the URL)

---

## Option 3: Development Mode (Hot Reload)

### Backend (Terminal 1)
```bash
cd src/py
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start with hot reload
uvicorn main:app --reload
```

### Frontend (Terminal 2)
```bash
cd src/web
npm install
npm run dev
```

### Redis (Terminal 3)
```bash
docker run --rm -p 6379:6379 redis:7-alpine
```

**Access:**
- Frontend: http://localhost:3000 (Vite dev server)
- Backend: http://localhost:8000/api/docs
- Hot reload enabled for both frontend and backend

---

## Troubleshooting

### "WASM module not found"

**Problem:** `crypto.js` and `crypto.wasm` not in `/public/` directory

**Solution:**
```bash
cd src/cpp
make
ls ../web/public/  # Should show crypto.js and crypto.wasm
```

### "Redis connection refused"

**Problem:** Redis container not running

**Solution:**
```bash
docker-compose ps  # Check if redis is running
docker-compose logs redis  # Check for errors
docker-compose restart redis
```

### "Port 8000 already in use"

**Problem:** Another process using port 8000

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill it or change port in docker-compose.yml
docker-compose up -d --force-recreate
```

### "Module not found" errors in frontend

**Problem:** Dependencies not installed

**Solution:**
```bash
cd src/web
rm -rf node_modules package-lock.json
npm install
```

---

## Quick Demo Script (For Interviews)

### 1. Show the Architecture (1 minute)
```bash
cat README.md | head -n 30
```
Point to the ASCII diagram.

### 2. Show the Code Quality (2 minutes)

**Backend (strict typing):**
```bash
cat src/py/models/file.py
```
Point out Pydantic validation, type hints.

**Frontend (strict TypeScript):**
```bash
cat src/web/tsconfig.json
```
Point out `"strict": true`.

**Crypto (WASM integration):**
```bash
cat src/web/src/utils/crypto.ts
```
Point out try-finally memory management.

### 3. Live Demo (3 minutes)

1. Start services: `docker-compose up -d`
2. Open http://localhost:3000
3. Upload a test file
4. Open DevTools → Network tab
5. Show key in URL fragment (`#`)
6. Download file in new tab
7. Show successful decryption

### 4. Infrastructure (1 minute)

```bash
cat docker-compose.yml
cat Caddyfile | head -n 30
```
Point out rate limiting, security headers.

---

## Next Steps After Demo

### For Job Applications

1. **Push to GitHub:**
```bash
git remote add origin https://github.com/yourusername/deaddrop.git
git push -u origin main
```

2. **Add to README:**
   - Live demo link (if deployed)
   - Architecture diagram (draw.io or similar)
   - Screenshots of UI

3. **Record Video Demo:**
   - 2-minute walkthrough
   - Upload to YouTube
   - Add link to README

### For Interviews

1. **Practice explaining:**
   - Why ChaCha20-Poly1305?
   - How does WASM memory management work?
   - Why API versioning?
   - How would you scale this?

2. **Prepare questions:**
   - "What's your deployment strategy?"
   - "Do you use structured logging?"
   - "What's your observability stack?"

3. **Know the numbers:**
   - 50MB max file size
   - 1-5 download limit
   - 1h/1d/3d TTL options
   - ~1,800 lines of code
   - ChaCha20 = 256-bit keys
   - Poly1305 = 128-bit MAC

---

## Production Checklist

Before deploying to production:

- [ ] Update `Caddyfile` with your domain
- [ ] Configure CORS origins
- [ ] Set strong Redis password
- [ ] Enable HTTPS (Caddy handles this)
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure backups (Redis + storage)
- [ ] Review security headers
- [ ] Test rate limiting
- [ ] Set up alerting
- [ ] Document runbook

---

## Common Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# Check Redis
docker-compose exec redis redis-cli ping

# Check backend health
curl http://localhost:8000/api/v1/health

# Clean build (frontend)
cd src/web && rm -rf dist node_modules && npm install && npm run build

# Clean build (WASM)
cd src/cpp && make clean && make
```

---

## Support

For questions or issues:
- Check `DEPLOYMENT.md` for detailed deployment guide
- Check `PROJECT_SUMMARY.md` for architecture deep dive
- Check `README.md` for comprehensive documentation
- Check GitHub Issues (if public repo)

---

**Good luck with your interview! 🚀**

Remember: This project demonstrates senior-level **system design awareness** with **achievable implementation**. Focus on explaining your architectural decisions, not just the code.
