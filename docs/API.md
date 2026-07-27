# SIER Platform API Documentation

## Base URL
```
http://localhost:3001/api
```

## Authentication

All protected routes require `Authorization: Bearer <token>` header.

### Register
`POST /auth/register`
```json
{
  "email": "admin@company.com",
  "password": "password123",
  "name": "Jane Smith",
  "tenantName": "Acme Corp"
}
```

### Login
`POST /auth/login`
```json
{ "email": "admin@company.com", "password": "password123" }
```

### Get current user
`GET /auth/me`

---

## Pages (Website Builder)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /pages | List all pages |
| POST | /pages | Create page |
| GET | /pages/:id | Get page with components |
| PUT | /pages/:id | Update page |
| DELETE | /pages/:id | Delete page |
| PUT | /pages/:id/components | Save page components |

---

## Back Office

### HR
- `GET /backoffice/hr/employees` - List employees
- `POST /backoffice/hr/employees` - Create employee
- `PUT /backoffice/hr/employees/:id` - Update employee
- `DELETE /backoffice/hr/employees/:id` - Delete employee
- `GET /backoffice/hr/attendance` - Attendance records
- `POST /backoffice/hr/attendance` - Log attendance

### Finance
- `GET /backoffice/finance/budgets` - List budgets
- `POST /backoffice/finance/budgets` - Create budget
- `GET /backoffice/finance/expenses` - List expenses
- `POST /backoffice/finance/expenses` - Submit expense
- `PATCH /backoffice/finance/expenses/:id/approve` - Approve expense

### Stats
- `GET /backoffice/stats` - HR & Finance summary stats

---

## Front Office (CRM)

- `GET /frontoffice/crm/customers` - List customers (query: status, search)
- `POST /frontoffice/crm/customers` - Create customer
- `PUT /frontoffice/crm/customers/:id` - Update customer
- `DELETE /frontoffice/crm/customers/:id` - Delete customer
- `GET /frontoffice/crm/deals` - List deals
- `POST /frontoffice/crm/deals` - Create deal
- `PUT /frontoffice/crm/deals/:id` - Update deal
- `GET /frontoffice/crm/pipeline` - Pipeline stage summary

---

## Supply Chain (Inventory)

- `GET /supplychain/inventory` - List items (query: category, search)
- `POST /supplychain/inventory` - Create item
- `PUT /supplychain/inventory/:id` - Update item
- `DELETE /supplychain/inventory/:id` - Delete item
- `GET /supplychain/inventory/stats` - Inventory summary
- `GET /supplychain/inventory/alerts/low-stock` - Low stock items

---

## Operations (Tasks)

- `GET /operations/tasks` - List tasks (query: status, priority, assigneeId, module)
- `POST /operations/tasks` - Create task
- `PUT /operations/tasks/:id` - Update task
- `DELETE /operations/tasks/:id` - Delete task
- `GET /operations/tasks/stats` - Task statistics

---

## Governance

- `GET /governance/analytics/overview` - Platform KPI overview
- `GET /governance/users` - List tenant users (admin only)
- `PATCH /governance/users/:id/role` - Change user role (admin only)
- `PATCH /governance/users/:id/toggle` - Enable/disable user (admin only)
- `GET /governance/audit-logs` - Audit trail (admin only)
- `GET /governance/esg/metrics` - ESG metrics

---

## Plugins

- `GET /plugins` - List installed plugins
- `POST /plugins` - Install plugin
- `PATCH /plugins/:id/toggle` - Enable/disable plugin
- `DELETE /plugins/:id` - Remove plugin

---

## WebSocket

Connect to `ws://localhost:3001/ws` for real-time collaboration.
Messages are broadcast to all connected clients (same session).

Message format:
```json
{ "type": "component_update", "pageId": "...", "data": { ... } }
```
