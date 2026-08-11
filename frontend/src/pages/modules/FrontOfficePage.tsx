import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { frontofficeApi } from '../../api/client';
import { Customer, Deal } from '../../types';
import { FunnelChart, Funnel, LabelList, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Cell } from 'recharts';
import React from 'react';

const STAGES = ['prospecting', 'qualification', 'proposal', 'negotiation', 'closed_won', 'closed_lost'];
const STAGE_COLORS: Record<string, string> = {
  prospecting: 'bg-gray-100 text-gray-700',
  qualification: 'bg-blue-100 text-blue-700',
  proposal: 'bg-purple-100 text-purple-700',
  negotiation: 'bg-amber-100 text-amber-700',
  closed_won: 'bg-green-100 text-green-700',
  closed_lost: 'bg-red-100 text-red-700',
};

export default function FrontOfficePage() {
  const [tab, setTab] = useState<'customers' | 'deals'>('customers');
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [pipeline, setPipeline] = useState<any[]>([]);
  const [showCustForm, setShowCustForm] = useState(false);
  const [custForm, setCustForm] = useState({ name: '', email: '', phone: '', company: '', industry: '' });
  const [showDealForm, setShowDealForm] = useState(false);
  const [dealForm, setDealForm] = useState({ title: '', value: '', stage: 'prospecting', customerId: '' });
  const [search, setSearch] = useState('');

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const [cRes, dRes, pRes] = await Promise.all([
        frontofficeApi.getCustomers(),
        frontofficeApi.getDeals(),
        frontofficeApi.getPipeline(),
      ]);
      setCustomers(cRes.data.customers);
      setDeals(dRes.data.deals);
      setPipeline(pRes.data.pipeline);
    } catch (err) { console.error(err); }
  }

  async function addCustomer() {
    try {
      await frontofficeApi.createCustomer(custForm);
      toast.success('Customer added');
      setShowCustForm(false);
      setCustForm({ name: '', email: '', phone: '', company: '', industry: '' });
      loadData();
    } catch { toast.error('Failed'); }
  }

  async function addDeal() {
    try {
      await frontofficeApi.createDeal({ ...dealForm, value: parseFloat(dealForm.value) });
      toast.success('Deal added');
      setShowDealForm(false);
      setDealForm({ title: '', value: '', stage: 'prospecting', customerId: '' });
      loadData();
    } catch { toast.error('Failed'); }
  }

  const filtered = customers.filter(c =>
    !search || c.name.toLowerCase().includes(search.toLowerCase()) || (c.company || '').toLowerCase().includes(search.toLowerCase())
  );

  const pipelineData = STAGES.map(stage => {
    const found = pipeline.find(p => p.stage === stage);
    return { stage: stage.replace('_', ' '), count: found?.count || 0, value: found?.total_value || 0 };
  });

  const totalPipelineValue = pipeline.reduce((sum, p) => sum + (p.total_value || 0), 0);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Front Office — CRM</h1>
        <div className="flex gap-2">
          {(['customers', 'deals'] as const).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-1.5 rounded text-sm font-medium ${tab === t ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'}`}>
              {t === 'customers' ? '🤝 Customers' : '💼 Deals'}
            </button>
          ))}
        </div>
      </div>

      {/* Pipeline summary */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-blue-50 text-blue-700 rounded-xl p-5">
          <div className="text-3xl mb-2">🤝</div>
          <div className="text-2xl font-bold">{customers.length}</div>
          <div className="text-xs opacity-70 mt-1">Total Customers</div>
        </div>
        <div className="bg-green-50 text-green-700 rounded-xl p-5">
          <div className="text-3xl mb-2">💼</div>
          <div className="text-2xl font-bold">{deals.length}</div>
          <div className="text-xs opacity-70 mt-1">Total Deals</div>
        </div>
        <div className="bg-amber-50 text-amber-700 rounded-xl p-5">
          <div className="text-3xl mb-2">💰</div>
          <div className="text-2xl font-bold">${totalPipelineValue.toLocaleString()}</div>
          <div className="text-xs opacity-70 mt-1">Pipeline Value</div>
        </div>
      </div>

      {tab === 'customers' && (
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="p-4 border-b border-gray-200 flex items-center justify-between flex-wrap gap-3">
            <h3 className="font-semibold text-gray-700">Customers</h3>
            <div className="flex gap-3">
              <input
                placeholder="Search..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="border border-gray-300 rounded px-3 py-1.5 text-sm w-40"
              />
              <button onClick={() => setShowCustForm(!showCustForm)} className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm">
                + Add Customer
              </button>
            </div>
          </div>
          {showCustForm && (
            <div className="p-4 bg-blue-50 border-b border-blue-200 grid grid-cols-2 gap-3">
              {[['name', 'Name *'], ['email', 'Email'], ['phone', 'Phone'], ['company', 'Company'], ['industry', 'Industry']].map(([k, l]) => (
                <input key={k} placeholder={l} value={(custForm as any)[k]} onChange={e => setCustForm({ ...custForm, [k]: e.target.value })}
                  className="border border-gray-300 rounded px-3 py-1.5 text-sm" />
              ))}
              <div className="col-span-2 flex gap-2">
                <button onClick={addCustomer} className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm">Save</button>
                <button onClick={() => setShowCustForm(false)} className="bg-gray-200 text-gray-700 px-4 py-1.5 rounded text-sm">Cancel</button>
              </div>
            </div>
          )}
          <div className="overflow-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>{['Name', 'Company', 'Email', 'Industry', 'Status'].map(h => (
                  <th key={h} className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase">{h}</th>
                ))}</tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map(c => (
                  <tr key={c.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-sm">{c.name}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{c.company || '—'}</td>
                    <td className="px-4 py-3 text-sm text-gray-500">{c.email || '—'}</td>
                    <td className="px-4 py-3 text-sm text-gray-500">{c.industry || '—'}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${c.status === 'customer' ? 'bg-green-100 text-green-700' : c.status === 'lead' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'}`}>
                        {c.status}
                      </span>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && <tr><td colSpan={5} className="text-center py-8 text-gray-400 text-sm">No customers found</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'deals' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200">
            <div className="p-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="font-semibold text-gray-700">Deals</h3>
              <button onClick={() => setShowDealForm(!showDealForm)} className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm">
                + Add Deal
              </button>
            </div>
            {showDealForm && (
              <div className="p-4 bg-blue-50 border-b border-blue-200 grid grid-cols-2 gap-3">
                <input placeholder="Deal Title *" value={dealForm.title} onChange={e => setDealForm({ ...dealForm, title: e.target.value })}
                  className="border border-gray-300 rounded px-3 py-1.5 text-sm" />
                <input type="number" placeholder="Value ($)" value={dealForm.value} onChange={e => setDealForm({ ...dealForm, value: e.target.value })}
                  className="border border-gray-300 rounded px-3 py-1.5 text-sm" />
                <select value={dealForm.stage} onChange={e => setDealForm({ ...dealForm, stage: e.target.value })}
                  className="border border-gray-300 rounded px-3 py-1.5 text-sm">
                  {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
                <select value={dealForm.customerId} onChange={e => setDealForm({ ...dealForm, customerId: e.target.value })}
                  className="border border-gray-300 rounded px-3 py-1.5 text-sm">
                  <option value="">Select customer...</option>
                  {customers.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
                <div className="col-span-2 flex gap-2">
                  <button onClick={addDeal} className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm">Save</button>
                  <button onClick={() => setShowDealForm(false)} className="bg-gray-200 text-gray-700 px-4 py-1.5 rounded text-sm">Cancel</button>
                </div>
              </div>
            )}
            <div className="divide-y divide-gray-100">
              {deals.map(d => (
                <div key={d.id} className="p-4 flex items-center justify-between">
                  <div>
                    <p className="font-medium text-sm">{d.title}</p>
                    <p className="text-xs text-gray-400">{d.customer_name || 'No customer'} • {d.close_date || 'No close date'}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-medium text-sm">{d.value ? `$${d.value.toLocaleString()}` : '—'}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${STAGE_COLORS[d.stage] || 'bg-gray-100 text-gray-700'}`}>
                      {d.stage?.replace('_', ' ')}
                    </span>
                  </div>
                </div>
              ))}
              {deals.length === 0 && <div className="p-8 text-center text-gray-400 text-sm">No deals yet</div>}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-700 mb-4">Pipeline by Stage</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={pipelineData} layout="vertical">
                <XAxis type="number" tick={{ fontSize: 10 }} />
                <YAxis type="category" dataKey="stage" tick={{ fontSize: 10 }} width={80} />
                <Tooltip />
                <Bar dataKey="count" fill="#3b82f6" name="Deals" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
