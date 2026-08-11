import { Router, Request, Response } from 'express';
import { execFile } from 'child_process';
import path from 'path';

const router = Router();

const SEARCHER_PATH = path.join(__dirname, 'searcher.py');

/**
 * POST /api/plugins/github-search/query
 * body: { message: "GitHubで似たようなものを作ろうとしている人がいるか探したい" }
 */
router.post('/query', async (req: Request, res: Response) => {
  const { message } = req.body;

  if (!message || typeof message !== 'string') {
    return res.status(400).json({ error: 'message フィールドが必要です' });
  }

  execFile(
    'python3',
    [SEARCHER_PATH, message],
    { timeout: 15000 },
    (error, stdout, stderr) => {
      if (error) {
        console.error('[github_search] searcher.py error:', stderr);
        return res.status(500).json({ error: 'GitHub検索中にエラーが発生しました', detail: stderr });
      }

      try {
        const result = JSON.parse(stdout);
        return res.json(result);
      } catch (parseError) {
        console.error('[github_search] JSON parse error:', stdout);
        return res.status(500).json({ error: 'レスポンスの解析に失敗しました' });
      }
    }
  );
});

/**
 * GET /api/plugins/github-search/health
 * プラグインの死活確認用
 */
router.get('/health', (_req: Request, res: Response) => {
  res.json({ status: 'ok', plugin: 'github_search' });
});

export default router;