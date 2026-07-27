import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { supplyChainApi } from '../../api/client';
import { InventoryItem } from '../../types';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, XAxis, YAxis } from 'recharts';
import React from 'react';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

export default function SupplyChainPage() {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [lowStock, setLowStock] = useState<InventoryItem[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', sku: '', category: '', quantity: '', unitCost: '', sellingPrice: '', reorderLevel: '', supplier: '' });
  const [search, setSearch] = useState('');

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const [iRes, sRes, lRes] = await Promise.all([
        supplyChainApi.getInventory(),
        supplyChainApi.getStats(),
        supplyChainApi.getLowStock(),
      ]);
      setItems(iRes.data.items);
      setStats(sRes.data);
      setLowStock(lRes.data.items);
    } catch (err) { console.error(err); }
  }

  async function addItem() {
    if (!form.name) return toast.error('Name is required');
    try {
      await supplyChainApi.createItem({
        ...form,
        quantity: parseInt(form.quantity) || 0,
        unitCost: parseFloat(form.unitCost) || 0,
        sellingPrice: parseFloat(form.sellingPrice) || 0,
        reorderLevel: parseInt(form.reorderLevel) || 0,
      });
      toast.success('Item added');
      setShowForm(false);
      setForm({ name: '', sku: '', category: '', quantity: '', unitCost: '', sellingPrice: '', reorderLevel: '', supplier: '' });
      loadData();
    } catch { toast.error('Failed'); }
  }

  async function deleteItem(id: string) {
    if (!confirm('Delete item?')) return;
    try {
      await supplyChainApi.deleteItem(id);
      toast.success('Item deleted');
      loadData();
    } catch (err) { console.error(err); }
  }

  const filtered = items.filter(i => !search || i.name.toLowerCase().includes(search.toLowerCase()) || (i.sku || '').toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Supply Chain — Inventory</h1>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-blue-50 text-blue-700 rounded-xl p-5">
          <div className="text-3xl mb-2">📦</div>
          <div className="text-2xl font-bold">{stats?.totalItems ?? 0}</div>
          <div className="text-xs opacity-70 mt-1">Total Items</div>
        </div>
        <div className="bg-green-50 text-green-700 rounded-xl p-5">
          <div className="text-3xl mb-2">💵</div>
          <div className="text-2xl font-bold">${(stats?.totalValue || 0).toLocaleString()}</div>
          <div className="text-xs opacity-70 mt-1">Total Value</div>
        </div>
        <div className={`rounded-xl p-5 ${stats?.lowStock > 0 ? 'bg-red-50 text-red-700' : 'bg-gray-50 text-gray-700'}`}>
          <div className="text-3xl mb-2">⚠️</div>
          <div className="text-2xl font-bold">{stats?.lowStock ?? 0}</div>
          <div className="text-xs opacity-70 mt-1">Low Stock Alerts</div>
        </div>
      </div>

      {/* Low stock alerts */}
      {lowStock.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <h3 className="font-semibold text-red-700 mb-2">⚠️ Low Stock Alerts</h3>
          <div className="flex flex-wrap gap-2">
            {lowStock.map(i => (
              <span key={i.id} className="bg-red-100 text-red-700 text-xs px-3 py-1 rounded-full">
                {i.name} ({i.quantity} left, reorder at {i.reorder_level})
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200">
          <div className="p-4 border-b border-gray-200 flex items-center justify-between flex-wrap gap-3">
            <h3 className="font-semibold text-gray-700">Inventory Items</h3>
            <div className="flex gap-3">
              <input
                placeholder="Search items..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="border border-gray-300 rounded px-3 py-1.5 text-sm w-36"
              />
              <button onClick={() => setShowForm(!showForm)} className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm">
                + Add Item
              </button>
            </div>
          </div>
          {showForm && (
            <div className="p-4 bg-blue-50 border-b border-blue-200 grid grid-cols-2 gap-3">
              {[['name', 'Name *'], ['sku', 'SKU'], ['category', 'Category'], ['quantity', 'Quantity'], ['unitCost', 'Unit Cost'], ['sellingPrice', 'Selling Price'], ['reorderLevel', 'Reorder Level'], ['supplier', 'Supplier']].map(([k, l]) => (
                <input key={k} placeholder={l} value={(form as any)[k]} onChange={e => setForm({ ...form, [k]: e.target.value })}
                  className="border border-gray-300 rounded px-3 py-1.5 text-sm" />
              ))}
              <div className="col-span-2 flex gap-2">
                <button onClick={addItem} className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm">Save</button>
                <button onClick={() => setShowForm(false)} className="bg-gray-200 text-gray-700 px-4 py-1.5 rounded text-sm">Cancel</button>
              </div>
            </div>
          )}
          <div className="overflow-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>{['SKU', 'Name', 'Category', 'Qty', 'Unit Cost', 'Value', ''].map(h => (
                  <th key={h} className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase">{h}</th>
                ))}</tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map(i => (
                  <tr key={i.id} className={`hover:bg-gray-50 ${i.quantity <= i.reorder_level ? 'bg-red-50' : ''}`}>
                    <td className="px-4 py-3 text-xs text-gray-400 font-mono">{i.sku || '—'}</td>
                    <td className="px-4 py-3 font-medium text-sm">{i.name}</td>
                    <td className="px-4 py-3 text-sm text-gray-500">{i.category || '—'}</td>
                    <td className="px-4 py-3 text-sm">
                      <span className={i.quantity <= i.reorder_level ? 'text-red-600 font-semibold' : 'text-gray-700'}>{i.quantity}</span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{i.unit_cost ? `$${i.unit_cost}` : '—'}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{i.unit_cost && i.quantity ? `$${(i.unit_cost * i.quantity).toLocaleString()}` : '—'}</td>
                    <td className="px-4 py-3">
                      <button onClick={() => deleteItem(i.id)} className="text-xs text-red-500 hover:underline">Delete</button>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && <tr><td colSpan={7} className="text-center py-8 text-gray-400 text-sm">No items</td></tr>}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-700 mb-4">By Category</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={stats?.categories || []} dataKey="count" nameKey="category" cx="50%" cy="50%" outerRadius={70} label={({ category }) => category}>
                {(stats?.categories || []).map((_: any, i: number) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
