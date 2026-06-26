# 💻 Aura Prints & Gifts Shop — Local Development & Testing Guide

This guide explains how to set up and start the **Aura Prints & Gifts Shop** system on your local machine for development, testing, and debugging.

---

## 🛠️ Prerequisites

Before you begin, ensure you have the following installed:
1. **Node.js** (v18 or higher) & **npm**
2. **Python** (v3.10 or higher)
3. **PostgreSQL** (v14 or higher) running locally, OR **Docker** (to run PostgreSQL in a container)

---

## 💾 Step 1: Local Database Setup

The backend connects to a PostgreSQL database named `aura_prints`.

### Option A: Using Docker (Recommended & Fast)
Run a PostgreSQL container with the default credentials used by the development backend:
```bash
docker run --name aura-postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=root -e POSTGRES_DB=aura_prints -p 5432:5432 -d postgres:latest
```

### Option B: Using a Native Local PostgreSQL Installation
1. Start your local PostgreSQL server.
2. Log into the PostgreSQL CLI (`psql`) or a GUI tool (like pgAdmin or DBeaver).
3. Create the database user (if not present) and the database:
   ```sql
   CREATE USER postgres WITH PASSWORD 'root';
   ALTER USER postgres WITH SUPERUSER; -- Required to enable extensions
   CREATE DATABASE aura_prints OWNER postgres;
   ```

### Initialize Database Schema
1. Open a terminal in the root folder.
2. Navigate to the `backend/` folder:
   ```bash
   cd backend
   ```
3. Initialize the Python virtual environment and activate it (see Step 2 below) to ensure required libraries (`asyncpg`) are installed.
4. Run the schema creation script:
   ```bash
   python create_db.py       # Creates the aura_prints database if Option B was used without creating it manually
   python import_schema4.py  # Imports tables and indexes into the database
   ```
   > [!NOTE]
   > `import_schema4.py` is configured specifically for local development. It skips Supabase-specific Row-Level Security (RLS) policies and `auth` schema references, allowing the tables to build cleanly on standard local PostgreSQL.
5. Run the validation script to verify that all schemas and tables were created successfully:
   ```bash
   python list_tables.py
   ```

---

## 🐍 Step 2: Backend Setup (FastAPI)

1. Open a terminal and navigate to the `backend/` folder:
   ```bash
   cd backend
   ```
2. Create a Python virtual environment:
   ```bash
   python -m venv .venv
   ```
3. Activate the virtual environment:
   * **Windows (PowerShell)**:
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   * **Windows (CMD)**:
     ```cmd
     .venv\Scripts\activate.bat
     ```
   * **macOS/Linux**:
     ```bash
     source .venv/bin/activate
     ```
4. Install Python dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
5. Configure local environment variables:
   * Copy the example environment file:
     ```bash
     cp .env.example .env
     ```
   * The default values inside `.env` match the local database defaults (`postgresql+asyncpg://postgres:root@localhost:5432/aura_prints`). You only need to modify them if you configured different database credentials.
6. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --port 8080 --reload
   ```
   > [!TIP]
   > The server will start on `http://127.0.0.1:8080`. The `--reload` flag enables auto-reload, meaning the server will restart automatically whenever you modify backend python files.

---

## 🎨 Step 3: Frontend Setup (Vite + React)

1. Open a new terminal window and navigate to the `frontend/` folder:
   ```bash
   cd frontend
   ```
2. Install Node.js dependencies:
   ```bash
   npm install
   ```
3. Configure the local environment variables:
   * Verify that the `frontend/.env` file contains the API pointer to your local backend:
     ```env
     VITE_API_URL=http://127.0.0.1:8080/api
     ```
4. Start the Vite React development server:
   ```bash
   npm run dev
   ```
5. Open your browser and navigate to the local site:
   `http://localhost:5173`

---

## 🧪 Step 4: Testing & Seed Accounts

During development startup, FastAPI automatically detects if the database tables are empty and populates them with sample products and pre-configured accounts.

You can log in immediately using the following accounts:

| Role | Username / Email | Password | Details |
| :--- | :--- | :--- | :--- |
| **Site Admin** | `admin@auraprints.com` | `aura@2024` | Full access to products, users, orders, and maintenance dashboards. |
| **Employee** | `employee@auraprints.com` | `dave123` | Access to product management and maintenance logs. |
| **Shopkeeper** | `shopkeeper@auraprints.com` | `shopkeeper123` | Access to product views and customer orders fulfillment. |
| **Customer** | `customer@auraprints.com` | `customer123` | Regular store user with points and premium subscription. |
| **Student Customer** | `student@auraprints.com` | `student123` | Student subscription tier customer. |

---

## 📖 API Documentation & Debugging

When the backend server is running, FastAPI automatically serves interactive OpenAPI documentation. You can test API endpoints directly from the browser:

* **Swagger UI Docs**: [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs) (Interactive GUI to execute and test endpoints)
* **ReDoc API Documentation**: [http://127.0.0.1:8080/redoc](http://127.0.0.1:8080/redoc) (Clean, structured API blueprint)
* **Backend Health Check**: [http://127.0.0.1:8080/api/health](http://127.0.0.1:8080/api/health)
