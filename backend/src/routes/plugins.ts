// src/routes/plugins.ts
import { Router, Response } from 'express';
import { v4 as uuidv4 } from 'uuid';

import { getDb } from '../config/database';
import { authenticate, AuthRequest } from '../middleware/auth';
import { requireRole } from '../middleware/rbac';
import { tenantIsolation } from '../middleware/tenant';

// ✅ 修正1: PluginManager を src/plugins/ に移動したので、パスは「../plugins/」になります
import { PluginManager } from '../plugins/PluginManager';

const router = Router();

// 1. まず認証・テナント隔離ミドルウェアを適用
router.use(authenticate, tenantIsolation);

// ✅ 修正2: githubSearchPlugin はTS用の実体がまだ無いので、一旦コメントアウトしてエラーを防ぎます。
// （後でTS版のプラグインを作った時にコメントを外せばOKです）
/*
router.use('/github-search', githubSearchPlugin.routes);

if (!PluginManager.isActive('github_search')) {
  PluginManager.register(githubSearchPlugin);
  if (githubSearchPlugin.onInstall) githubSearchPlugin.onInstall();
}
*/

// ================================================================
// 以下、既存のDB連携エンドポイント（そのまま維持）
// ================================================================

// GET /api/plugins
router.get('/', (req: AuthRequest, res: Response) => {
  const db = getDb();
  const plugins = db.prepare('SELECT * FROM plugins WHERE tenant_id = ?').all(req.user!.tenantId);
  res.json({ plugins });
});

// POST /api/plugins - install plugin
router.post('/', requireRole('admin', 'manager'), (req: AuthRequest, res: Response) => {
  const { name, version, config } = req.body;
  const db = getDb();
  const id = uuidv4();
  db.prepare(
    'INSERT INTO plugins (id, tenant_id, name, version, config) VALUES (?, ?, ?, ?, ?)'
  ).run(id, req.user!.tenantId, name, version || '1.0.0', JSON.stringify(config || {}));

  const plugin = db.prepare('SELECT * FROM plugins WHERE id = ?').get(id);
  return res.status(201).json({ plugin });
});

// PATCH /api/plugins/:id/toggle
router.patch('/:id/toggle', requireRole('admin'), (req: AuthRequest, res: Response) => {
  const db = getDb();
  const plugin = db.prepare('SELECT * FROM plugins WHERE id = ? AND tenant_id = ?').get(req.params.id, req.user!.tenantId) as any;
  if (!plugin) return res.status(404).json({ error: 'Plugin not found' });

  db.prepare('UPDATE plugins SET is_active = ? WHERE id = ?').run(plugin.is_active ? 0 : 1, req.params.id);
  const updated = db.prepare('SELECT * FROM plugins WHERE id = ?').get(req.params.id);
  return res.json({ plugin: updated });
});

// DELETE /api/plugins/:id
router.delete('/:id', requireRole('admin'), (req: AuthRequest, res: Response) => {
  const db = getDb();
  const plugin = db.prepare('SELECT * FROM plugins WHERE id = ? AND tenant_id = ?').get(req.params.id, req.user!.tenantId);
  if (!plugin) return res.status(404).json({ error: 'Plugin not found' });

  db.prepare('DELETE FROM plugins WHERE id = ?').run(req.params.id);
  return res.json({ message: 'Plugin removed' });
});

export default router;