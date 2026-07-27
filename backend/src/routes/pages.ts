import { Router, Response } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { body, validationResult } from 'express-validator';
import { getDb } from '../config/database';
import { authenticate, AuthRequest } from '../middleware/auth';
import { tenantIsolation } from '../middleware/tenant';

const router = Router();
router.use(authenticate, tenantIsolation);

// GET /api/pages
router.get('/', (req: AuthRequest, res: Response) => {
  const db = getDb();
  const pages = db.prepare('SELECT * FROM pages WHERE tenant_id = ? ORDER BY created_at DESC').all(req.user!.tenantId);
  res.json({ pages });
});

// GET /api/pages/:id
router.get('/:id', (req: AuthRequest, res: Response) => {
  const db = getDb();
  const page = db.prepare('SELECT * FROM pages WHERE id = ? AND tenant_id = ?').get(req.params.id, req.user!.tenantId) as any;
  if (!page) return res.status(404).json({ error: 'Page not found' });

  const components = db.prepare(
    'SELECT * FROM page_components WHERE page_id = ? ORDER BY order_index ASC'
  ).all(page.id);

  res.json({ page, components });
});

// POST /api/pages
router.post('/', [body('title').notEmpty()], (req: AuthRequest, res: Response) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });

  const { title, slug, metaTitle, metaDescription } = req.body;
  const db = getDb();
  const id = uuidv4();
  const pageSlug = slug || title.toLowerCase().replace(/\s+/g, '-') + '-' + id.slice(0, 6);

  try {
    db.prepare(
      'INSERT INTO pages (id, tenant_id, title, slug, meta_title, meta_description, created_by) VALUES (?, ?, ?, ?, ?, ?, ?)'
    ).run(id, req.user!.tenantId, title, pageSlug, metaTitle || title, metaDescription || '', req.user!.id);

    const page = db.prepare('SELECT * FROM pages WHERE id = ?').get(id);
    return res.status(201).json({ page });
  } catch (err: any) {
    if (err.code === 'SQLITE_CONSTRAINT_UNIQUE') {
      return res.status(409).json({ error: 'Slug already exists' });
    }
    return res.status(500).json({ error: 'Internal server error' });
  }
});

// PUT /api/pages/:id
router.put('/:id', (req: AuthRequest, res: Response) => {
  const db = getDb();
  const page = db.prepare('SELECT * FROM pages WHERE id = ? AND tenant_id = ?').get(req.params.id, req.user!.tenantId);
  if (!page) return res.status(404).json({ error: 'Page not found' });

  const { title, slug, status, metaTitle, metaDescription } = req.body;
  db.prepare(
    'UPDATE pages SET title = COALESCE(?, title), slug = COALESCE(?, slug), status = COALESCE(?, status), meta_title = COALESCE(?, meta_title), meta_description = COALESCE(?, meta_description), updated_at = CURRENT_TIMESTAMP WHERE id = ?'
  ).run(title, slug, status, metaTitle, metaDescription, req.params.id);

  const updated = db.prepare('SELECT * FROM pages WHERE id = ?').get(req.params.id);
  return res.json({ page: updated });
});

// DELETE /api/pages/:id
router.delete('/:id', (req: AuthRequest, res: Response) => {
  const db = getDb();
  const page = db.prepare('SELECT * FROM pages WHERE id = ? AND tenant_id = ?').get(req.params.id, req.user!.tenantId);
  if (!page) return res.status(404).json({ error: 'Page not found' });

  db.prepare('DELETE FROM pages WHERE id = ?').run(req.params.id);
  return res.json({ message: 'Page deleted' });
});

// PUT /api/pages/:id/components - save all components
router.put('/:id/components', (req: AuthRequest, res: Response) => {
  const db = getDb();
  const page = db.prepare('SELECT * FROM pages WHERE id = ? AND tenant_id = ?').get(req.params.id, req.user!.tenantId);
  if (!page) return res.status(404).json({ error: 'Page not found' });

  const { components } = req.body;
  if (!Array.isArray(components)) return res.status(400).json({ error: 'components must be array' });

  const deleteStmt = db.prepare('DELETE FROM page_components WHERE page_id = ?');
  const insertStmt = db.prepare(
    'INSERT INTO page_components (id, page_id, tenant_id, type, order_index, props, styles) VALUES (?, ?, ?, ?, ?, ?, ?)'
  );

  const saveAll = db.transaction(() => {
    deleteStmt.run(req.params.id);
    components.forEach((c: any, idx: number) => {
      insertStmt.run(
        c.id || uuidv4(),
        req.params.id,
        req.user!.tenantId,
        c.type,
        idx,
        JSON.stringify(c.props || {}),
        JSON.stringify(c.styles || {})
      );
    });
  });

  saveAll();
  const saved = db.prepare('SELECT * FROM page_components WHERE page_id = ? ORDER BY order_index').all(req.params.id);
  return res.json({ components: saved });
});

export default router;
