import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { governanceApi } from '../../api/client';
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';
import React from 'react';

export default function GovernancePage() {
  const [tab, setTab] = useState<'analytics' | 'security' | 'audit' | 'esg'>('analytics');
  const [overview, setOverview] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [esg, setEsg] = useState<any[]>([]);

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const [ovRes, uRes, aRes, eRes] = await Promise.all([
        governanceApi.getAnalyticsOverview(),
        governanceApi.getUsers(),
        governanceApi.getAuditLogs(),
        governanceApi.getEsgMetrics(),
      ]);
      setOverview(ovRes.data);
      setUsers(uRes.data.users);
      setAuditLogs(aRes.data.logs);
      setEsg(eRes.data.metrics);
    } catch (err) { console.error(err); }
  }

  async function changeRole(userId: string, role: string) {
    try {
      await governanceApi.updateUserRole(userId, role);
      toast.success('Role updated');
      setUsers(users.map(u => u.id === userId ? { ...u, role } : u));
    } catch { toast.error('Failed'); }
  }

  async function toggleUser(userId: string) {
    try {
      await governanceApi.toggleUser(userId);
      setUsers(users.map(u => u.id === userId ? { ...u, is_active: u.is_active ? 0 : 1 } : u));
      toast.success('Updated');
    } catch { toast.error('Failed'); }
  }

  const overviewData = overview ? [
    { name: 'Users', value: overview.users },
    { name: 'Pages', value: overview.pages },
    { name: 'Customers', value: overview.customers },
    { name: 'Deals', value: overview.deals },
    { name: 'Employees', value: overview.employees },
    { name: 'Open Tasks', value: overview.tasks },
  ] : [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Governance</h1>
        <div className="flex gap-2">
          {([['analytics', '📊 Analytics'], ['security', '🔑 Security'], ['audit', '📋 Audit Log'], ['esg', '🌱 ESG']] as const).map(([t, l]) => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-3 py-1.5 rounded text-xs font-medium ${tab === t ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'}`}>
              {l}
            </button>
          ))}
        </div>
      </div>

      {tab === 'analytics' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-700 mb-4">Platform Overview</h3>
            <div className="grid grid-cols-3 gap-3">
              {overviewData.map(item => (
                <div key={item.name} className="bg-gray-50 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-blue-600">{item.value ?? 0}</div>
                  <div className="text-xs text-gray-500 mt-1">{item.name}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-700 mb-4">Resource Distribution</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={overviewData}>
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="value" fill="#3b82f6">
                  {overviewData.map((_, i) => <Cell key={i} fill={['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#ec4899'][i % 6]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          {overview?.dealValue !== undefined && (
            <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-700 mb-2">Pipeline Deal Value</h3>
              <div className="text-4xl font-bold text-green-600">${(overview.dealValue || 0).toLocaleString()}</div>
              <p className="text-sm text-gray-500 mt-1">Total value across all CRM deals</p>
            </div>
          )}
        </div>
      )}

      {tab === 'security' && (
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="p-4 border-b border-gray-200">
            <h3 className="font-semibold text-gray-700">User Management</h3>
          </div>
          <div className="overflow-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>{['Name', 'Email', 'Role', 'Status', 'Actions'].map(h => (
                  <th key={h} className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase">{h}</th>
                ))}</tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {users.map(u => (
                  <tr key={u.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-sm">{u.name}</td>
                    <td className="px-4 py-3 text-sm text-gray-500">{u.email}</td>
                    <td className="px-4 py-3">
                      <select
                        value={u.role}
                        onChange={e => changeRole(u.id, e.target.value)}
                        className="border border-gray-300 rounded px-2 py-1 text-xs"
                      >
                        <option value="user">User</option>
                        <option value="manager">Manager</option>
                        <option value="admin">Admin</option>
                      </select>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${u.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                        {u.is_active ? 'Active' : 'Disabled'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <button onClick={() => toggleUser(u.id)} className="text-xs text-blue-600 hover:underline">
                        {u.is_active ? 'Disable' : 'Enable'}
                      </button>
                    </td>
                  </tr>
                ))}
                {users.length === 0 && <tr><td colSpan={5} className="text-center py-8 text-gray-400 text-sm">No users</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'audit' && (
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="p-4 border-b border-gray-200">
            <h3 className="font-semibold text-gray-700">Audit Log ({auditLogs.length} entries)</h3>
          </div>
          <div className="divide-y divide-gray-100 max-h-[500px] overflow-y-auto">
            {auditLogs.map(log => (
              <div key={log.id} className="px-4 py-3 flex items-center gap-4">
                <div className="text-xs text-gray-400 w-36 flex-shrink-0">{new Date(log.created_at).toLocaleString()}</div>
                <div className="font-medium text-sm text-blue-700">{log.action}</div>
                <div className="text-sm text-gray-600">{log.resource}</div>
                <div className="text-sm text-gray-500 ml-auto">{log.user_name || 'System'}</div>
              </div>
            ))}
            {auditLogs.length === 0 && <div className="p-8 text-center text-gray-400 text-sm">No audit entries yet</div>}
          </div>
        </div>
      )}

      {tab === 'esg' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-700 mb-4">ESG Scores</h3>
            <div className="space-y-4">
              {esg.map(m => (
                <div key={m.category}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium">{m.category}</span>
                    <span className="text-gray-500">{m.score}/{m.target}</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-3">
                    <div
                      className="h-3 rounded-full bg-gradient-to-r from-green-400 to-green-600"
                      style={{ width: `${(m.score / 100) * 100}%` }}
                    />
                  </div>
                  <div className="text-xs text-gray-400 mt-0.5">Target: {m.target}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-700 mb-4">ESG Radar</h3>
            <ResponsiveContainer width="100%" height={220}>
              <RadarChart data={esg}>
                <PolarGrid />
                <PolarAngleAxis dataKey="category" tick={{ fontSize: 12 }} />
                <Radar dataKey="score" stroke="#10b981" fill="#10b981" fillOpacity={0.4} />
                <Radar dataKey="target" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.2} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
