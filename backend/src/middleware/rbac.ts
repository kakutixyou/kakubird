import { Response, NextFunction } from 'express';
import { AuthRequest } from './auth';

const ROLE_HIERARCHY: Record<string, number> = {
  admin: 3,
  manager: 2,
  user: 1,
};

export function requireRole(...roles: string[]) {
  return (req: AuthRequest, res: Response, next: NextFunction) => {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }
    const userLevel = ROLE_HIERARCHY[req.user.role] || 0;
    const hasAccess = roles.some(r => ROLE_HIERARCHY[r] <= userLevel);
    if (!hasAccess) {
      return res.status(403).json({ error: 'Forbidden: insufficient role' });
    }
    next();
  };
}

export function requireAdmin(req: AuthRequest, res: Response, next: NextFunction) {
  if (!req.user || req.user.role !== 'admin') {
    return res.status(403).json({ error: 'Admin access required' });
  }
  next();
}
