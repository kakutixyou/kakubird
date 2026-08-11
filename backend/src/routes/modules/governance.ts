import { Router, Response } from 'express';
import { getDb } from '../../config/database';
import { authenticate, AuthRequest } from '../../middleware/auth';
import { tenantIsolation } from '../../middleware/tenant';
import { requireRole } from '../../middleware/rbac';

const router = Router();
router.use(authenticate, tenantIsolation);

// ---- Audit Logs ----
router.get('/audit-logs', requireRole('admin'), (req: AuthRequest, res: Response) => {
  const db = getDb();
  const { limit = 50, offset = 0 } = req.query;
  const logs = db.prepare(
    'SELECT a.*, u.name as user_name FROM audit_logs a LEFT JOIN users u ON a.user_id = u.id WHERE a.tenant_id = ? ORDER BY a.created_at DESC LIMIT ? OFFSET ?'
  ).all(req.user!.tenantId, Number(limit), Number(offset));
  const total = (db.prepare('SELECT COUNT(*) as c FROM audit_logs WHERE tenant_id = ?').get(req.user!.tenantId) as any).c;
  res.json({ logs, total });
});

// ---- Security / Users ----
router.get('/users', requireRole('admin'), (req: AuthRequest, res: Response) => {
  const db = getDb();
  const users = db.prepare(
    'SELECT id, email, name, role, is_active, created_at FROM users WHERE tenant_id = ? ORDER BY name'
  ).all(req.user!.tenantId);
  res.json({ users });
});

router.patch('/users/:id/role', requireRole('admin'), (req: AuthRequest, res: Response) => {
  const { role } = req.body;
  if (!['admin', 'manager', 'user'].includes(role)) {
    return res.status(400).json({ error: 'Invalid role' });
  }
  const db = getDb();
  const user = db.prepare('SELECT * FROM users WHERE id = ? AND tenant_id = ?').get(req.params.id, req.user!.tenantId);
  if (!user) return res.status(404).json({ error: 'User not found' });
  db.prepare('UPDATE users SET role = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?').run(role, req.params.id);
  res.json({ user: db.prepare('SELECT id, email, name, role, is_active FROM users WHERE id = ?').get(req.params.id) });
});

router.patch('/users/:id/toggle', requireRole('admin'), (req: AuthRequest, res: Response) => {
  const db = getDb();
  const user = db.prepare('SELECT * FROM users WHERE id = ? AND tenant_id = ?').get(req.params.id, req.user!.tenantId) as any;
  if (!user) return res.status(404).json({ error: 'User not found' });
  db.prepare('UPDATE users SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?').run(user.is_active ? 0 : 1, req.params.id);
  res.json({ user: db.prepare('SELECT id, email, name, role, is_active FROM users WHERE id = ?').get(req.params.id) });
});

// ---- Analytics ----
router.get('/analytics/overview', (req: AuthRequest, res: Response) => {
  const db = getDb();
  const tid = req.user!.tenantId;
  const users = (db.prepare('SELECT COUNT(*) as c FROM users WHERE tenant_id = ?').get(tid) as any).c;
  const pages = (db.prepare('SELECT COUNT(*) as c FROM pages WHERE tenant_id = ?').get(tid) as any).c;
  const customers = (db.prepare('SELECT COUNT(*) as c FROM crm_customers WHERE tenant_id = ?').get(tid) as any).c;
  const deals = (db.prepare('SELECT COUNT(*) as c FROM crm_deals WHERE tenant_id = ?').get(tid) as any).c;
  const dealValue = (db.prepare('SELECT COALESCE(SUM(value),0) as v FROM crm_deals WHERE tenant_id = ?').get(tid) as any).v;
  const employees = (db.prepare("SELECT COUNT(*) as c FROM hr_employees WHERE tenant_id = ? AND status = 'active'").get(tid) as any).c;
  const tasks = (db.prepare("SELECT COUNT(*) as c FROM workflow_tasks WHERE tenant_id = ? AND status != 'done'").get(tid) as any).c;
  res.json({ users, pages, customers, deals, dealValue, employees, tasks });
});

// ---- ESG placeholder ----
router.get('/esg/metrics', (req: AuthRequest, res: Response) => {
  res.json({
    metrics: [
      { category: 'Environmental', score: 72, target: 85 },
      { category: 'Social', score: 68, target: 80 },
      { category: 'Governance', score: 81, target: 90 },
    ],
  });
});

export default router;
