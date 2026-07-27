import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { backofficeApi } from '../../api/client';
import { Employee, Budget, Expense } from '../../types';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import React from 'react';

export default function BackOfficePage() {
  const [tab, setTab] = useState<'hr' | 'finance'>('hr');
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [showForm, setShowForm] = useState(false);
  const [empForm, setEmpForm] = useState({ name: '', email: '', department: '', position: '', salary: '' });

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [empRes, budRes, expRes, stRes] = await Promise.all([
        backofficeApi.getEmployees(),
        backofficeApi.getBudgets(),
        backofficeApi.getExpenses(),
        backofficeApi.getStats(),
      ]);
      setEmployees(empRes.data.employees);
      setBudgets(budRes.data.budgets);
      setExpenses(expRes.data.expenses);
      setStats(stRes.data);
    } catch (err) { console.error(err); }
  }

  async function addEmployee() {
    try {
      await backofficeApi.createEmployee({ ...empForm, salary: parseFloat(empForm.salary) });
      toast.success('Employee added');
      setShowForm(false);
      setEmpForm({ name: '', email: '', department: '', position: '', salary: '' });
      loadData();
    } catch { toast.error('Failed to add employee'); }
  }

  async function deleteEmployee(id: string) {
    if (!confirm('Delete employee?')) return;
    try {
      await backofficeApi.deleteEmployee(id);
      toast.success('Employee deleted');
      loadData();
    } catch { toast.error('Failed'); }
  }

  const deptData = employees.reduce((acc: any[], emp) => {
    const existing = acc.find(d => d.dept === emp.department);
    if (existing) existing.count++;
    else acc.push({ dept: emp.department || 'N/A', count: 1 });
    return acc;
  }, []);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Back Office</h1>
        <div className="flex gap-2">
          {(['hr', 'finance'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-1.5 rounded text-sm font-medium ${tab === t ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              {t === 'hr' ? '👥 HR' : '💰 Finance'}
            </button>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard icon="👥" label="Active Employees" value={stats?.employeeCount ?? 0} color="blue" />
        <StatCard icon="💰" label="Total Budget" value={`$${(stats?.totalBudget || 0).toLocaleString()}`} color="green" />
        <StatCard icon="⏳" label="Pending Expenses" value={stats?.pendingExpenses ?? 0} color="amber" />
      </div>

      {tab === 'hr' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200">
            <div className="p-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="font-semibold text-gray-700">Employees ({employees.length})</h3>
              <button onClick={() => setShowForm(!showForm)} className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm">
                + Add Employee
              </button>
            </div>
            {showForm && (
              <div className="p-4 bg-blue-50 border-b border-blue-200 grid grid-cols-2 gap-3">
                {[['name', 'Name'], ['email', 'Email'], ['department', 'Department'], ['position', 'Position'], ['salary', 'Salary']].map(([key, label]) => (
                  <input
                    key={key}
                    placeholder={label}
                    value={(empForm as any)[key]}
                    onChange={e => setEmpForm({ ...empForm, [key]: e.target.value })}
                    className="border border-gray-300 rounded px-3 py-1.5 text-sm"
                  />
                ))}
                <div className="col-span-2 flex gap-2">
                  <button onClick={addEmployee} className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm">Save</button>
                  <button onClick={() => setShowForm(false)} className="bg-gray-200 text-gray-700 px-4 py-1.5 rounded text-sm">Cancel</button>
                </div>
              </div>
            )}
            <div className="overflow-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>{['Employee', 'Department', 'Position', 'Salary', 'Status', ''].map(h => (
                    <th key={h} className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase">{h}</th>
                  ))}</tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {employees.map(emp => (
                    <tr key={emp.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="font-medium text-sm text-gray-800">{emp.name}</div>
                        <div className="text-xs text-gray-400">{emp.email}</div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">{emp.department || '—'}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{emp.position || '—'}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{emp.salary ? `$${emp.salary.toLocaleString()}` : '—'}</td>
                      <td className="px-4 py-3">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${emp.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                          {emp.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <button onClick={() => deleteEmployee(emp.id)} className="text-xs text-red-500 hover:underline">Delete</button>
                      </td>
                    </tr>
                  ))}
                  {employees.length === 0 && (
                    <tr><td colSpan={6} className="text-center py-8 text-gray-400 text-sm">No employees yet</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-700 mb-4">By Department</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={deptData} layout="vertical">
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="dept" tick={{ fontSize: 11 }} width={80} />
                <Tooltip />
                <Bar dataKey="count" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {tab === 'finance' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-gray-200">
            <div className="p-4 border-b border-gray-200">
              <h3 className="font-semibold text-gray-700">Budgets</h3>
            </div>
            <div className="divide-y divide-gray-100">
              {budgets.map(b => (
                <div key={b.id} className="p-4">
                  <div className="flex justify-between mb-1">
                    <span className="font-medium text-sm">{b.name}</span>
                    <span className="text-sm text-gray-500">${b.amount.toLocaleString()}</span>
                  </div>
                  <div className="text-xs text-gray-400 mb-2">{b.department} • FY{b.fiscal_year}</div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                    <div
                      className="bg-blue-500 h-2 rounded-full"
                      style={{ width: `${Math.min(100, (b.spent / b.amount) * 100)}%` }}
                    />
                  </div>
                  <div className="text-xs text-gray-400 mt-1">${b.spent.toLocaleString()} spent</div>
                </div>
              ))}
              {budgets.length === 0 && <div className="p-6 text-center text-gray-400 text-sm">No budgets</div>}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200">
            <div className="p-4 border-b border-gray-200">
              <h3 className="font-semibold text-gray-700">Recent Expenses</h3>
            </div>
            <div className="divide-y divide-gray-100">
              {expenses.slice(0, 10).map(e => (
                <div key={e.id} className="p-4 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">{e.description || e.category}</p>
                    <p className="text-xs text-gray-400">{e.category} • {e.date}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">${e.amount.toLocaleString()}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${e.status === 'approved' ? 'bg-green-100 text-green-700' : e.status === 'rejected' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>
                      {e.status}
                    </span>
                  </div>
                </div>
              ))}
              {expenses.length === 0 && <div className="p-6 text-center text-gray-400 text-sm">No expenses</div>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ icon, label, value, color }: { icon: string; label: string; value: any; color: string }) {
  const colors: Record<string, string> = { blue: 'bg-blue-50 text-blue-700', green: 'bg-green-50 text-green-700', amber: 'bg-amber-50 text-amber-700' };
  return (
    <div className={`rounded-xl p-5 ${colors[color]}`}>
      <div className="text-3xl mb-2">{icon}</div>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs opacity-70 mt-1">{label}</div>
    </div>
  );
}
