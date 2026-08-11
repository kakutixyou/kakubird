import { Router, Request, Response } from 'express';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { v4 as uuidv4 } from 'uuid';
import { body, validationResult } from 'express-validator';
import { getDb } from '../config/database';
import { authenticate, AuthRequest } from '../middleware/auth';

const router = Router();

// POST /api/auth/register
router.post(
  '/register',
  [
    body('email').isEmail(),
    body('password').isLength({ min: 6 }),
    body('name').notEmpty(),
    body('tenantName').notEmpty(),
  ],
  async (req: Request, res: Response) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });

    const { email, password, name, tenantName } = req.body;
    const db = getDb();

    try {
      // Create tenant
      const tenantId = uuidv4();
      const tenantSlug = tenantName.toLowerCase().replace(/\s+/g, '-') + '-' + tenantId.slice(0, 6);
      db.prepare(
        'INSERT INTO tenants (id, name, slug) VALUES (?, ?, ?)'
      ).run(tenantId, tenantName, tenantSlug);

      // Create admin user
      const passwordHash = await bcrypt.hash(password, 10);
      const userId = uuidv4();
      db.prepare(
        'INSERT INTO users (id, tenant_id, email, password_hash, name, role) VALUES (?, ?, ?, ?, ?, ?)'
      ).run(userId, tenantId, email, passwordHash, name, 'admin');

      const token = generateToken({ id: userId, email, role: 'admin', tenantId });
      return res.status(201).json({
        token,
        user: { id: userId, email, name, role: 'admin', tenantId },
        tenant: { id: tenantId, name: tenantName, slug: tenantSlug },
      });
    } catch (err: any) {
      if (err.code === 'SQLITE_CONSTRAINT_UNIQUE') {
        return res.status(409).json({ error: 'Email already in use for this tenant' });
      }
      console.error(err);
      return res.status(500).json({ error: 'Internal server error' });
    }
  }
);

// POST /api/auth/login
router.post(
  '/login',
  [body('email').isEmail(), body('password').notEmpty()],
  async (req: Request, res: Response) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });

    const { email, password } = req.body;
    const db = getDb();

    const user = db.prepare(
      'SELECT u.*, t.name as tenant_name, t.slug as tenant_slug FROM users u JOIN tenants t ON u.tenant_id = t.id WHERE u.email = ? AND u.is_active = 1 LIMIT 1'
    ).get(email) as any;

    if (!user) return res.status(401).json({ error: 'Invalid credentials' });

    const valid = await bcrypt.compare(password, user.password_hash);
    if (!valid) return res.status(401).json({ error: 'Invalid credentials' });

    const token = generateToken({ id: user.id, email: user.email, role: user.role, tenantId: user.tenant_id });
    return res.json({
      token,
      user: { id: user.id, email: user.email, name: user.name, role: user.role, tenantId: user.tenant_id },
      tenant: { id: user.tenant_id, name: user.tenant_name, slug: user.tenant_slug },
    });
  }
);

// GET /api/auth/me
router.get('/me', authenticate, (req: AuthRequest, res: Response) => {
  const db = getDb();
  const user = db.prepare(
    'SELECT u.id, u.email, u.name, u.role, u.tenant_id, t.name as tenant_name FROM users u JOIN tenants t ON u.tenant_id = t.id WHERE u.id = ?'
  ).get(req.user!.id) as any;

  if (!user) return res.status(404).json({ error: 'User not found' });
  return res.json({ user });
});

function generateToken(payload: object): string {
  const secret = process.env.JWT_SECRET;
  if (!secret) {
    throw new Error('JWT_SECRET environment variable is not set');
  }
  return jwt.sign(payload, secret, { expiresIn: '24h' });
}

export default router;
