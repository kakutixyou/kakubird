import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { operationsApi } from '../../api/client';
import { Task } from '../../types';
import React from 'react';

const STATUS_COLS = ['todo', 'in_progress', 'review', 'done'] as const;
const STATUS_LABELS: Record<string, string> = { todo: 'To Do', in_progress: 'In Progress', review: 'Review', done: 'Done' };
const STATUS_COLORS: Record<string, string> = { todo: 'bg-gray-100', in_progress: 'bg-blue-100', review: 'bg-amber-100', done: 'bg-green-100' };
const PRIORITY_COLORS: Record<string, string> = { low: 'bg-gray-100 text-gray-600', medium: 'bg-blue-100 text-blue-700', high: 'bg-amber-100 text-amber-700', urgent: 'bg-red-100 text-red-700' };

export default function OperationsPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [showForm, setShowForm] = useState(false);
  const [view, setView] = useState<'kanban' | 'list'>('kanban');
  const [form, setForm] = useState({ title: '', description: '', priority: 'medium', dueDate: '', module: '' });

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const [tRes, sRes] = await Promise.all([
        operationsApi.getTasks(),
        operationsApi.getTaskStats(),
      ]);
      setTasks(tRes.data.tasks);
      setStats(sRes.data);
    } catch (err) { console.error(err); }
  }

  async function addTask() {
    if (!form.title) return toast.error('Title required');
    try {
      await operationsApi.createTask(form);
      toast.success('Task created');
      setShowForm(false);
      setForm({ title: '', description: '', priority: 'medium', dueDate: '', module: '' });
      loadData();
    } catch { toast.error('Failed'); }
  }

  async function moveTask(task: Task, newStatus: string) {
    try {
      await operationsApi.updateTask(task.id, { status: newStatus });
      setTasks(tasks.map(t => t.id === task.id ? { ...t, status: newStatus as any } : t));
    } catch (err) { console.error(err); }
  }

  async function deleteTask(id: string) {
    if (!confirm('Delete task?')) return;
    try {
      await operationsApi.deleteTask(id);
      setTasks(tasks.filter(t => t.id !== id));
      toast.success('Deleted');
    } catch (err) { console.error(err); }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Operations — Tasks</h1>
        <div className="flex gap-2">
          <button onClick={() => setView(view === 'kanban' ? 'list' : 'kanban')}
            className="bg-gray-100 text-gray-700 px-3 py-1.5 rounded text-sm">
            {view === 'kanban' ? '≡ List' : '⊞ Kanban'}
          </button>
          <button onClick={() => setShowForm(!showForm)} className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm">
            + Add Task
          </button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="flex flex-wrap gap-3">
          {(stats.byStatus || []).map((s: any) => (
            <div key={s.status} className={`px-4 py-2 rounded-lg text-sm font-medium ${STATUS_COLORS[s.status] || 'bg-gray-100'}`}>
              {STATUS_LABELS[s.status] || s.status}: <strong>{s.count}</strong>
            </div>
          ))}
          {stats.overdue > 0 && (
            <div className="px-4 py-2 rounded-lg text-sm font-medium bg-red-100 text-red-700">
              Overdue: <strong>{stats.overdue}</strong>
            </div>
          )}
        </div>
      )}

      {/* Add form */}
      {showForm && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 grid grid-cols-2 gap-3">
          <input placeholder="Task Title *" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })}
            className="col-span-2 border border-gray-300 rounded px-3 py-2 text-sm" />
          <textarea placeholder="Description" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}
            className="col-span-2 border border-gray-300 rounded px-3 py-2 text-sm" rows={2} />
          <select value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })}
            className="border border-gray-300 rounded px-3 py-2 text-sm">
            {['low', 'medium', 'high', 'urgent'].map(p => <option key={p} value={p}>{p}</option>)}
          </select>
          <input type="date" value={form.dueDate} onChange={e => setForm({ ...form, dueDate: e.target.value })}
            className="border border-gray-300 rounded px-3 py-2 text-sm" />
          <input placeholder="Module (optional)" value={form.module} onChange={e => setForm({ ...form, module: e.target.value })}
            className="border border-gray-300 rounded px-3 py-2 text-sm" />
          <div className="flex gap-2 col-span-2">
            <button onClick={addTask} className="bg-blue-600 text-white px-4 py-2 rounded text-sm">Save</button>
            <button onClick={() => setShowForm(false)} className="bg-gray-200 text-gray-700 px-4 py-2 rounded text-sm">Cancel</button>
          </div>
        </div>
      )}

      {view === 'kanban' ? (
        <div className="grid grid-cols-4 gap-4">
          {STATUS_COLS.map(status => {
            const colTasks = tasks.filter(t => t.status === status);
            return (
              <div key={status} className="bg-white rounded-xl border border-gray-200 flex flex-col">
                <div className={`p-3 rounded-t-xl ${STATUS_COLORS[status]} border-b border-gray-200`}>
                  <span className="font-semibold text-sm">{STATUS_LABELS[status]}</span>
                  <span className="ml-2 text-xs text-gray-500">({colTasks.length})</span>
                </div>
                <div className="p-3 space-y-2 flex-1">
                  {colTasks.map(task => (
                    <div key={task.id} className="bg-gray-50 rounded-lg p-3 border border-gray-100">
                      <p className="text-sm font-medium text-gray-800 mb-1">{task.title}</p>
                      {task.description && <p className="text-xs text-gray-500 mb-2 line-clamp-2">{task.description}</p>}
                      <div className="flex items-center justify-between">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${PRIORITY_COLORS[task.priority]}`}>{task.priority}</span>
                        {task.due_date && <span className="text-xs text-gray-400">{task.due_date}</span>}
                      </div>
                      <div className="flex gap-1 mt-2">
                        {STATUS_COLS.filter(s => s !== status).map(s => (
                          <button key={s} onClick={() => moveTask(task, s)}
                            className="text-xs text-blue-600 hover:underline">→ {STATUS_LABELS[s]}</button>
                        ))}
                        <button onClick={() => deleteTask(task.id)} className="text-xs text-red-500 ml-auto hover:underline">✕</button>
                      </div>
                    </div>
                  ))}
                  {colTasks.length === 0 && <div className="text-xs text-gray-300 text-center py-4">Drop tasks here</div>}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>{['Title', 'Status', 'Priority', 'Module', 'Due Date', ''].map(h => (
                <th key={h} className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase">{h}</th>
              ))}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {tasks.map(t => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-sm">{t.title}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_COLORS[t.status]}`}>{STATUS_LABELS[t.status]}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${PRIORITY_COLORS[t.priority]}`}>{t.priority}</span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">{t.module || '—'}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{t.due_date || '—'}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => deleteTask(t.id)} className="text-xs text-red-500 hover:underline">Delete</button>
                  </td>
                </tr>
              ))}
              {tasks.length === 0 && <tr><td colSpan={6} className="text-center py-8 text-gray-400 text-sm">No tasks yet</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
