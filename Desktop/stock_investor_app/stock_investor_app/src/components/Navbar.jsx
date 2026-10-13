import React from 'react';
import { Bot, LineChart, Table, Database, Compass, DollarSign, RefreshCw, LogOut, ChevronDown, Activity, Trophy } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, currency, setCurrency, onResetData, user, onLogout }) {
  const tabs = [
    { id: 'chat', label: 'AI Investment Chat', icon: Bot },
    { id: 'planner', label: 'Investment Planner', icon: LineChart },
    { id: 'chartsheet', label: 'Chartsheet & Portfolio', icon: Table },
    { id: 'paper', label: 'Paper Trading', icon: Activity },
    { id: 'leaderboard', label: 'Leaderboard', icon: Trophy },
    { id: 'database', label: 'Stock Database', icon: Database },
    { id: 'strategies', label: 'Strategies & Playbooks', icon: Compass },
  ];

  return (
    <header style={{
      background: 'var(--bg-secondary)',
      borderBottom: '1px solid var(--border-color)',
      position: 'sticky',
      top: 0,
      zIndex: 100
    }}>
      <div style={{
        maxWidth: '1400px',
        margin: '0 auto',
        padding: '14px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '16px'
      }}>
        {/* Brand Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer' }} onClick={() => setActiveTab('chat')}>
          <div style={{
            background: 'linear-gradient(135deg, #10b981 0%, #047857 100%)',
            width: '42px',
            height: '42px',
            borderRadius: '12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 12px rgba(16, 185, 129, 0.4)'
          }}>
            <LineChart size={24} color="#ffffff" />
          </div>
          <div>
            <div style={{ fontSize: '1.25rem', fontWeight: '800', letterSpacing: '-0.03em', color: '#ffffff' }}>
              Investwithsrijan
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: '500' }}>
              {currency === '$' ? 'AI US Stock Portfolio Advisor' : 'AI Indian Stock Portfolio Advisor'}
            </div>
          </div>
        </div>

        {/* Tab Navigation Buttons */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'var(--bg-primary)', padding: '5px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
          {tabs.map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 14px',
                  borderRadius: 'var(--radius-sm)',
                  border: 'none',
                  background: isActive ? 'var(--bg-card-hover)' : 'transparent',
                  color: isActive ? 'var(--accent-green)' : 'var(--text-muted)',
                  fontWeight: isActive ? '700' : '500',
                  fontSize: '0.88rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  borderBottom: isActive ? '2px solid var(--accent-green)' : '2px solid transparent'
                }}
              >
                <Icon size={18} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Currency & User Profile Tools */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {/* Currency Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'var(--bg-input)', padding: '4px 10px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <DollarSign size={16} color="var(--text-muted)" />
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              style={{ background: 'transparent', border: 'none', color: 'var(--text-main)', fontSize: '0.88rem', fontWeight: '600', outline: 'none', cursor: 'pointer' }}
            >
              <option value="₹">INR (₹)</option>
              <option value="$">USD ($)</option>
              <option value="€">EUR (€)</option>
              <option value="£">GBP (£)</option>
            </select>
          </div>

          <button
            onClick={onResetData}
            title="Reset Stock DB to Defaults"
            style={{ background: 'transparent', border: '1px solid var(--border-color)', color: 'var(--text-muted)', padding: '8px', borderRadius: 'var(--radius-md)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          >
            <RefreshCw size={16} />
          </button>

          {/* User Avatar + Logout */}
          {user && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', background: 'var(--bg-input)', padding: '5px 12px 5px 5px', borderRadius: 'var(--radius-full)', border: '1px solid var(--border-color)' }}>
              {user.picture ? (
                <img
                  src={user.picture}
                  alt={user.name}
                  style={{ width: '30px', height: '30px', borderRadius: '50%', objectFit: 'cover', border: '2px solid var(--accent-green)' }}
                />
              ) : (
                <div style={{ width: '30px', height: '30px', borderRadius: '50%', background: 'var(--accent-green)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.85rem', fontWeight: '700', color: '#fff' }}>
                  {user.name?.charAt(0)?.toUpperCase()}
                </div>
              )}
              <div>
                <div style={{ fontSize: '0.82rem', fontWeight: '700', color: '#ffffff', lineHeight: 1 }}>{user.name?.split(' ')[0]}</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>{user.email}</div>
              </div>
              <button
                onClick={onLogout}
                title="Sign out"
                style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center', marginLeft: '4px', borderRadius: '6px', transition: 'color 0.2s' }}
                onMouseEnter={e => e.currentTarget.style.color = 'var(--accent-red)'}
                onMouseLeave={e => e.currentTarget.style.color = 'var(--text-dim)'}
              >
                <LogOut size={16} />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

