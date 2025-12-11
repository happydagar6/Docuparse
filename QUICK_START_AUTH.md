# 🚀 Quick Start - Authentication Deployment

## Prerequisites Check
- [x] Frontend auth complete (already done)
- [ ] Backend ready for auth integration
- [ ] Supabase project created
- [ ] Have access to Supabase dashboard

---

## 5-Minute Setup

### 1️⃣ Install Backend Dependency (30 seconds)
```bash
cd litwise-backend
pip install PyJWT==2.10.1
```

### 2️⃣ Add Environment Variables (2 minutes)

**File**: `litwise-backend/.env`

```env
SUPABASE_URL=https://YOUR-PROJECT.supabase.co
SUPABASE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret
```

**Get these from**: https://app.supabase.com → Your Project → Settings → API

- `SUPABASE_URL`: Project URL
- `SUPABASE_KEY`: service_role key (⚠️ Keep secret!)
- `SUPABASE_JWT_SECRET`: JWT Secret (under JWT Settings)

### 3️⃣ Execute Database Policies (2 minutes)

1. Open: https://app.supabase.com
2. Go to: **SQL Editor**
3. Copy all content from: `litwise-backend/rls_policies.sql`
4. Paste and click **Run**
5. Wait for "Success" message

### 4️⃣ Restart Servers (30 seconds)

**Backend**:
```bash
cd litwise-backend
python run.py
```

**Frontend** (in new terminal):
```bash
cd litwise-frontend
npm run dev
```

---

## ✅ Verify It Works

### Test 1: Signup (1 minute)
1. Go to: http://localhost:3000/signup
2. Create account: test@example.com / password123
3. Should see "Success" and redirect to home

### Test 2: Upload Paper (1 minute)
1. Login if not already
2. Go to Upload page
3. Upload any PDF
4. Should see paper in your list

### Test 3: Data Isolation (2 minutes)
1. Logout (user menu → Logout)
2. Create second account: test2@example.com
3. Upload different paper
4. **Verify**: You only see the second paper (not the first user's paper)

---

## 🚨 Troubleshooting

### Error: "Invalid JWT token"
```bash
# Check your JWT secret is correct
# Should match Supabase dashboard exactly
```

### Error: "Module not found: PyJWT"
```bash
pip install PyJWT==2.10.1
```

### Error: "SUPABASE_JWT_SECRET not found"
```bash
# Add to litwise-backend/.env file
SUPABASE_JWT_SECRET=your-secret-here
```

### Papers not showing up
```sql
-- In Supabase SQL Editor, check if user_id is set:
SELECT id, title, user_id FROM papers;

-- If NULL, assign to your user:
SELECT id FROM auth.users;  -- Copy your user ID
UPDATE papers SET user_id = 'your-user-id' WHERE user_id IS NULL;
```

---

## 📋 Quick Checklist

- [ ] PyJWT installed: `pip list | grep PyJWT`
- [ ] .env has SUPABASE_JWT_SECRET
- [ ] RLS policies executed (check Supabase SQL history)
- [ ] Both servers running (no errors in terminal)
- [ ] Can signup new user
- [ ] Can login
- [ ] Can upload paper
- [ ] User A can't see User B's papers

---

## 🎯 What Changed

### Before
- No authentication
- All users saw all papers
- No user tracking
- No data privacy

### After
✅ User signup/login required
✅ Each user sees only their papers
✅ All endpoints protected
✅ Database-level security (RLS)
✅ JWT token validation

---

## 📁 Key Files

| File | Purpose | Location |
|------|---------|----------|
| `auth_middleware.py` | JWT validation | `litwise-backend/` |
| `rls_policies.sql` | Database security | `litwise-backend/` |
| `.env` | Secrets | `litwise-backend/.env` |
| `requirements.txt` | Dependencies | `litwise-backend/` |

---

## 🆘 Get Help

1. **Detailed Guide**: See `AUTHENTICATION_DEPLOYMENT_GUIDE.md`
2. **Implementation Summary**: See `BACKEND_AUTH_IMPLEMENTATION_SUMMARY.md`
3. **Supabase Docs**: https://supabase.com/docs/guides/auth
4. **JWT Debugger**: https://jwt.io (paste token to debug)

---

## 🎉 Success!

If you can:
- Create an account ✅
- Login ✅
- Upload a paper ✅
- Not see other users' papers ✅

**You're done!** 🎊

---

**Time to Deploy**: ~5 minutes  
**Difficulty**: Easy  
**Status**: Ready for Production ✅
