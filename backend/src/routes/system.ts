// To-main/backend/src/routes/system.ts
import { Router, Response } from 'express';
import { getDb } from '../config/database';
import { authenticate, AuthRequest } from '../middleware/auth';
import { tenantIsolation } from '../middleware/tenant';

const router = Router();
router.use(authenticate, tenantIsolation);

// GET /api/system/databases
router.get('/databases', (req: AuthRequest, res: Response) => {
  try {
    const db = getDb();
    const tid = req.user!.tenantId;

    // テナントが接続可能なデータベース一覧を返す
    // （例: 外部DB設定、ローカルDB情報など）
    const databases = db.prepare(
      'SELECT id, name, type, host, port, username FROM external_databases WHERE tenant_id = ?'
    ).all(tid);

    res.json({ 
      status: 'ok',
      databases,
      timestamp: new Date()
    });
  } catch (error) {
    console.error('Failed to fetch databases:', error);
    res.status(500).json({ 
      error: 'Failed to fetch databases',
      timestamp: new Date()
    });
  }
});

// GET /api/system/health
router.get('/health', (req: AuthRequest, res: Response) => {
  res.json({ 
    status: 'healthy',
    timestamp: new Date(),
    user: req.user
  });
});

export default router;