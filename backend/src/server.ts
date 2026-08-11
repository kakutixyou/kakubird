// jimdo_Sutdio_replica_2-main/backend/src/server.ts
import http from 'http';
import { WebSocketServer } from 'ws';
// import app from './app.ts';
import app from './app';
// ↑好成績です。(うまく行けば)app.tsより200の信号が沢山出てきます!
// import { checkOllamaConnection } from './plugins/Algorithm_search_engine/ollama_router.js';
//確かなくてもつながる↑
// サーバーの初期化処理の中で呼び出す
// try {
//   checkOllamaConnection();
// } catch (e) {
//   console.warn("⚠ Ollama接続確認をスキップ:", e);
// }

const PORT = process.env.PORT || 3001;
const server = http.createServer(app);

const wss = new WebSocketServer({ server, path: '/ws' });

const clients = new Set<any>();

wss.on('connection', (ws: any) => {
  clients.add(ws);

  ws.on('message', (data: Buffer) => {
    try {
      const msg = JSON.parse(data.toString());
      // Broadcast to all other clients
      clients.forEach(client => {
        if (client !== ws && client.readyState === 1) {
          client.send(JSON.stringify(msg));
        }
      });
    } catch (err) {
      console.warn('WebSocket: malformed message ignored', err);
    }
  });

  ws.on('close', () => {
    clients.delete(ws);
  });

  ws.send(JSON.stringify({ type: 'connected', message: 'WebSocket connected' }));
});

server.listen(PORT, () => {
  console.log(`🚀 Server running on http://localhost:${PORT}`);
  console.log(`🔌 WebSocket available at ws://localhost:${PORT}/ws`);
});
