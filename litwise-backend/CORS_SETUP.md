# CORS Configuration Guide

## How It Works

The backend now automatically detects whether it's running in **development** or **production** based on the `ALLOWED_ORIGINS` environment variable.

### Development (Default)

**When `ALLOWED_ORIGINS` is NOT set:**
```
✅ Allowed origins (automatic):
   - http://localhost:3000
   - http://127.0.0.1:3000
   - https://localhost:3000
```

**Usage:** Just run the app locally, no environment variable needed.

### Production (Custom)

**When `ALLOWED_ORIGINS` IS set:**

Set the environment variable to your production domain(s):

```bash
# For single domain
export ALLOWED_ORIGINS=https://yourdomain.com

# For multiple domains
export ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# With subdomains
export ALLOWED_ORIGINS=https://app.yourdomain.com,https://api.yourdomain.com
```

**On deployment (Railway, Vercel, AWS, etc.):**

1. Go to environment variables settings
2. Add: `ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com`
3. Redeploy

---

## Setup Instructions

### Local Development (No Action Needed)
```bash
# Just start the backend - will use localhost origins automatically
python run.py
# or
uvicorn app:app --reload
```

### Production Deployment

**Option 1: Railway**
```
1. Go to Variables → Add Variable
2. Name: ALLOWED_ORIGINS
3. Value: https://yourdomain.com,https://www.yourdomain.com
4. Deploy
```

**Option 2: Vercel (for backend on separate domain)**
```
1. Environment Variables
2. Add: ALLOWED_ORIGINS = https://yourdomain.com
3. Redeploy
```

**Option 3: AWS/DigitalOcean**
```bash
# In docker or deployment config
ENV ALLOWED_ORIGINS=https://yourdomain.com
```

**Option 4: .env file in production**
```bash
# .env file (never commit this!)
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

---

## Verification

Check logs when app starts:

**Development:**
```
ℹ️  CORS Origins (default development): ['http://localhost:3000', 'http://127.0.0.1:3000', 'https://localhost:3000']
```

**Production:**
```
✅ CORS Origins (from environment): ['https://yourdomain.com', 'https://www.yourdomain.com']
```

---

## Important Notes

✅ **NEVER commit `.env` file to git** (it contains secrets)  
✅ **Use `.env.example` as template** for documentation  
✅ **Always set ALLOWED_ORIGINS in production** (don't leave blank)  
✅ **Include www and non-www versions** if both are used  
✅ **Must use HTTPS** in production (not HTTP)

---

## Examples

### Local Testing
```bash
# Terminal 1: Backend
cd litwise-backend
python run.py
# Logs show: ℹ️  CORS Origins (default development): ...
```

### Production Deployment
```bash
# On Railway/Vercel dashboard:
ALLOWED_ORIGINS=https://myapp.com,https://www.myapp.com

# On AWS using docker:
docker run -e ALLOWED_ORIGINS=https://myapp.com myapp:latest
```

---

## Troubleshooting

**Problem:** CORS error in production  
**Solution:** Check that ALLOWED_ORIGINS environment variable is set to your domain

**Problem:** App not starting in production  
**Solution:** Check logs, make sure ALLOWED_ORIGINS doesn't have invalid characters

**Problem:** Works in dev but not production  
**Solution:** Make sure frontend URL matches exactly (case-sensitive, protocol matters)
