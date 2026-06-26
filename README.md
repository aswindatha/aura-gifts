# 🌟 Aura Prints & Gifts Shop — Production Deployment Guide

This guide provides a comprehensive production deployment plan for the **Aura Prints & Gifts Shop** system. It details how to host the backend, frontend, and database completely within **Free Tier** limits while comfortably handling **10,000 API calls/day**, **200+ new logins/month**, and **1,000+ products**.

---

## 🏗️ Production Architecture Overview

The system is deployed using a highly optimized serverless architecture to ensure zero hosting costs:

```
                  ┌──────────────────────┐
                  │   Vercel Frontend    │ (Static Web App)
                  │ (Vite + React Host)  │
                  └──────────┬───────────┘
                             │ (HTTPS / CORS API calls)
                             ▼
                  ┌──────────────────────┐
                  │ Google Cloud Run API │ (FastAPI Container)
                  │  (Scales to 0 Idle)  │
                  └──────────┬───────────┘
                             │ (PostgreSQL Pooler URI: 6543)
                             ▼
                  ┌──────────────────────┐
                  │  Supabase Database   │ (PostgreSQL RLS Enabled)
                  │     (500MB Limit)    │
                  └──────────────────────┘
                             ▲
                             │ (Daily Ping to prevent DB pausing)
                  ┌──────────┴───────────┐
                  │ External Cron Pinger │ (e.g., UptimeRobot / Cron-Job.org)
                  └──────────────────────┘
```

---

## 💾 Phase 1: Database Setup (Supabase)

Supabase offers a free PostgreSQL database tier which provides a dedicated database with full Row-Level Security (RLS) support.

### 1. Create a Supabase Project
1. Go to [supabase.com](https://supabase.com) and sign up for a free account.
2. Click **New Project** and select your region.
3. Choose a strong database password and copy it down.
4. Wait for the database provisioning to complete (takes 1-2 minutes).

### 2. Apply Schema & Seed Data
1. Navigate to the **SQL Editor** from the left navigation menu in your Supabase project.
2. Click **New Query**.
3. Open [backend/schema.sql](file:///c:/Users/aswin/Music/SAD_CORPORATIONS/aura-prints/backend/schema.sql) in your workspace, copy its contents, paste them into the SQL Editor, and click **Run**.
   > [!NOTE]
   > The schema creates two schemas (`ecommerce` and `maintenance`), enables RLS, and sets up RLS policies using `auth.uid() = id`.
4. Open a second **New Query** tab.
5. Open [backend/data.sql](file:///c:/Users/aswin/Music/SAD_CORPORATIONS/aura-prints/backend/data.sql) in your workspace, copy the contents, paste them into the SQL Editor, and click **Run**. This will populate the default user roles (admin, employee, shopkeeper, customer), sample products, and default maintenance entries.

### 3. Retrieve Connection URL
1. Go to **Project Settings** (gear icon) -> **Database**.
2. Scroll to **Connection String** and click the **URI** tab.
3. Copy the URL. It will look like this:
   `postgresql://postgres.[YOUR_PROJECT_ID]:[YOUR_PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres`
   > [!IMPORTANT]
   > For the FastAPI backend, you **MUST**:
   > 1. Use the **Connection Pooler URL** (port `6543` with Transaction mode) instead of direct connection (port `5432`). This is critical because serverless instances can scale quickly and exhaust direct PostgreSQL connections.
   > 2. Change the scheme prefix from `postgresql://` to `postgresql+asyncpg://` to match SQLAlchemy's async driver requirement.

---

## ⚡ Phase 2: Backend Deployment (Google Cloud Run)

FastAPI is packaged inside a lightweight Docker container and deployed to Google Cloud Run, which scales down to zero when there is no traffic, preventing any idle compute charges.

### 1. Prerequisites & GCP Setup
1. Create a Google Cloud Platform account (Free tier includes $300 credits + perpetual free tier limits).
2. Install the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) on your local machine.
3. Authenticate the CLI:
   ```bash
   gcloud auth login
   gcloud auth configure-docker
   ```
4. Create a new GCP project or select an existing one:
   ```bash
   gcloud config set project [YOUR_GCP_PROJECT_ID]
   ```
5. Enable the required APIs:
   ```bash
   gcloud services enable run.googleapis.com artifactregistry.googleapis.com
   ```

### 2. Build and Push Container Image
1. Create an Artifact Registry Repository:
   ```bash
   gcloud artifacts repositories create aura-prints-repo \
       --repository-format=docker \
       --location=us-central1 \
       --description="Docker repository for Aura Prints Backend"
   ```
2. Navigate to the backend directory and build the Docker image locally (substituting your project ID):
   ```bash
   cd backend
   docker build -t us-central1-docker.pkg.dev/[YOUR_GCP_PROJECT_ID]/aura-prints-repo/backend:latest .
   ```
3. Push the image to Artifact Registry:
   ```bash
   docker push us-central1-docker.pkg.dev/[YOUR_GCP_PROJECT_ID]/aura-prints-repo/backend:latest
   ```

### 3. Deploy to Google Cloud Run
Deploy the container with environment variables and **Free-Tier optimizations**:
```bash
gcloud run deploy aura-prints-backend \
    --image=us-central1-docker.pkg.dev/[YOUR_GCP_PROJECT_ID]/aura-prints-repo/backend:latest \
    --platform=managed \
    --region=us-central1 \
    --allow-unauthenticated \
    --set-env-vars="DATABASE_URL=postgresql+asyncpg://postgres.[PROJECT]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres,JWT_SECRET_KEY=[SECURE_RANDOM_KEY]" \
    --memory=512Mi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=5 \
    --concurrency=80 \
    --no-cpu-throttling-during-initialization
```

> [!TIP]
> **Free Tier Tunings Applied Above:**
> * `--min-instances=0`: Ensures the container scales down to 0 instances when idle, resulting in **$0 cost**.
> * `--max-instances=5`: Sets a hard ceiling to prevent run-away scaling charges if subjected to a DDOS or traffic spike.
> * `--memory=512Mi` & `--cpu=1`: Optimizes resource usage to stay well within the GCP free tier allowance (180,000 vCPU-seconds and 360,000 GiB-seconds per month).
> * `--concurrency=80`: Allows a single container instance to process up to 80 requests simultaneously using FastAPI async processing, saving memory.

---

## 🎨 Phase 3: Frontend Deployment (Vercel)

Vercel provides static file hosting with global CDN delivery, which is 100% free for static sites.

### 1. Configure the Frontend Build
1. Push your code to a Git Repository (GitHub, GitLab, or Bitbucket).
2. Log into [vercel.com](https://vercel.com) and click **Add New** -> **Project**.
3. Import your Git repository.
4. In the configuration settings:
   * **Framework Preset**: Select `Vite` (Vercel will auto-detect).
   * **Root Directory**: Set this to `frontend`.
   * **Build Command**: `npm run build`
   * **Output Directory**: `dist`
5. Expand **Environment Variables** and add:
   * **Key**: `VITE_API_URL`
   * **Value**: `[YOUR_CLOUD_RUN_API_URL]/api` (e.g., `https://aura-prints-backend-xxxxxx-uc.a.run.app/api`)
6. Click **Deploy**.

---

## 🔗 Phase 4: Connecting the Systems & Keep-Alive Triggers

Now that all parts are deployed, configure the safety mechanisms to bypass Free-Tier restrictions.

### 1. Setup Database Keep-Alive Trigger (Supabase Pause Bypass)
Supabase free tier databases pause after **7 days of inactivity**. To prevent this:
1. Since Cloud Run scales to `0` when idle, the internal python `keep_alive_loop` in the backend will go to sleep.
2. Go to a free uptime checking tool such as [UptimeRobot](https://uptimerobot.com) or [cron-job.org](https://cron-job.org).
3. Create a HTTP monitor:
   * **URL**: `[YOUR_CLOUD_RUN_API_URL]/api/health`
   * **Interval**: Every **24 hours** (or 12 hours).
4. When this cron ping hits the endpoint:
   * Cloud Run wakes up from zero instances.
   * The FastAPI `startup` event fires.
   * FastAPI runs the health check ping (`SELECT NOW();`) against the Supabase database.
   * This double-wakes both services, keeping the database alive indefinitely at **$0 cost**.

### 2. Setup Gzip Compression for Bandwidth Conservation
GCP Cloud Run provides free egress up to **1 GB per month**. To ensure 10,000 API calls/day fit into 1 GB, enable Gzip compression on backend JSON data. If not already included, ensure `GzipMiddleware` is added in FastAPI:
```python
from fastapi.middleware.gzip import GzipMiddleware
app.add_middleware(GzipMiddleware, minimum_size=1000)
```

---

## 📊 Traffic & Capacity Audit (Free Tier Feasibility)

| Resource | Free Tier Limit | Aura Prints Projected Consumption | Status | Mitigations |
| :--- | :--- | :--- | :--- | :--- |
| **Cloud Run Requests** | 2 Million requests / mo | ~300,000 requests / mo (10k/day) | **100% Free** | Under 15% of limit. |
| **Cloud Run Compute** | 180k vCPU-s / 360k GiB-s | ~60,000 vCPU-s / ~30,000 GiB-s | **100% Free** | Scale to 0 configuration prevents resource leakage. |
| **Cloud Run Egress** | 1.0 GB / month | ~600 MB / month | **100% Free** | Gzip middleware compresses JSON payloads to keep under 1 GB. |
| **Supabase DB Size** | 500 MB | ~1.5 MB for 1000 products & users | **100% Free** | No binary file/image storage inside DB (URLs only). |
| **Supabase Bandwidth** | 5 GB / month | ~2.5 GB / month | **100% Free** | Large files are cached or direct-downloaded. |
| **Vercel Bandwidth** | 100 GB / month | ~8.0 GB / month (1,000 daily sessions) | **100% Free** | Rely on browser static caching for CSS/JS. |

---

## 🛡️ Production Verification Checklist
- [ ] Connect to backend `/api/health` in browser and confirm `{"status":"healthy","database":"connected"}`.
- [ ] Sign up a new user via the React Frontend, confirming a user record is generated in Supabase `ecommerce.users`.
- [ ] Validate CORS configurations by checking if API requests fail with Preflight/CORS errors. (If they do, confirm `allow_origins` includes the Vercel domain).
