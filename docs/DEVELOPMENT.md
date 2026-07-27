# Development Guide

## Prerequisites
- Node.js 18+
- npm 9+

## Quick Start

### 1. Clone and install
```bash
# Install backend dependencies
cd backend && npm install

# Install frontend dependencies
cd ../frontend && npm install
```

### 2. Configure backend
```bash
cp backend/.env.example backend/.env
# Edit JWT_SECRET for production!
```

### 3. Run development servers

**Backend** (port 3001):
```bash
cd backend && npm run dev
```

**Frontend** (port 5173):
```bash
cd frontend && npm run dev
```

### 4. Open the app
Navigate to [http://localhost:5173](http://localhost:5173)

Register a new account (creates a tenant automatically).

---

## Project Structure

### Backend (`/backend/src/`)
- `server.ts` — Entry point, HTTP + WebSocket server
- `app.ts` — Express app setup, routes, middleware
- `config/database.ts` — SQLite connection (better-sqlite3)
- `database/migrations.ts` — Schema definitions
- `middleware/` — JWT auth, RBAC, tenant isolation
- `routes/` — REST API endpoints
- `plugins/PluginManager.ts` — Plugin system

### Frontend (`/frontend/src/`)
- `App.tsx` — Router and layout
- `api/client.ts` — Axios client with auth interceptors
- `store/authStore.ts` — Zustand auth state (persisted)
- `store/builderStore.ts` — Drag-and-drop builder state
- `components/Builder/` — DragDrop, Canvas, Palette, Properties
- `components/Layout/` — Navbar, Sidebar, Layout wrapper
- `pages/` — Dashboard, Builder, Login, and all module pages

---

## Architecture Decisions

### Multi-tenancy
Every database table has a `tenant_id` column. All queries filter by the authenticated user's tenant. Tenants are completely isolated.

### RBAC
- **admin** — Full access, user management, audit logs
- **manager** — Read/write, can approve expenses, modify inventory
- **user** — Read + create own records

### Drag-and-Drop Builder
Uses `@hello-pangea/dnd`. Components are stored as JSON in `page_components` table with `type`, `props`, and `styles` columns.

### WebSocket
Single `/ws` endpoint broadcasts messages to all connected clients in the same server instance. Useful for real-time collaboration on page editing.

---

## Database

SQLite database is stored at `backend/data/platform.db` (created automatically on first run).

Tables: `tenants`, `users`, `pages`, `page_components`, `plugins`, `hr_employees`, `hr_attendance`, `finance_budgets`, `finance_expenses`, `crm_customers`, `crm_deals`, `inventory_items`, `workflow_tasks`, `audit_logs`

---

## Building for Production

```bash
# Build backend
cd backend && npm run build

# Build frontend
cd frontend && npm run build
```

Frontend outputs to `frontend/dist/`, serve with any static file server.
Backend outputs to `backend/dist/`, run with `node dist/server.js`.

### Using Docker
```bash
docker-compose up --build
```
