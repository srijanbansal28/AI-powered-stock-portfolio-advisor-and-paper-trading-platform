import React, { useState } from 'react';
import { Database, Plus, Search, Filter, Edit3, Trash2, Check, RefreshCw, AlertCircle } from 'lucide-react';
import { saveStocksToStore } from '../data/stockDatabase';

export default function StockManager({ stocks, setStocks, onReset, currency = '$' }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSector, setSelectedSector] = useState('All');
  const [selectedRisk, setSelectedRisk] = useState('All');
  
  // Modal / Form state for Add or Edit Stock
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingStock, setEditingStock] = useState(null);

  const [formData, setFormData] = useState({
    ticker: '',
    name: '',
    sector: 'Technology',
    price: 100,
    cagr: 12,
    dividendYield: 1.5,
    risk: 'Moderate',
    beta: 1.0,
    peRatio: 20,
    description: ''
  });

  // Extract unique sectors
  const sectors = ['All', ...new Set(stocks.map(s => s.sector))];
  const riskLevels = ['All', 'Low', 'Moderate', 'High', 'Very High'];

  const filteredStocks = stocks.filter(stock => {
    const matchesSearch = stock.ticker.toLowerCase().includes(searchTerm.toLowerCase()) || stock.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesSector = selectedSector === 'All' || stock.sector === selectedSector;
    const matchesRisk = selectedRisk === 'All' || stock.risk === selectedRisk;
    return matchesSearch && matchesSector && matchesRisk;
  });

  const handleOpenAddModal = () => {
    setEditingStock(null);
    setFormData({
      ticker: '',
      name: '',
      sector: 'Technology',
      price: currency === '$' ? 150 : 1500,
      cagr: 12,
      dividendYield: 1.5,
      risk: 'Moderate',
      beta: 1.0,
      peRatio: 22,
      description: ''
    });
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (stock) => {
    setEditingStock(stock.ticker);
    setFormData({ ...stock });
    setIsModalOpen(true);
  };

  const handleSaveStock = (e) => {
    e.preventDefault();
    if (!formData.ticker || !formData.name) return;

    let updatedList = [];
    if (editingStock) {
      updatedList = stocks.map(s => s.ticker === editingStock ? { ...formData, ticker: formData.ticker.toUpperCase() } : s);
    } else {
      // Add new stock (check duplicate)
      if (stocks.some(s => s.ticker.toUpperCase() === formData.ticker.toUpperCase())) {
        alert("Stock with this Ticker symbol already exists in database!");
        return;
      }
      updatedList = [...stocks, { ...formData, ticker: formData.ticker.toUpperCase() }];
    }

    setStocks(updatedList);
    saveStocksToStore(updatedList, currency);
    setIsModalOpen(false);
  };

  const handleDeleteStock = (tickerToDelete) => {
    if (confirm(`Are you sure you want to remove ${tickerToDelete} from the stock database?`)) {
      const updatedList = stocks.filter(s => s.ticker !== tickerToDelete);
      setStocks(updatedList);
      saveStocksToStore(updatedList, currency);
    }
  };

  return (
    <div style={{ maxWidth: '1300px', margin: '0 auto', padding: '24px 16px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Header Bar */}
      <div className="glass-card" style={{ padding: '24px 28px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-green)', fontWeight: '700', fontSize: '0.88rem' }}>
            <Database size={18} />
            <span>STOCK DATABASE MANAGEMENT SYSTEM</span>
          </div>
          <h2 style={{ fontSize: '1.75rem', marginTop: '4px' }}>Stock & ETF Market Repository</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '2px' }}>
            {stocks.length} equities & funds currently configured for portfolio optimization calculations.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button onClick={onReset} className="btn btn-secondary">
            <RefreshCw size={16} />
            <span>Reset to Defaults</span>
          </button>
          <button onClick={handleOpenAddModal} className="btn btn-primary">
            <Plus size={18} />
            <span>Add Custom Stock</span>
          </button>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="glass-card" style={{ padding: '16px 20px', display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
        {/* Search */}
        <div style={{ flex: '1 1 240px', display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--bg-input)', padding: '8px 14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
          <Search size={18} color="var(--text-muted)" />
          <input
            type="text"
            placeholder="Search by Ticker or Name (e.g. AAPL, Vanguard)..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ background: 'transparent', border: 'none', color: '#ffffff', outline: 'none', width: '100%', fontSize: '0.9rem' }}
          />
        </div>

        {/* Sector Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.84rem', color: 'var(--text-muted)', fontWeight: '600' }}>Sector:</span>
          <select
            className="select-field"
            value={selectedSector}
            onChange={(e) => setSelectedSector(e.target.value)}
            style={{ padding: '8px 12px', width: 'auto' }}
          >
            {sectors.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>

        {/* Risk Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.84rem', color: 'var(--text-muted)', fontWeight: '600' }}>Risk:</span>
          <select
            className="select-field"
            value={selectedRisk}
            onChange={(e) => setSelectedRisk(e.target.value)}
            style={{ padding: '8px 12px', width: 'auto' }}
          >
            {riskLevels.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
      </div>

      {/* Stocks Table */}
      <div className="glass-card" style={{ padding: '20px' }}>
        <div className="custom-table-container">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Ticker & Name</th>
                <th>Sector</th>
                <th>Current Price</th>
                <th>Exp. CAGR %</th>
                <th>Dividend Yield</th>
                <th>Risk Profile</th>
                <th>Beta</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredStocks.map((stock) => (
                <tr key={stock.ticker}>
                  <td>
                    <div style={{ fontWeight: '800', color: '#ffffff', fontSize: '1rem' }}>{stock.ticker}</div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{stock.name}</div>
                  </td>
                  <td><span className="badge badge-blue">{stock.sector}</span></td>
                  <td style={{ fontWeight: '700', color: '#ffffff' }}>${stock.price}</td>
                  <td style={{ color: 'var(--accent-green)', fontWeight: '700' }}>{stock.cagr}% / yr</td>
                  <td style={{ color: 'var(--accent-purple)' }}>{stock.dividendYield}%</td>
                  <td>
                    <span className={`badge ${
                      stock.risk === 'Low' ? 'badge-green' :
                      stock.risk === 'Moderate' ? 'badge-blue' :
                      stock.risk === 'High' ? 'badge-amber' : 'badge-red'
                    }`}>
                      {stock.risk}
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-muted)' }}>{stock.beta}</td>
                  <td>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button
                        onClick={() => handleOpenEditModal(stock)}
                        style={{ background: 'var(--bg-input)', border: '1px solid var(--border-color)', color: 'var(--text-main)', padding: '6px 10px', borderRadius: 'var(--radius-sm)', cursor: 'pointer' }}
                      >
                        <Edit3 size={15} />
                      </button>
                      <button
                        onClick={() => handleDeleteStock(stock.ticker)}
                        style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)', color: 'var(--accent-red)', padding: '6px 10px', borderRadius: 'var(--radius-sm)', cursor: 'pointer' }}
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal Form for Add/Edit Stock */}
      {isModalOpen && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div className="glass-card animate-fade-in" style={{ width: '100%', maxWidth: '600px', padding: '28px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
            <h3 style={{ fontSize: '1.25rem', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Database size={20} color="var(--accent-green)" />
              <span>{editingStock ? `Edit ${editingStock} Metrics` : 'Add New Custom Stock / ETF'}</span>
            </h3>

            <form onSubmit={handleSaveStock} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '12px' }}>
                <div className="input-group">
                  <label className="input-label">Ticker Symbol</label>
                  <input
                    type="text"
                    className="input-field"
                    required
                    disabled={!!editingStock}
                    value={formData.ticker}
                    onChange={(e) => setFormData({ ...formData, ticker: e.target.value.toUpperCase() })}
                    placeholder="e.g. TSM"
                  />
                </div>
                <div className="input-group">
                  <label className="input-label">Company / Fund Name</label>
                  <input
                    type="text"
                    className="input-field"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g. Taiwan Semiconductor"
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="input-group">
                  <label className="input-label">Sector</label>
                  <input
                    type="text"
                    className="input-field"
                    value={formData.sector}
                    onChange={(e) => setFormData({ ...formData, sector: e.target.value })}
                  />
                </div>
                <div className="input-group">
                  <label className="input-label">Current Share Price ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    className="input-field"
                    value={formData.price}
                    onChange={(e) => setFormData({ ...formData, price: Number(e.target.value) })}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
                <div className="input-group">
                  <label className="input-label">Expected CAGR %</label>
                  <input
                    type="number"
                    step="0.1"
                    className="input-field"
                    value={formData.cagr}
                    onChange={(e) => setFormData({ ...formData, cagr: Number(e.target.value) })}
                  />
                </div>
                <div className="input-group">
                  <label className="input-label">Dividend Yield %</label>
                  <input
                    type="number"
                    step="0.01"
                    className="input-field"
                    value={formData.dividendYield}
                    onChange={(e) => setFormData({ ...formData, dividendYield: Number(e.target.value) })}
                  />
                </div>
                <div className="input-group">
                  <label className="input-label">Risk Profile</label>
                  <select
                    className="select-field"
                    value={formData.risk}
                    onChange={(e) => setFormData({ ...formData, risk: e.target.value })}
                  >
                    <option value="Low">Low</option>
                    <option value="Moderate">Moderate</option>
                    <option value="High">High</option>
                    <option value="Very High">Very High</option>
                  </select>
                </div>
              </div>

              <div className="input-group">
                <label className="input-label">Investment Thesis / Description</label>
                <textarea
                  className="input-field"
                  rows={3}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Short explanation of why this stock is included..."
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '12px' }}>
                <button type="button" onClick={() => setIsModalOpen(false)} className="btn btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  <Check size={18} />
                  <span>Save Stock Record</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
