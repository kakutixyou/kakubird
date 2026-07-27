import { Router, Response } from 'express';
import axios, { AxiosError } from 'axios';
import { authenticate, AuthRequest } from '../middleware/auth';
import { tenantIsolation } from '../middleware/tenant';

const router = Router();
router.use(authenticate, tenantIsolation);

const HTML_ENGINE_URL = process.env.HTML_ENGINE_URL || 'http://localhost:8001';

// HTML生成
router.post('/generate', async (req: AuthRequest, res: Response) => {
  try {
    const response = await axios.post(`${HTML_ENGINE_URL}/api/html/generate`, req.body);
    res.json(response.data);
  } catch (error: any) {
    res.status(error.response?.status || 500).json({ error: error.message });
  }
});

// HTMLエクスポート
router.post('/export', async (req: AuthRequest, res: Response) => {
  try {
    const { format = 'html' } = req.query;
    const response = await axios.post(`${HTML_ENGINE_URL}/api/html/export`, 
      { ...req.body, format }
    );
    res.json(response.data);
  } catch (error: any) {
    res.status(error.response?.status || 500).json({ error: error.message });
  }
});

// コンポーネントルール取得
router.get('/rules', async (req: AuthRequest, res: Response) => {
  try {
    const response = await axios.get(`${HTML_ENGINE_URL}/api/html/rules`);
    res.json(response.data);
  } catch (error: any) {
    res.status(error.response?.status || 500).json({ error: error.message });
  }
});

export default router;