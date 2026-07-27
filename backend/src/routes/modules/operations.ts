import { Router, Response } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { getDb } from '../../config/database';
import { authenticate, AuthRequest } from '../../middleware/auth';
import { tenantIsolation } from '../../middleware/tenant';
import { requireRole } from '../../middleware/rbac';

const router = Router();
router.use(authenticate, tenantIsolation);

// ---- Workflow Tasks ----
router.get('/tasks', (req: AuthRequest, res: Response) => {
  const db = getDb();
  const { status, priority, assigneeId, module } = req.query;
  let query = 'SELECT t.*, u.name as assignee_name FROM workflow_tasks t LEFT JOIN users u ON t.assignee_id = u.id WHERE t.tenant_id = ?';
  const params: any[] = [req.user!.tenantId];
  if (status) { query += ' AND t.status = ?'; params.push(status); }
  if (priority) { query += ' AND t.priority = ?'; params.push(priority); }
  if (assigneeId) { query += ' AND t.assignee_id = ?'; params.push(assigneeId); }
  if (module) { query += ' AND t.module = ?'; params.push(module); }
  query += ' ORDER BY t.created_at DESC';
  const tasks = db.prepare(query).all(...params);
  res.json({ tasks });
});

router.post('/tasks', (req: AuthRequest, res: Response) => {
  const { title, description, assigneeId, priority, dueDate, module } = req.body;
  const db = getDb();
  const id = uuidv4();
  db.prepare(
    'INSERT INTO workflow_tasks (id, tenant_id, title, description, assignee_id, priority, due_date, module, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
  ).run(id, req.user!.tenantId, title, description, assigneeId, priority || 'medium', dueDate, module, req.user!.id);
  res.status(201).json({ task: db.prepare('SELECT * FROM workflow_tasks WHERE id = ?').get(id) });
});

router.put('/tasks/:id', (req: AuthRequest, res: Response) => {
  const db = getDb();
  const task = db.prepare('SELECT * FROM workflow_tasks WHERE id = ? AND tenant_id = ?').get(req.params.id, req.user!.tenantId);
  if (!task) return res.status(404).json({ error: 'Task not found' });
  const { title, description, status, priority, assigneeId, dueDate } = req.body;
  db.prepare(
    'UPDATE workflow_tasks SET title=COALESCE(?,title), description=COALESCE(?,description), status=COALESCE(?,status), priority=COALESCE(?,priority), assignee_id=COALESCE(?,assignee_id), due_date=COALESCE(?,due_date), updated_at=CURRENT_TIMESTAMP WHERE id=?'
  ).run(title, description, status, priority, assigneeId, dueDate, req.params.id);
  res.json({ task: db.prepare('SELECT * FROM workflow_tasks WHERE id = ?').get(req.params.id) });
});

router.delete('/tasks/:id', requireRole('admin', 'manager'), (req: AuthRequest, res: Response) => {
  const db = getDb();
  db.prepare('DELETE FROM workflow_tasks WHERE id = ? AND tenant_id = ?').run(req.params.id, req.user!.tenantId);
  res.json({ message: 'Task deleted' });
});

// ---- Task stats ----
router.get('/tasks/stats', (req: AuthRequest, res: Response) => {
  const db = getDb();
  const tid = req.user!.tenantId;
  const byStatus = db.prepare('SELECT status, COUNT(*) as count FROM workflow_tasks WHERE tenant_id = ? GROUP BY status').all(tid);
  const byPriority = db.prepare('SELECT priority, COUNT(*) as count FROM workflow_tasks WHERE tenant_id = ? GROUP BY priority').all(tid);
  const overdue = (db.prepare("SELECT COUNT(*) as c FROM workflow_tasks WHERE tenant_id = ? AND due_date < date('now') AND status != 'done'").get(tid) as any).c;
  res.json({ byStatus, byPriority, overdue });
});

export default router;
