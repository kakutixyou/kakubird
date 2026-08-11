import { Router, Response } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { getDb } from '../../config/database';
import { authenticate, AuthRequest } from '../../middleware/auth';
import { tenantIsolation } from '../../middleware/tenant';
import { requireRole } from '../../middleware/rbac';

const router = Router();
router.use(authenticate, tenantIsolation);

// ---- CRM Customers ----
router.get('/crm/customers', (req: AuthRequest, res: Response) => {
  const db = getDb();
  const { status, search } = req.query;
  let query = 'SELECT * FROM crm_customers WHERE tenant_id = ?';
  const params: any[] = [req.user!.tenantId];
  if (status) { query += ' AND status = ?'; params.push(status); }
  if (search) { query += ' AND (name LIKE ? OR email LIKE ? OR company LIKE ?)'; params.push(`%${search}%`, `%${search}%`, `%${search}%`); }
  query += ' ORDER BY created_at DESC';
  const customers = db.prepare(query).all(...params);
  res.json({ customers });
});

router.post('/crm/customers', (req: AuthRequest, res: Response) => {
  const { name, email, phone, company, industry, status } = req.body;
  const db = getDb();
  const id = uuidv4();
  db.prepare(
    'INSERT INTO crm_customers (id, tenant_id, name, email, phone, company, industry, status, assigned_to) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
  ).run(id, req.user!.tenantId, name, email, phone, company, industry, status || 'lead', req.user!.id);
  res.status(201).json({ customer: db.prepare('SELECT * FROM crm_customers WHERE id = ?').get(id) });
});

router.put('/crm/customers/:id', (req: AuthRequest, res: Response) => {
  const db = getDb();
  const c = db.prepare('SELECT * FROM crm_customers WHERE id = ? AND tenant_id = ?').get(req.params.id, req.user!.tenantId);
  if (!c) return res.status(404).json({ error: 'Customer not found' });
  const { name, email, phone, company, industry, status, notes } = req.body;
  db.prepare(
    'UPDATE crm_customers SET name=COALESCE(?,name), email=COALESCE(?,email), phone=COALESCE(?,phone), company=COALESCE(?,company), industry=COALESCE(?,industry), status=COALESCE(?,status), notes=COALESCE(?,notes), updated_at=CURRENT_TIMESTAMP WHERE id=?'
  ).run(name, email, phone, company, industry, status, notes, req.params.id);
  res.json({ customer: db.prepare('SELECT * FROM crm_customers WHERE id = ?').get(req.params.id) });
});

router.delete('/crm/customers/:id', requireRole('admin', 'manager'), (req: AuthRequest, res: Response) => {
  const db = getDb();
  db.prepare('DELETE FROM crm_customers WHERE id = ? AND tenant_id = ?').run(req.params.id, req.user!.tenantId);
  res.json({ message: 'Customer deleted' });
});

// ---- CRM Deals ----
router.get('/crm/deals', (req: AuthRequest, res: Response) => {
  const db = getDb();
  const deals = db.prepare(
    'SELECT d.*, c.name as customer_name FROM crm_deals d LEFT JOIN crm_customers c ON d.customer_id = c.id WHERE d.tenant_id = ? ORDER BY d.created_at DESC'
  ).all(req.user!.tenantId);
  res.json({ deals });
});

router.post('/crm/deals', (req: AuthRequest, res: Response) => {
  const { customerId, title, value, stage, probability, closeDate } = req.body;
  const db = getDb();
  const id = uuidv4();
  db.prepare(
    'INSERT INTO crm_deals (id, tenant_id, customer_id, title, value, stage, probability, close_date, assigned_to) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
  ).run(id, req.user!.tenantId, customerId, title, value, stage || 'prospecting', probability || 0, closeDate, req.user!.id);
  res.status(201).json({ deal: db.prepare('SELECT * FROM crm_deals WHERE id = ?').get(id) });
});

router.put('/crm/deals/:id', (req: AuthRequest, res: Response) => {
  const db = getDb();
  const deal = db.prepare('SELECT * FROM crm_deals WHERE id = ? AND tenant_id = ?').get(req.params.id, req.user!.tenantId);
  if (!deal) return res.status(404).json({ error: 'Deal not found' });
  const { title, value, stage, probability, closeDate, notes } = req.body;
  db.prepare(
    'UPDATE crm_deals SET title=COALESCE(?,title), value=COALESCE(?,value), stage=COALESCE(?,stage), probability=COALESCE(?,probability), close_date=COALESCE(?,close_date), notes=COALESCE(?,notes), updated_at=CURRENT_TIMESTAMP WHERE id=?'
  ).run(title, value, stage, probability, closeDate, notes, req.params.id);
  res.json({ deal: db.prepare('SELECT * FROM crm_deals WHERE id = ?').get(req.params.id) });
});

// ---- Pipeline stats ----
router.get('/crm/pipeline', (req: AuthRequest, res: Response) => {
  const db = getDb();
  const pipeline = db.prepare(
    'SELECT stage, COUNT(*) as count, COALESCE(SUM(value),0) as total_value FROM crm_deals WHERE tenant_id = ? GROUP BY stage'
  ).all(req.user!.tenantId);
  res.json({ pipeline });
});

export default router;
