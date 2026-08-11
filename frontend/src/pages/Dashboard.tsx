import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import { governanceApi, backofficeApi, frontofficeApi } from '../api/client';
import { useAuthStore } from '../store/authStore';
import React from 'react';
// import AiChatPanel from '../components/AiChatPanel';
const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

export default function Dashboard() {
  const { user, tenant } = useAuthStore();
  const [overview, setOverview] = useState<any>(null);
  const [backStats, setBackStats] = useState<any>(null);
  const [pipeline, setPipeline] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [dbPath, setDbPath]       = useState(""); 
  useEffect(() => {
    Promise.all([
      governanceApi.getAnalyticsOverview().catch(() => ({ data: null })),
      backofficeApi.getStats().catch(() => ({ data: null })),
      frontofficeApi.getPipeline().catch(() => ({ data: { pipeline: [] } })),
    ]).then(([ov, bs, pp]) => {
      setOverview(ov.data);
      setBackStats(bs.data);
      setPipeline(pp.data.pipeline || []);
    }).finally(() => setLoading(false));
  }, []);

  const stats = [
    { label: 'Employees', value: backStats?.employeeCount ?? '—', icon: '👥', color: 'bg-blue-50 text-blue-700' },
    { label: 'Customers', value: overview?.customers ?? '—', icon: '🤝', color: 'bg-green-50 text-green-700' },
    { label: 'Open Deals', value: overview?.deals ?? '—', icon: '💼', color: 'bg-amber-50 text-amber-700' },
    { label: 'Pages', value: overview?.pages ?? '—', icon: '📄', color: 'bg-purple-50 text-purple-700' },
    { label: 'Open Tasks', value: overview?.tasks ?? '—', icon: '✅', color: 'bg-red-50 text-red-700' },
    { label: 'Budget Total', value: overview?.totalBudget ? `$${Number(overview.totalBudget).toLocaleString()}` : '—', icon: '💰', color: 'bg-teal-50 text-teal-700' },
  ];

  const pipelineChartData = pipeline.map(p => ({ name: p.stage, count: p.count, value: p.total_value }));

  const modules = [
    { name: 'Page Builder', desc: 'Create and manage web pages', icon: '🏗', path: '/builder', color: 'border-blue-200' },
    { name: 'Back Office', desc: 'HR, Finance, Assets', icon: '🏢', path: '/backoffice', color: 'border-green-200' },
    { name: 'Front Office', desc: 'CRM, Sales Pipeline', icon: '🤝', path: '/frontoffice', color: 'border-amber-200' },
    { name: 'Supply Chain', desc: 'Inventory Management', icon: '📦', path: '/supplychain', color: 'border-orange-200' },
    { name: 'Operations', desc: 'Tasks & Workflows', icon: '⚙️', path: '/operations', color: 'border-purple-200' },
    { name: 'Governance', desc: 'Security, Analytics, ESG', icon: '🛡', path: '/governance', color: 'border-red-200' },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome back, {user?.name} 👋
        </h1>
        <p className="text-gray-500">{tenant?.name} • {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {stats.map((stat) => (
          <div key={stat.label} className={`rounded-xl p-4 ${stat.color}`}>
            <div className="text-2xl mb-1">{stat.icon}</div>
            <div className="text-2xl font-bold">{stat.value}</div>
            <div className="text-xs opacity-70 mt-1">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-700 mb-4">Sales Pipeline</h3>
          {pipelineChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={pipelineChartData}>
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#3b82f6" name="Deals" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-400 text-sm">
              No pipeline data yet
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-700 mb-4">Module Overview</h3>
          <div className="grid grid-cols-2 gap-3">
            {modules.map(m => (
              <Link
                key={m.path}
                to={m.path}
                className={`border ${m.color} rounded-lg p-3 hover:bg-gray-50 transition-colors`}
              >
                <div className="text-2xl mb-1">{m.icon}</div>
                <div className="font-medium text-sm text-gray-800">{m.name}</div>
                <div className="text-xs text-gray-500">{m.desc}</div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
