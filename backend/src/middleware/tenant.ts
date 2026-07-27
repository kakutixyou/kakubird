import { Response, NextFunction } from 'express';
import { AuthRequest } from './auth';
import { getDb } from '../config/database';

export function tenantIsolation(req: AuthRequest, res: Response, next: NextFunction) {
  if (!req.user) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  const db = getDb();
  const tenant = db.prepare('SELECT id FROM tenants WHERE id = ?').get(req.user.tenantId);
  if (!tenant) {
    return res.status(403).json({ error: 'Tenant not found' });
  }

  next();
}

export function auditLog(action: string, resource: string) {
  return (req: AuthRequest, res: Response, next: NextFunction) => {
    const originalJson = res.json.bind(res);
    res.json = (body: any) => {
      if (res.statusCode < 400 && req.user) {
        const db = getDb();
        const { v4: uuidv4 } = require('uuid');
        db.prepare(
          'INSERT INTO audit_logs (id, tenant_id, user_id, action, resource, ip_address) VALUES (?, ?, ?, ?, ?, ?)'
        ).run(
          uuidv4(),
          req.user.tenantId,
          req.user.id,
          action,
          resource,
          req.ip || ''
        );
      }
      return originalJson(body);
    };
    next();
  };
}
