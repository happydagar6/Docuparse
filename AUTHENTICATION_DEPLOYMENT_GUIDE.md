# Authentication Deployment Guide - Litwise Project

## ✅ Implementation Complete

Full Supabase Authentication with Row Level Security (RLS) has been implemented.

---

## 📋 Prerequisites

1. **Supabase Project**: Active project at https://app.supabase.com
2. **Frontend Dependencies**: Already installed (`@supabase/supabase-js`, `@supabase/ssr`)
3. **Backend Dependencies**: Need to install `PyJWT==2.10.1`

---

## 🚀 Deployment Steps

### Step 1: Backend Dependencies

```bash
cd litwise-backend
pip install PyJWT==2.10.1
```

Or use requirements.txt (already updated):
```bash
pip install -r requirements.txt
```

### Step 2: Environment Variables

#### Backend (.env in litwise-backend/)

Add these variables to your backend `.env` file:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key-here
SUPABASE_JWT_SECRET=your-jwt-secret-here
```

**How to get these values:**

1. Go to https://app.supabase.com
2. Select your project
3. Navigate to **Settings** → **API**
4. Copy:
   - **Project URL** → `SUPABASE_URL`
   - **service_role key** → `SUPABASE_KEY` (⚠️ Keep this secret!)
   - **JWT Secret** → `SUPABASE_JWT_SECRET` (under JWT Settings)

#### Frontend (.env.local in litwise-frontend/)

**Already configured** - verify these exist:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
```

Use the **anon key** (public) for frontend, NOT the service_role key.

### Step 3: Execute RLS Policies in Supabase

1. Go to https://app.supabase.com
2. Select your project
3. Navigate to **SQL Editor**
4. Open the file: `litwise-backend/rls_policies.sql`
5. Copy entire contents
6. Paste into Supabase SQL Editor
7. Click **Run**

**What this does:**
- Enables Row Level Security on all tables
- Creates policies to ensure users can only access their own data
- Adds trigger to auto-create user records on signup
- Enforces data isolation at the database level

### Step 4: Verify Supabase Auth is Enabled

1. Go to **Authentication** → **Settings**
2. Ensure **Email Auth** is enabled
3. (Optional) Configure email templates under **Email Templates**
4. (Optional) Enable other providers (Google, GitHub, etc.)

### Step 5: Restart Backend Server

```bash
cd litwise-backend
python run.py
```

### Step 6: Restart Frontend Server

```bash
cd litwise-frontend
npm run dev
```

---

## 🧪 Testing the Authentication System

### 1. Test User Signup

1. Navigate to `http://localhost:3000/signup`
2. Create a new account with email and password
3. Check Supabase dashboard → **Authentication** → **Users** to verify user creation
4. Check **Table Editor** → **users** table to verify trigger created user record

### 2. Test Login

1. Navigate to `http://localhost:3000/login`
2. Login with the credentials you just created
3. Should redirect to home page with user menu visible

### 3. Test Paper Upload (Authentication Required)

1. Login first
2. Navigate to Upload page
3. Upload a PDF paper
4. Verify paper appears in your papers list
5. Check database: paper should have your `user_id`

### 4. Test Data Isolation

**Create two test accounts:**

**Account A:**
1. Login as User A
2. Upload a paper (Paper A)
3. Note the paper appears in your list

**Account B:**
1. Logout (click user menu → Logout)
2. Signup/Login as User B
3. Upload a different paper (Paper B)
4. **Critical Test**: Verify you ONLY see Paper B, NOT Paper A

**Database Verification:**
```sql
-- In Supabase SQL Editor
SELECT id, title, user_id FROM papers;
-- Should show different user_id for each paper
```

### 5. Test Protected Endpoints (via Browser DevTools)

1. Login and upload a paper
2. Open Browser DevTools → Network tab
3. Navigate to paper detail page
4. Check request headers - should include `Authorization: Bearer <jwt_token>`
5. Logout and try to access paper URL directly - should redirect to login

---

## 🔒 Security Features Implemented

### Frontend Security
- ✅ JWT tokens stored in httpOnly cookies (XSS protection)
- ✅ Automatic token refresh via middleware
- ✅ Protected routes redirect to login
- ✅ User context available via `useAuth()` hook
- ✅ Secure logout clears all session data

### Backend Security
- ✅ JWT validation on all protected endpoints
- ✅ User ID extracted from verified token (not request body)
- ✅ All queries filtered by authenticated user's ID
- ✅ Ownership verification before modifications
- ✅ Consistent error messages (404 for unauthorized access)

### Database Security (RLS)
- ✅ Row Level Security enabled on all tables
- ✅ Policies enforce user can only access own data
- ✅ Automatic user record creation on signup
- ✅ Foreign key constraints maintain data integrity
- ✅ Cascading deletes for related records

---

## 📁 Files Created/Modified

### Backend Files (NEW)
- `litwise-backend/auth_middleware.py` - JWT validation middleware
- `litwise-backend/rls_policies.sql` - Database security policies

### Backend Files (MODIFIED)
- `litwise-backend/app.py` - Added auth to all endpoints
- `litwise-backend/routes/chat.py` - Added auth to chat routes
- `litwise-backend/routes/citations.py` - Added auth to citation routes
- `litwise-backend/routes/literature_review.py` - Added auth to review routes
- `litwise-backend/routes/study_plan.py` - Added auth to study plan routes
- `litwise-backend/requirements.txt` - Added PyJWT dependency

### Frontend Files (Already Complete)
- `litwise-frontend/.env.local` - Environment variables
- `litwise-frontend/middleware.js` - Token refresh
- `litwise-frontend/src/lib/supabase/` - Supabase clients
- `litwise-frontend/src/contexts/AuthContext.jsx` - Auth state management
- `litwise-frontend/src/components/auth/` - Login/Signup/UserMenu components
- `litwise-frontend/src/app/(auth)/` - Auth pages
- `litwise-frontend/src/app/layout.js` - Auth provider wrapper

---

## 🔧 Troubleshooting

### Issue: "Invalid JWT token" errors

**Solution:**
1. Verify `SUPABASE_JWT_SECRET` matches Supabase dashboard
2. Check token expiration (default: 1 hour)
3. Clear browser cookies and re-login

### Issue: Users can't access their own papers

**Solution:**
1. Verify RLS policies were executed successfully:
   ```sql
   SELECT schemaname, tablename, policyname 
   FROM pg_policies 
   WHERE tablename = 'papers';
   ```
2. Check if user_id field is populated:
   ```sql
   SELECT id, title, user_id FROM papers LIMIT 5;
   ```
3. Verify JWT token contains correct user ID (decode at jwt.io)

### Issue: Frontend not sending Authorization header

**Solution:**
1. Check `.env.local` has correct `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`
2. Verify middleware.js is in root of `litwise-frontend/` (not in src/)
3. Clear browser cache and cookies
4. Check browser DevTools → Application → Cookies for auth tokens

### Issue: "Paper not found or access denied" for own papers

**Solution:**
1. Check if paper has user_id set:
   ```sql
   SELECT id, user_id FROM papers WHERE id = 'your-paper-id';
   ```
2. Verify current user ID matches:
   - Get user ID from JWT token (decode at jwt.io)
   - Compare with paper's user_id
3. If user_id is NULL, manually update:
   ```sql
   UPDATE papers SET user_id = 'your-user-id' WHERE id = 'paper-id';
   ```

### Issue: Database errors about missing user_id

**Solution:**
Older papers might not have user_id. Run this migration:
```sql
-- Get your user ID first
SELECT id FROM auth.users WHERE email = 'your-email@example.com';

-- Assign orphaned papers to your account
UPDATE papers 
SET user_id = 'your-user-id-here' 
WHERE user_id IS NULL;
```

---

## 🎯 What's Protected

All these endpoints now require authentication:

### Papers
- ✅ Upload paper (POST /upload)
- ✅ List papers (GET /papers)
- ✅ Get paper details (GET /papers/{id})
- ✅ Delete paper (DELETE /papers/{id})
- ✅ Get multimodal content (GET /papers/{id}/multimodal)
- ✅ Process paper (POST /papers/{id}/process)

### Search & Synthesis
- ✅ Search papers (POST /search) - only user's papers
- ✅ Synthesize results (POST /search/synthesize)
- ✅ Save synthesis (POST /synthesis/save)
- ✅ List synthesis history (GET /synthesis/history)
- ✅ Get synthesis (GET /synthesis/history/{id})
- ✅ Delete synthesis (DELETE /synthesis/history/{id})
- ✅ Update tags (PATCH /synthesis/history/{id}/tags)

### Chat
- ✅ Create chat session (POST /api/chat/sessions)
- ✅ List chat sessions (GET /api/chat/sessions/{paper_id})
- ✅ Get messages (GET /api/chat/sessions/{session_id}/messages)
- ✅ Stream chat (POST /api/chat/stream)
- ✅ Delete session (DELETE /api/chat/sessions/{session_id})

### Citations
- ✅ Generate citation (POST /api/citations/generate)
- ✅ Batch citations (POST /api/citations/batch)
- ✅ Export BibTeX (POST /api/citations/export/bibtex)
- ✅ Extract citations (POST /api/citations/extract)
- ✅ Get paper citations (GET /api/citations/paper/{paper_id})
- ✅ Get stats (GET /api/citations/stats/{paper_id})
- ✅ Delete citations (DELETE /api/citations/paper/{paper_id}/citations)
- ✅ Verify/unverify citation (PATCH /api/citations/{id}/verify)
- ✅ Get verified citations (GET /api/citations/verified/{paper_id})

### Study Plans
- ✅ Generate plan (POST /api/study-plan/generate)
- ✅ List plans (GET /api/study-plan/list)
- ✅ Get plan (GET /api/study-plan/{id})
- ✅ Delete plan (DELETE /api/study-plan/{id})

### Literature Reviews
- ✅ Generate review (POST /api/literature-review/generate)
- ✅ List reviews (GET /api/literature-review/list)
- ✅ Get review (GET /api/literature-review/{id})
- ✅ Delete review (DELETE /api/literature-review/{id})

---

## 🎉 Success Indicators

When everything is working correctly:

1. ✅ Users can signup and login
2. ✅ Papers are tied to users (user_id field populated)
3. ✅ User A cannot see User B's papers
4. ✅ All API requests include Authorization header
5. ✅ Database policies prevent unauthorized access
6. ✅ Logout clears session and redirects to login
7. ✅ Protected routes redirect unauthenticated users

---

## 📝 Next Steps (Optional Enhancements)

### Email Verification
Configure in Supabase → Authentication → Settings:
- Enable "Confirm email" requirement
- Customize email templates

### Password Reset
Already implemented in frontend (`/forgot-password` page):
- User requests reset
- Receives email with reset link
- Sets new password

### Social Login (Google, GitHub, etc.)
Configure in Supabase → Authentication → Providers:
- Enable desired provider
- Add OAuth credentials
- Update frontend login page to show social buttons

### Admin Panel
Use `require_admin()` dependency in new routes:
```python
from auth_middleware import require_admin

@app.get("/admin/users")
async def list_all_users(admin: AuthUser = Depends(require_admin)):
    # Only accessible to admins
    pass
```

Set admin flag in Supabase:
```sql
UPDATE auth.users 
SET raw_user_meta_data = raw_user_meta_data || '{"is_admin": true}'::jsonb 
WHERE email = 'admin@example.com';
```

---

## 🔗 Resources

- **Supabase Docs**: https://supabase.com/docs/guides/auth
- **RLS Guide**: https://supabase.com/docs/guides/database/postgres/row-level-security
- **JWT Debugger**: https://jwt.io
- **FastAPI Security**: https://fastapi.tiangolo.com/tutorial/security/

---

## ✅ Deployment Checklist

Before going to production:

- [ ] All environment variables set correctly
- [ ] RLS policies executed in Supabase
- [ ] PyJWT installed in backend
- [ ] Frontend and backend servers running
- [ ] Test user signup flow
- [ ] Test login flow
- [ ] Test data isolation (multi-user)
- [ ] Test paper upload with auth
- [ ] Test protected endpoints return 401 when not logged in
- [ ] Test logout clears session
- [ ] Configure email templates in Supabase (optional)
- [ ] Enable email confirmation (optional)
- [ ] Set up password reset flow (already implemented)
- [ ] Review error messages don't leak sensitive data
- [ ] Rate limiting configured in Supabase (optional)
- [ ] Backup database before production deployment

---

**Implementation Date**: January 2025  
**Status**: ✅ Complete - Ready for Testing and Deployment
