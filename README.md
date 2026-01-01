# DeadDrop - Zero-Knowledge Ephemeral File Sharing

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**DeadDrop** is a trust-no-one file sharing service where files are encrypted client-side using WebAssembly. The server never sees your encryption key or plaintext data.

---

## Features

- **Client-Side Encryption**: Files encrypted in-browser using ChaCha20-Poly1305 (C++/WASM)
- **Zero-Knowledge**: Encryption key stored in URL fragment (never sent to server)
- **Ephemeral Storage**: Files auto-delete after expiration or download limit
- **Configurable TTL**: Choose 1 hour, 1 day, or 3 days
- **Download Limits**: Set 1-5 downloads before auto-deletion
- **Type-Safe**: Strict TypeScript + Python type hints
- **Production-Ready**: Docker Compose + Caddy reverse proxy with automatic HTTPS

---

## Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Browser   │         │   FastAPI    │         │    Redis    │
│  (React +   │◄───────►│   Backend    │◄───────►│  (Metadata) │
│    WASM)    │         │              │         │             │
└─────────────┘         └──────────────┘         └─────────────┘
      │                        │
      │  Encryption Key        │  Encrypted Blob
      │  (Never Sent!)         │
      │                        ▼
      │                 ┌─────────────┐
      │                 │   Storage   │
      └────────────────►│ (Disk/S3)   │
         Decryption     └─────────────┘
```

### Data Flow

**Upload:**

1. User selects file in browser
2. Generate random 256-bit key via `crypto.getRandomValues()`
3. Encrypt file using ChaCha20-Poly1305 (WASM)
4. Upload encrypted blob to server
5. Server stores blob + metadata in Redis (with TTL)
6. Return shareable link: `https://domain/download?id={UUID}#{KEY}`

**Download:**

1. Parse UUID (query param) and key (URL fragment)
2. Download encrypted blob from server (key never transmitted)
3. Decrypt in browser using WASM
4. Trigger browser download of plaintext file
5. Server increments download count; deletes if limit reached

---

## Quick Start

### Prerequisites

- **Docker & Docker Compose**
- **Emscripten SDK** (for building WASM module)
- **Node.js 20+** (for frontend development)

### Setup

1. **Clone repository:**

```bash
git clone https://github.com/yourusername/deaddrop.git
cd deaddrop
```

2. **Build WASM cryptography module:**

```bash
# Install Emscripten (first time only)
git clone https://github.com/emscripten-core/emsdk.git
cd emsdk
./emsdk install latest
./emsdk activate latest
source ./emsdk_env.sh
cd ..

# Build WASM module
cd src/cpp
make
cd ../..
```

3. **Build frontend:**

```bash
cd src/web
npm install
npm run build
cd ../..
```

4. **Start services:**

```bash
docker-compose up -d
```

5. **Access application:**
   - **Frontend**: http://localhost:3000
   - **Backend API**: http://localhost:8000/api/docs
   - **Redis**: localhost:6379

---

## Development

### Backend (FastAPI)

```bash
cd src/py
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run with hot reload
uvicorn main:app --reload
```

### Frontend (React + Vite)

```bash
cd src/web
npm install
npm run dev  # Starts on http://localhost:3000
```

### Type Checking

```bash
# Python
cd src/py
mypy .

# TypeScript
cd src/web
npm run build  # tsc runs automatically
```

---

## Production Deployment

1. **Build frontend:**

```bash
cd src/web
npm run build
```

2. **Update Caddyfile:**
   - Replace `deaddrop.yourdomain.com` with your domain
   - Update CORS origins in `docker-compose.prod.yml`

3. **Deploy:**

```bash
docker-compose -f docker-compose.prod.yml up -d
```

4. **DNS Configuration:**
   - Point your domain to the server IP
   - Caddy automatically provisions SSL via Let's Encrypt

---

## Security Considerations

### Zero-Knowledge Architecture

The encryption key is stored in the URL fragment (after `#`). According to RFC 3986, fragments are NEVER sent in HTTP requests—the browser strips them before transmission. You can verify this in browser DevTools (Network tab).

### Current Limitations

⚠️ **Metadata Privacy**: Original filenames are stored in plaintext on the server for MVP.

**Future Enhancement**: Encrypt metadata client-side for full zero-knowledge architecture.

### Best Practices

- **HTTPS Required**: Deploy behind Caddy for automatic TLS
- **Rate Limiting**: Caddy enforces 10 uploads/hour per IP
- **Generic Errors**: Server returns "File unavailable" for all failures (prevents enumeration attacks)
- **Structured Logging**: No sensitive data in logs (IP addresses hashed)

---

## QA

### 1. "Why ChaCha20-Poly1305 over AES-256-GCM?"

"ChaCha20-Poly1305 is a constant-time AEAD cipher that doesn't rely on hardware acceleration (AES-NI). I used Monocypher—a single-file, audited library (2000 LOC)—which compiles cleanly to WASM without OpenSSL's complex dependencies."

### 2. "How do you prevent memory leaks in WASM?"

"I use a strict try-finally pattern in TypeScript where every `_malloc()` has a corresponding `_free()` in the finally block. I also use `.slice()` to copy data out of the WASM heap before freeing, preventing dangling pointer issues."

### 3. "Why React instead of Vanilla JS?"

"React's component model makes it easier to manage the encryption state machine (idle → encrypting → uploading → done). It's also what most companies use, so it demonstrates job-ready skills."

### 4. "How does the server ensure it never sees the key?"

"The key lives in the URL fragment (after `#`). Per RFC 3986, fragments are client-side only. I can demonstrate this live in DevTools during an interview."

### 5. "What if someone downloads the file twice?"

"The default limit is 1, but I made it configurable (1-5) to handle network failures. After max downloads, a FastAPI background task immediately deletes the file from disk and Redis, making it unrecoverable."

### 6. "How would you scale this to handle 10,000 concurrent users?"

"Current architecture uses local disk storage. I'd swap `LocalStorage` for `S3Storage` (same Protocol interface), use Redis Cluster for HA, and deploy FastAPI behind a load balancer. Client-side encryption means server load is just network I/O."

### 7. "Why API versioning (`/api/v1/`)?"

"I namespaced endpoints to support future protocol changes. If I needed to upgrade the encryption algorithm or modify the upload schema, I could release v2 without breaking existing clients."

### 8. "Why structured logging (JSON) instead of `print()`?"

"Structured logs are machine-parseable for log aggregation tools (ELK stack, Datadog). I log events, not data—no sensitive information. This helps detect brute force attempts while maintaining user privacy."

### 9. "Why rate limiting in Caddy instead of Python?"

"Handling rate limiting at the reverse proxy level protects the application server from getting overloaded by DoS attacks before the request even hits Python. It's also much faster."

---

## Tech Stack

- **Frontend**: React 18 + TypeScript (strict mode) + Vite
- **Crypto**: C++20 + Monocypher → WebAssembly (Emscripten)
- **Backend**: Python 3.11 + FastAPI + Pydantic v2
- **Database**: Redis 7 (metadata + TTL management)
- **Storage**: Local filesystem (abstraction layer for S3 migration)
- **Infrastructure**: Docker Compose + Caddy (automatic HTTPS)

---

## Project Structure

```
DeadDrop/
├── src/
│   ├── cpp/                # Cryptography module (C++/WASM)
│   │   ├── crypto.cpp
│   │   ├── monocypher.{c,h}
│   │   ├── Makefile
│   │   └── README.md
│   ├── py/                 # Backend (FastAPI)
│   │   ├── main.py
│   │   ├── api/v1/
│   │   ├── models/
│   │   ├── services/
│   │   ├── core/
│   │   └── requirements.txt
│   └── web/                # Frontend (React)
│       ├── src/
│       │   ├── pages/
│       │   ├── hooks/
│       │   ├── utils/
│       │   └── types/
│       ├── public/
│       ├── package.json
│       └── vite.config.ts
├── docker-compose.yml      # Development
├── docker-compose.prod.yml # Production
├── Caddyfile               # Reverse proxy config
└── LICENSE                 # MIT License
```

---

## API Reference

### POST /api/v1/upload

Upload encrypted file blob.

**Request:**

- `file` (binary): Encrypted file data
- `ttl` (int): Time to live (3600, 86400, or 259200 seconds)
- `max_downloads` (int): Maximum downloads (1-5)
- `filename` (string): Original filename

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "expires_at": "2025-12-31T22:00:00Z"
}
```

### GET /api/v1/download/{uuid}

Download encrypted file blob.

**Response:**

- `200`: Encrypted file stream (`application/octet-stream`)
- `404`: File unavailable (expired/deleted/invalid)

---

## License

MIT License - see [LICENSE](LICENSE) file

---

## Contributing

This is a portfolio project demonstrating senior-level system design with junior-level implementation scope. Pull requests welcome!

---

## Author

Built as a portfolio project to demonstrate:

- ✅ Zero-knowledge cryptography (client-side encryption)
- ✅ Full-stack development (React + FastAPI)
- ✅ WebAssembly integration (C++ → WASM)
- ✅ Production-ready infrastructure (Docker + Caddy)
- ✅ Type safety (TypeScript strict + Python mypy)
- ✅ Security awareness (rate limiting, structured logging, generic errors)

**Perfect for showing to potential employers during technical interviews.**
