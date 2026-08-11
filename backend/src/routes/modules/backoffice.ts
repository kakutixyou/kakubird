import { Router, Response } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { getDb } from '../../config/database';
import { authenticate, AuthRequest } from '../../middleware/auth';
import { tenantIsolation } from '../../middleware/tenant';
import { requireRole } from '../../middleware/rbac';

const router = Router();
router.use(authenticate, tenantIsolation);

// ---- HR Employees ----
router.get('/hr/employees', (req: AuthRequest, res: Response) => {
  const db = getDb();
  const employees = db.prepare('SELECT * FROM hr_employees WHERE tenant_id = ? ORDER BY name').all(req.user!.tenantId);
  res.json({ employees });
});

router.post('/hr/employees', requireRole('admin', 'manager'), (req: AuthRequest, res: Response) => {
  const { name, email, department, position, hireDate, salary, employeeNumber } = req.body;
  const db = getDb();
  const id = uuidv4();
  db.prepare(
    'INSERT INTO hr_employees (id, tenant_id, employee_number, name, email, department, position, hire_date, salary) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
  ).run(id, req.user!.tenantId, employeeNumber || `EMP-${Date.now()}`, name, email, department, position, hireDate, salary);
  res.status(201).json({ employee: db.prepare('SELECT * FROM hr_employees WHERE id = ?').get(id) });
});

router.put('/hr/employees/:id', requireRole('admin', 'manager'), (req: AuthRequest, res: Response) => {
  const db = getDb();
  const emp = db.prepare('SELECT * FROM hr_employees WHERE id = ? AND tenant_id = ?').get(req.params.id, req.user!.tenantId);
  if (!emp) return res.status(404).json({ error: 'Employee not found' });
  const { name, email, department, position, salary, status } = req.body;
  db.prepare(
    'UPDATE hr_employees SET name=COALESCE(?,name), email=COALESCE(?,email), department=COALESCE(?,department), position=COALESCE(?,position), salary=COALESCE(?,salary), status=COALESCE(?,status), updated_at=CURRENT_TIMESTAMP WHERE id=?'
  ).run(name, email, department, position, salary, status, req.params.id);
  res.json({ employee: db.prepare('SELECT * FROM hr_employees WHERE id = ?').get(req.params.id) });
});

router.delete('/hr/employees/:id', requireRole('admin'), (req: AuthRequest, res: Response) => {
  const db = getDb();
  db.prepare('DELETE FROM hr_employees WHERE id = ? AND tenant_id = ?').run(req.params.id, req.user!.tenantId);
  res.json({ message: 'Employee deleted' });
});

// ---- HR Attendance ----
router.get('/hr/attendance', (req: AuthRequest, res: Response) => {
  const db = getDb();
  const { date, employeeId } = req.query;
  let query = 'SELECT a.*, e.name as employee_name FROM hr_attendance a JOIN hr_employees e ON a.employee_id = e.id WHERE a.tenant_id = ?';
  const params: any[] = [req.user!.tenantId];
  if (date) { query += ' AND a.date = ?'; params.push(date); }
  if (employeeId) { query += ' AND a.employee_id = ?'; params.push(employeeId); }
  query += ' ORDER BY a.date DESC';
  const records = db.prepare(query).all(...params);
  res.json({ records });
});

router.post('/hr/attendance', requireRole('admin', 'manager'), (req: AuthRequest, res: Response) => {
  const { employeeId, date, checkIn, checkOut, status } = req.body;
  const db = getDb();
  const id = uuidv4();
  db.prepare(
    'INSERT INTO hr_attendance (id, tenant_id, employee_id, date, check_in, check_out, status) VALUES (?, ?, ?, ?, ?, ?, ?)'
  ).run(id, req.user!.tenantId, employeeId, date, checkIn, checkOut, status || 'present');
  res.status(201).json({ record: db.prepare('SELECT * FROM hr_attendance WHERE id = ?').get(id) });
});

// ---- Finance Budgets ----
router.get('/finance/budgets', (req: AuthRequest, res: Response) => {
  const db = getDb();
  const budgets = db.prepare('SELECT * FROM finance_budgets WHERE tenant_id = ? ORDER BY created_at DESC').all(req.user!.tenantId);
  res.json({ budgets });
});

router.post('/finance/budgets', requireRole('admin', 'manager'), (req: AuthRequest, res: Response) => {
  const { name, department, amount, period, fiscalYear } = req.body;
  const db = getDb();
  const id = uuidv4();
  db.prepare(
    'INSERT INTO finance_budgets (id, tenant_id, name, department, amount, period, fiscal_year) VALUES (?, ?, ?, ?, ?, ?, ?)'
  ).run(id, req.user!.tenantId, name, department, amount, period, fiscalYear || new Date().getFullYear());
  res.status(201).json({ budget: db.prepare('SELECT * FROM finance_budgets WHERE id = ?').get(id) });
});

// ---- Finance Expenses ----
router.get('/finance/expenses', (req: AuthRequest, res: Response) => {
  const db = getDb();
  const expenses = db.prepare('SELECT * FROM finance_expenses WHERE tenant_id = ? ORDER BY created_at DESC').all(req.user!.tenantId);
  res.json({ expenses });
});

router.post('/finance/expenses', (req: AuthRequest, res: Response) => {
  const { budgetId, category, amount, description, date } = req.body;
  const db = getDb();
  const id = uuidv4();
  db.prepare(
    'INSERT INTO finance_expenses (id, tenant_id, budget_id, employee_id, category, amount, description, date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
  ).run(id, req.user!.tenantId, budgetId, req.user!.id, category, amount, description, date || new Date().toISOString().split('T')[0]);
  res.status(201).json({ expense: db.prepare('SELECT * FROM finance_expenses WHERE id = ?').get(id) });
});

router.patch('/finance/expenses/:id/approve', requireRole('admin', 'manager'), (req: AuthRequest, res: Response) => {
  const db = getDb();
  db.prepare('UPDATE finance_expenses SET status = ?, approved_by = ? WHERE id = ? AND tenant_id = ?')
    .run('approved', req.user!.id, req.params.id, req.user!.tenantId);
  res.json({ expense: db.prepare('SELECT * FROM finance_expenses WHERE id = ?').get(req.params.id) });
});

// ---- Stats ----
router.get('/stats', (req: AuthRequest, res: Response) => {
  const db = getDb();
  const tid = req.user!.tenantId;
  const employeeCount = (db.prepare('SELECT COUNT(*) as c FROM hr_employees WHERE tenant_id = ? AND status = ?').get(tid, 'active') as any).c;
  const totalBudget = (db.prepare('SELECT COALESCE(SUM(amount),0) as s FROM finance_budgets WHERE tenant_id = ?').get(tid) as any).s;
  const pendingExpenses = (db.prepare("SELECT COUNT(*) as c FROM finance_expenses WHERE tenant_id = ? AND status = 'pending'").get(tid) as any).c;
  res.json({ employeeCount, totalBudget, pendingExpenses });
});

export default router;
