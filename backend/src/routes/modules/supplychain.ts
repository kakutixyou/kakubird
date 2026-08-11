import { Router, Response } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { getDb } from '../../config/database';
import { authenticate, AuthRequest } from '../../middleware/auth';
import { tenantIsolation } from '../../middleware/tenant';
import { requireRole } from '../../middleware/rbac';

const router = Router();
router.use(authenticate, tenantIsolation);

// ---- Inventory ----
router.get('/inventory', (req: AuthRequest, res: Response) => {
  const db = getDb();
  const { category, search } = req.query;
  let query = 'SELECT * FROM inventory_items WHERE tenant_id = ?';
  const params: any[] = [req.user!.tenantId];
  if (category) { query += ' AND category = ?'; params.push(category); }
  if (search) { query += ' AND (name LIKE ? OR sku LIKE ?)'; params.push(`%${search}%`, `%${search}%`); }
  query += ' ORDER BY name';
  const items = db.prepare(query).all(...params);
  res.json({ items });
});

router.post('/inventory', requireRole('admin', 'manager'), (req: AuthRequest, res: Response) => {
  const { name, sku, category, quantity, unitCost, sellingPrice, reorderLevel, location, supplier } = req.body;
  const db = getDb();
  const id = uuidv4();
  db.prepare(
    'INSERT INTO inventory_items (id, tenant_id, sku, name, category, quantity, unit_cost, selling_price, reorder_level, location, supplier) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
  ).run(id, req.user!.tenantId, sku || `SKU-${Date.now()}`, name, category, quantity || 0, unitCost, sellingPrice, reorderLevel || 0, location, supplier);
  res.status(201).json({ item: db.prepare('SELECT * FROM inventory_items WHERE id = ?').get(id) });
});

router.put('/inventory/:id', requireRole('admin', 'manager'), (req: AuthRequest, res: Response) => {
  const db = getDb();
  const item = db.prepare('SELECT * FROM inventory_items WHERE id = ? AND tenant_id = ?').get(req.params.id, req.user!.tenantId);
  if (!item) return res.status(404).json({ error: 'Item not found' });
  const { name, quantity, unitCost, sellingPrice, reorderLevel } = req.body;
  db.prepare(
    'UPDATE inventory_items SET name=COALESCE(?,name), quantity=COALESCE(?,quantity), unit_cost=COALESCE(?,unit_cost), selling_price=COALESCE(?,selling_price), reorder_level=COALESCE(?,reorder_level), updated_at=CURRENT_TIMESTAMP WHERE id=?'
  ).run(name, quantity, unitCost, sellingPrice, reorderLevel, req.params.id);
  res.json({ item: db.prepare('SELECT * FROM inventory_items WHERE id = ?').get(req.params.id) });
});

router.delete('/inventory/:id', requireRole('admin'), (req: AuthRequest, res: Response) => {
  const db = getDb();
  db.prepare('DELETE FROM inventory_items WHERE id = ? AND tenant_id = ?').run(req.params.id, req.user!.tenantId);
  res.json({ message: 'Item deleted' });
});

// ---- Low stock alerts ----
router.get('/inventory/alerts/low-stock', (req: AuthRequest, res: Response) => {
  const db = getDb();
  const items = db.prepare(
    'SELECT * FROM inventory_items WHERE tenant_id = ? AND quantity <= reorder_level ORDER BY quantity'
  ).all(req.user!.tenantId);
  res.json({ items });
});

// ---- Inventory stats ----
router.get('/inventory/stats', (req: AuthRequest, res: Response) => {
  const db = getDb();
  const tid = req.user!.tenantId;
  const totalItems = (db.prepare('SELECT COUNT(*) as c FROM inventory_items WHERE tenant_id = ?').get(tid) as any).c;
  const totalValue = (db.prepare('SELECT COALESCE(SUM(quantity * unit_cost),0) as v FROM inventory_items WHERE tenant_id = ?').get(tid) as any).v;
  const lowStock = (db.prepare('SELECT COUNT(*) as c FROM inventory_items WHERE tenant_id = ? AND quantity <= reorder_level').get(tid) as any).c;
  const categories = db.prepare('SELECT category, COUNT(*) as count FROM inventory_items WHERE tenant_id = ? GROUP BY category').all(tid);
  res.json({ totalItems, totalValue, lowStock, categories });
});

export default router;
