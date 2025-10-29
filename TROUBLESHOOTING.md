# Troubleshooting Guide - Backend Server

## Issue: Health endpoint not loading when starting with venv

### Solution Found

The server IS working correctly! The issue is HOW you start it. Here's the correct way:

### ✅ Correct Way to Start Server

```bash
cd backend

# Method 1: Using uvicorn module (RECOMMENDED)
PYTHONPATH=. ./venv/Scripts/python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Method 2: Using the startup scripts
./start_server.sh    # On Linux/Mac/Git Bash
start_server.bat     # On Windows CMD
```

### ❌ Wrong Way (Causes Issues)

```bash
# DON'T do this - it causes module import issues
./venv/Scripts/python.exe src/main.py
```

**Why?** When you run `python src/main.py` directly:
- The module path gets confused
- Imports like `from src.config import settings` may fail
- The auto-reload feature doesn't work properly

### Testing if Server is Running

After starting the server, test it:

```bash
# Method 1: Using curl
curl http://localhost:8000/health

# Method 2: Using Python test script
cd backend
PYTHONPATH=. ./venv/Scripts/python.exe test_server.py

# Method 3: Open in browser
# Navigate to: http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "environment": "development",
  "version": "0.1.0"
}
```

## Common Issues and Solutions

### Issue 1: "Module 'src' not found"

**Cause:** PYTHONPATH not set correctly

**Solution:**
```bash
export PYTHONPATH=.   # Linux/Mac/Git Bash
set PYTHONPATH=.      # Windows CMD
```

Or always run from backend directory using:
```bash
PYTHONPATH=. ./venv/Scripts/python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Issue 2: "Address already in use" or port 8000 busy

**Cause:** Another process is using port 8000

**Solution:**
```bash
# Find the process
netstat -ano | findstr :8000        # Windows
lsof -i :8000                       # Linux/Mac

# Kill the process (replace PID)
taskkill /PID <PID> /F              # Windows
kill -9 <PID>                       # Linux/Mac
```

### Issue 3: Docker services not running

**Cause:** PostgreSQL or Redis not started

**Solution:**
```bash
cd backend
docker-compose up -d

# Wait for PostgreSQL to be ready
sleep 5

# Check status
docker-compose ps
```

### Issue 4: Database connection errors

**Cause:** Database not initialized or wrong credentials

**Solution:**
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Run migrations
cd backend
PYTHONPATH=. ./venv/Scripts/alembic.exe upgrade head

# Check database
psql -h localhost -U postgres -d chatbot_db
# Password: 123456
```

### Issue 5: "Extra inputs are not permitted" validation error

**Cause:** Pydantic Settings strict mode rejecting .env variables

**Solution:** Already fixed in `src/config.py`:
```python
class Config:
    env_file = ".env"
    case_sensitive = True
    extra = "ignore"  # This allows extra fields from .env
```

### Issue 6: Server starts but health endpoint times out

**Possible Causes:**
1. Server is still loading (wait 5-10 seconds)
2. Firewall blocking localhost connections
3. Server bound to wrong interface

**Solution:**
```bash
# Check server logs
# Look for "Application startup complete" message

# Try different URLs
curl http://localhost:8000/health
curl http://127.0.0.1:8000/health
curl http://0.0.0.0:8000/health

# Check if port is listening
netstat -ano | findstr :8000
```

## Verification Checklist

Run through this checklist to verify everything is working:

- [ ] Docker services running
  ```bash
  docker ps | grep agenthub
  ```

- [ ] Database accessible
  ```bash
  psql -h localhost -U postgres -d chatbot_db -c "SELECT 1"
  ```

- [ ] Redis accessible
  ```bash
  redis-cli ping
  ```

- [ ] Server imports work
  ```bash
  cd backend
  PYTHONPATH=. ./venv/Scripts/python.exe test_server.py
  ```

- [ ] Server is running
  ```bash
  # Server should show: "Application startup complete"
  ```

- [ ] Health endpoint responds
  ```bash
  curl http://localhost:8000/health
  ```

- [ ] API docs accessible
  ```
  http://localhost:8000/docs
  ```

## Server Startup Logs

### Successful Startup Looks Like:

```
INFO:     Will watch for changes in these directories: ['C:\\Users\\...\\backend']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [2528] using WatchFiles
INFO:     Started server process [14280]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

Then you should see a JSON log line:
```json
{
  "environment": "development",
  "api_host": "0.0.0.0",
  "api_port": 8000,
  "event": "application_startup",
  "level": "info",
  "timestamp": "2025-10-29T05:33:01.414393Z"
}
```

### Failed Startup Looks Like:

```
Traceback (most recent call last):
  File "...", line X, in <module>
    from src.config import settings
ModuleNotFoundError: No module named 'src'
```

## Quick Reference

### Start Everything from Scratch

```bash
# 1. Start Docker services
cd backend
docker-compose up -d

# 2. Wait for database
sleep 5

# 3. Run migrations (first time only)
PYTHONPATH=. ./venv/Scripts/alembic.exe upgrade head

# 4. Start server
PYTHONPATH=. ./venv/Scripts/python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# 5. In another terminal, test health endpoint
curl http://localhost:8000/health
```

### Stop Everything

```bash
# Stop server: Press Ctrl+C in server terminal

# Stop Docker services
cd backend
docker-compose down
```

## Additional Help

- **API Documentation**: http://localhost:8000/docs (when server is running)
- **Setup Guide**: See [SETUP_COMPLETE.md](SETUP_COMPLETE.md)
- **Quick Start**: See [QUICK_START.md](QUICK_START.md)
- **Test Script**: Run `backend/test_server.py` to diagnose issues

## Current Server Status

**Server is running!** (Background process ID: fbac77)

To access:
- Health check: http://localhost:8000/health
- API docs: http://localhost:8000/docs
- Root: http://localhost:8000/

The server is running successfully with uvicorn. If you can't access it from your browser, it might be a firewall or network configuration issue on your local machine.
