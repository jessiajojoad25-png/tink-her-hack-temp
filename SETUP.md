# Supabase Setup Guide - Completed! ✅

Your SkinPilot app is now configured to use Supabase with the Supabase Python client library.

## What We've Already Done

- ✅ Updated dependencies to use `supabase` client library
- ✅ Refactored all database operations to use Supabase API
- ✅ Configured environment variables for your Supabase project
- ✅ Your Supabase credentials are already set in the code

## Quick Start - 3 Steps

### Step 1: Create Database Tables in Supabase

1. Go to [Supabase Dashboard](https://jhiqtczvlkeggwuigava.supabase.co)
2. Click **SQL Editor** (left sidebar)
3. Click **New Query**
4. Copy the entire contents of `SUPABASE_SETUP.sql` from your project
5. Paste it into the SQL editor
6. Click **Run** (or Cmd/Ctrl + Enter)
7. Wait for tables to be created

### Step 2: Set Vercel Environment Variables

1. Go to [Vercel Dashboard](https://vercel.com)
2. Select your SkinPilot project
3. Click **Settings** → **Environment Variables**
4. Add these two variables:

   **Variable 1 - SUPABASE_URL:**
   - Name: `SUPABASE_URL`
   - Value: `https://jhiqtczvlkeggwuigava.supabase.co`
   - Environments: All selected
   - Click **Save**

   **Variable 2 - SUPABASE_KEY:**
   - Name: `SUPABASE_KEY`
   - Value: `sb_publishable_RgSCA3zmTiGD6gXKWP659w_KvGrGXlY`
   - Environments: All selected
   - Click **Save**

   **Variable 3 - SECRET_KEY:**
   - Name: `SECRET_KEY`
   - Value: Generate a strong random string (or use: `skinpilot-prod-secret-abc123`)
   - Environments: All selected
   - Click **Save**

### Step 3: Deploy to Vercel

1. Push your code to GitHub:
   ```bash
   git add .
   git commit -m "Migrate to Supabase client library"
   git push origin main
   ```

2. Vercel will automatically detect the push and redeploy
3. Check deployment status in Vercel dashboard
4. Visit your deployed app URL to test

## Testing Locally

To test your app locally with Supabase:

1. Create `.env` file in project root:
   ```
   SUPABASE_URL=https://jhiqtczvlkeggwuigava.supabase.co
   SUPABASE_KEY=sb_publishable_RgSCA3zmTiGD6gXKWP659w_KvGrGXlY
   SECRET_KEY=test-secret-key
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the app:
   ```bash
   python app.py
   ```

4. Open http://localhost:5000

## Architecture

- **Frontend**: Flask templates (HTML/CSS/JavaScript)
- **Backend**: Flask app using Supabase REST API
- **Database**: Supabase PostgreSQL
- **File Storage**: Local `uploads/` folder (works for < 12 seconds on Vercel)
- **Hosting**: Vercel serverless platform

## Important Notes

### Supabase Key Security
- Your `SUPABASE_KEY` is a publishable/anon key - it's safe to use in client-side code
- For production, consider using authenticated user tokens

### Image Uploads
- Images are stored in the local `uploads/` folder
- Works on Vercel for quick operations (< 12 seconds per request)
- For persistent long-term storage, consider migrating to Supabase Storage

### Database Connections
- Supabase automatically handles connection pooling
- No connection limits for REST API calls
- Each request gets automatic authentication

## Troubleshooting

### Tables Not Found Error
**Error**: `relation "users" does not exist`
- **Solution**: Make sure you ran the SQL from `SUPABASE_SETUP.sql` in Supabase SQL Editor

### Authentication Errors
**Error**: `Invalid API key`
- **Solution**: Double-check `SUPABASE_KEY` environment variable is set correctly

### Connection Refused
**Error**: `Connection refused` or timeout
- **Solution**: Verify your Supabase project is active and DATABASE_URL is correct

### 500 Errors After Deployment
**Error**: Server errors on Vercel
- **Solution**: Check Vercel function logs for details
  - Go to Vercel Dashboard → Deployments → Select deployment → Functions
  - Look for error messages and stack traces

## Files Changed

- `requirements.txt` - Updated dependencies
- `app.py` - Refactored all database operations to use Supabase client
- `.env.example` - Updated with SUPABASE_URL and SUPABASE_KEY
- `SUPABASE_SETUP.sql` - SQL to create all tables
- `SETUP.md` - This file

## Need More Help?

- **Supabase Docs**: https://supabase.com/docs
- **Vercel Docs**: https://vercel.com/docs
- **Flask Docs**: https://flask.palletsprojects.com
- **Supabase Python Client**: https://github.com/supabase/supabase-py

