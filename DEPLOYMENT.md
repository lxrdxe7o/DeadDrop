# Deployment Guide

## Development Deployment

1. **Install Emscripten:**
```bash
git clone https://github.com/emscripten-core/emsdk.git
cd emsdk
./emsdk install latest
./emsdk activate latest
source ./emsdk_env.sh
cd ..
```

2. **Build WASM module:**
```bash
cd src/cpp
make
```

3. **Build frontend:**
```bash
cd ../web
npm install
npm run build
```

4. **Start services:**
```bash
docker-compose up -d
```

## Production Deployment

### Option 1: Docker Compose (Recommended)

1. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with production values
```

2. **Update Caddyfile:**
   - Replace `deaddrop.yourdomain.com` with your actual domain

3. **Build and deploy:**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Option 2: Kubernetes (Advanced)

Coming soon...

## SSL/TLS Configuration

Caddy automatically provisions SSL certificates via Let's Encrypt.

**Requirements:**
- Domain pointing to your server
- Ports 80 and 443 open
- Valid email in Caddyfile (for Let's Encrypt notifications)

## Monitoring

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

### Redis Check

```bash
docker-compose exec redis redis-cli ping
```

### Logs

```bash
# Backend logs
docker-compose logs -f backend

# Caddy logs
docker-compose -f docker-compose.prod.yml logs -f caddy
```

## Backup Strategy

### Redis Data
```bash
# Manual backup
docker-compose exec redis redis-cli BGSAVE

# Automated backup (add to cron)
0 2 * * * docker-compose exec redis redis-cli BGSAVE
```

### File Storage
```bash
# Backup storage directory
tar -czf storage-backup-$(date +%Y%m%d).tar.gz storage/
```

## Scaling

### Horizontal Scaling

1. **Replace LocalStorage with S3Storage:**
   - Uncomment S3Storage class in `src/py/services/storage.py`
   - Update dependencies: `boto3`
   - Configure AWS credentials

2. **Use Redis Cluster:**
   - Update `docker-compose.yml` with Redis Cluster configuration

3. **Load Balancer:**
   - Deploy multiple FastAPI instances
   - Use Caddy or nginx as load balancer

### Performance Tuning

**FastAPI:**
```bash
# Increase workers
uvicorn main:app --workers 4 --host 0.0.0.0 --port 8000
```

**Redis:**
```bash
# Increase max memory
redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
```

## Security Checklist

- [ ] HTTPS enabled (Caddy automatic)
- [ ] Rate limiting configured
- [ ] CORS origins restricted
- [ ] File size limits enforced
- [ ] Generic error messages (no info leakage)
- [ ] Structured logging (no secrets)
- [ ] Non-root Docker user
- [ ] Regular security updates

## Troubleshooting

### WASM module not loading

Check browser console for errors. Ensure `crypto.js` and `crypto.wasm` are in `/public/` directory.

### Redis connection failed

```bash
docker-compose logs redis
docker-compose exec backend ping redis -c 1
```

### File upload fails

Check storage permissions:
```bash
chmod 755 storage/
chown -R 1000:1000 storage/
```
