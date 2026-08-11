// app.ts
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import rateLimit from 'express-rate-limit';
import dotenv from 'dotenv';
import systemRoutes from './routes/system';
import authRoutes from './routes/auth';
import pagesRoutes from './routes/pages';
import pluginsRoutes from './routes/plugins';
import backofficeRoutes from './routes/modules/backoffice';
import frontofficeRoutes from './routes/modules/frontoffice';
import supplychainRoutes from './routes/modules/supplychain';
import operationsRoutes from './routes/modules/operations';
import governanceRoutes from './routes/modules/governance';
import { runMigrations } from './database/migrations';
// import memoryRoutes from './routes/routes_memory';//←pythonで作っていたりします
import htmlRoutes from './routes/html';
dotenv.config();
runMigrations();

const app = express();

app.use('/api/html', htmlRoutes);
app.use(helmet());
app.use(cors({
  origin: process.env.FRONTEND_URL || 'http://localhost:8000',//元々は5173
  credentials: true,
}));
app.use(morgan('dev'));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

const limiter = rateLimit({ windowMs: 15 * 60 * 1000, max: 500 });
app.use(limiter);

app.use('/api/auth', authRoutes);
app.use('/api/pages', pagesRoutes);
app.use('/api/plugins', pluginsRoutes);
app.use('/api/system', systemRoutes);
app.use('/api/backoffice', backofficeRoutes);
app.use('/api/frontoffice', frontofficeRoutes);
app.use('/api/supplychain', supplychainRoutes);
app.use('/api/operations', operationsRoutes);
app.use('/api/governance', governanceRoutes);
// app.use('/api/memory', require('./routes/routes_memory').default); 
// app.use('/api/memory', memoryRoutes);
app.get('/api/health', (_, res) => res.json({ status: 'ok', timestamp: new Date() }));

app.use((err: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Internal server error' });
});

export default app;
