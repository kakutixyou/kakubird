import { getDb } from '../config/database';

export function runMigrations() {
  const db = getDb();

  db.exec(`
    CREATE TABLE IF NOT EXISTS tenants (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      slug TEXT UNIQUE NOT NULL,
      plan TEXT DEFAULT 'free',
      settings TEXT DEFAULT '{}',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL,
      email TEXT NOT NULL,
      password_hash TEXT NOT NULL,
      name TEXT NOT NULL,
      role TEXT DEFAULT 'user',
      is_active INTEGER DEFAULT 1,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (tenant_id) REFERENCES tenants(id),
      UNIQUE(tenant_id, email)
    );

    CREATE TABLE IF NOT EXISTS pages (
      id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL,
      title TEXT NOT NULL,
      slug TEXT NOT NULL,
      status TEXT DEFAULT 'draft',
      meta_title TEXT,
      meta_description TEXT,
      created_by TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (tenant_id) REFERENCES tenants(id),
      UNIQUE(tenant_id, slug)
    );

    CREATE TABLE IF NOT EXISTS page_components (
      id TEXT PRIMARY KEY,
      page_id TEXT NOT NULL,
      tenant_id TEXT NOT NULL,
      type TEXT NOT NULL,
      order_index INTEGER DEFAULT 0,
      props TEXT DEFAULT '{}',
      styles TEXT DEFAULT '{}',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS plugins (
      id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL,
      name TEXT NOT NULL,
      version TEXT DEFAULT '1.0.0',
      is_active INTEGER DEFAULT 1,
      config TEXT DEFAULT '{}',
      installed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    );

    CREATE TABLE IF NOT EXISTS hr_employees (
      id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL,
      employee_number TEXT,
      name TEXT NOT NULL,
      email TEXT,
      department TEXT,
      position TEXT,
      hire_date DATE,
      salary REAL,
      status TEXT DEFAULT 'active',
      manager_id TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    );

    CREATE TABLE IF NOT EXISTS hr_attendance (
      id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL,
      employee_id TEXT NOT NULL,
      date DATE NOT NULL,
      check_in TIME,
      check_out TIME,
      status TEXT DEFAULT 'present',
      notes TEXT,
      FOREIGN KEY (tenant_id) REFERENCES tenants(id),
      FOREIGN KEY (employee_id) REFERENCES hr_employees(id)
    );

    CREATE TABLE IF NOT EXISTS finance_budgets (
      id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL,
      name TEXT NOT NULL,
      department TEXT,
      amount REAL NOT NULL,
      spent REAL DEFAULT 0,
      period TEXT,
      fiscal_year INTEGER,
      status TEXT DEFAULT 'active',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    );

    CREATE TABLE IF NOT EXISTS finance_expenses (
      id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL,
      budget_id TEXT,
      employee_id TEXT,
      category TEXT,
      amount REAL NOT NULL,
      description TEXT,
      date DATE,
      status TEXT DEFAULT 'pending',
      approved_by TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    );

    CREATE TABLE IF NOT EXISTS crm_customers (
      id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL,
      name TEXT NOT NULL,
      email TEXT,
      phone TEXT,
      company TEXT,
      industry TEXT,
      status TEXT DEFAULT 'lead',
      assigned_to TEXT,
      notes TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    );

    CREATE TABLE IF NOT EXISTS crm_deals (
      id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL,
      customer_id TEXT,
      title TEXT NOT NULL,
      value REAL,
      stage TEXT DEFAULT 'prospecting',
      probability INTEGER DEFAULT 0,
      close_date DATE,
      assigned_to TEXT,
      notes TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    );

    CREATE TABLE IF NOT EXISTS inventory_items (
      id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL,
      sku TEXT,
      name TEXT NOT NULL,
      category TEXT,
      quantity INTEGER DEFAULT 0,
      unit_cost REAL,
      selling_price REAL,
      reorder_level INTEGER DEFAULT 0,
      location TEXT,
      supplier TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    );

    CREATE TABLE IF NOT EXISTS workflow_tasks (
      id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL,
      title TEXT NOT NULL,
      description TEXT,
      assignee_id TEXT,
      status TEXT DEFAULT 'todo',
      priority TEXT DEFAULT 'medium',
      due_date DATE,
      module TEXT,
      created_by TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    );

    CREATE TABLE IF NOT EXISTS audit_logs (
      id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL,
      user_id TEXT,
      action TEXT NOT NULL,
      resource TEXT,
      resource_id TEXT,
      details TEXT DEFAULT '{}',
      ip_address TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    );
  `);

  console.log('✅ Migrations completed successfully');
}

// Run if called directly
if (require.main === module) {
  runMigrations();
  process.exit(0);
}
