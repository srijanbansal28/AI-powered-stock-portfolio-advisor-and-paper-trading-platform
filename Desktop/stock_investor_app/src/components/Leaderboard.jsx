import React, { useState, useEffect } from 'react';
import { Trophy, RefreshCw, TrendingUp, TrendingDown, Crown, Medal, Award } from 'lucide-react';

const FS_URL = 'https://firestore.googleapis.com/v1/projects/investiq-ai-a1b2c/databases/(default)/documents';

// ── Firestore helpers ──
const toFS = (obj) => ({
  fields: Object.fromEntries(
    Object.entries(obj).map(([k, v]) => {
      if (typeof v === 'number') return [k, { doubleValue: v }];
      if (typeof v === 'boolean') return [k, { booleanValue: v }];
      return [k, { stringValue: String(v ?? '') }];
    })
  )
});

const fromFS = (doc) => {
  if (!doc?.fields) return null;
  return Object.fromEntries(
    Object.entries(doc.fields).map(([k, v]) => {
      if ('doubleValue' in v) return [k, v.doubleValue];
      if ('integerValue' in v) return [k, Number(v.integerValue)];
      if ('booleanValue' in v) return [k, v.booleanValue];
      return [k, v.stringValue ?? ''];
    })
  );
};

// ── Export: called from PaperTrading whenever portfolio changes ──
export const syncToLeaderboard = async (user, portfolioData) => {
  if (!user) return;
  const uid = (user.sub || user.email || 'anon').replace(/[^a-zA-Z0-9_-]/g, '_');
  try {
    await fetch(`${FS_URL}/leaderboard/${uid}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(toFS({
        name: user.name || 'Anonymous',
        picture: user.picture || '',
        email: user.email || '',
        ...portfolioData,
        lastUpdated: new Date().toISOString()
      }))
    });
  } catch { /* Silently fail */ }
};

const getRankBadge = (i) => {
  if (i === 0) return { icon: <Crown size={18} color="#FFD700" />, bg: 'rgba(255,215,0,0.1)', border: 'rgba(255,215,0,0.3)' };
  if (i === 1) return { icon: <Medal size={18} color="#C0C0C0" />, bg: 'rgba(192,192,192,0.08)', border: 'rgba(192,192,192,0.25)' };
  if (i === 2) return { icon: <Award size={18} color="#CD7F32" />, bg: 'rgba(205,127,50,0.08)', border: 'rgba(205,127,50,0.25)' };
  return { icon: <span style={{ fontWeight: '800', color: 'var(--text-muted)', fontSize: '0.88rem' }}>#{i + 1}</span>, bg: 'transparent', border: 'transparent' };
};

export default function Leaderboard({ user, currency = '$' }) {
  const isUSD = currency === '$';
  const STARTING = isUSD ? 100000 : 1000000;
  const fmt = (n) => `${currency}${Math.abs(n).toLocaleString(isUSD ? 'en-US' : 'en-IN', { maximumFractionDigits: 0 })}`;

  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [rtdbError, setRtdbError] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(null);

  const fetch_ = async () => {
    setLoading(true);
    setRtdbError(false);
    try {
      const res = await fetch(`${FS_URL}/leaderboard`);
      if (!res.ok) throw new Error('not_found');
      const data = await res.json();
      if (!data?.documents || data.documents.length === 0) { setEntries([]); setLastRefresh(new Date()); return; }
      const list = data.documents
        .map(doc => fromFS(doc))
        .filter(e => e?.name)
        .sort((a, b) => (b.totalAssets || 0) - (a.totalAssets || 0));
      setEntries(list);
      setLastRefresh(new Date());
    } catch {
      setRtdbError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetch_(); }, []);

  const myName = user?.name;

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '24px 16px', display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Trophy size={24} color="#FFD700" />
            <h1 style={{ fontSize: '1.4rem', fontWeight: '800', margin: 0 }}>Paper Trading Leaderboard</h1>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.84rem', margin: '4px 0 0 32px' }}>
            Global ranking of all Investwithsrijan paper traders • Starting capital $100,000 each
          </p>
        </div>
        <button onClick={fetch_} disabled={loading} style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '9px 16px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: 'var(--radius-md)', cursor: loading ? 'wait' : 'pointer', fontWeight: '600', fontSize: '0.84rem' }}>
          <RefreshCw size={15} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {/* Firestore setup required */}
      {rtdbError && (
        <div className="glass-card" style={{ padding: '28px', border: '1px solid rgba(245,158,11,0.3)' }}>
          <div style={{ fontWeight: '800', color: 'var(--accent-amber)', marginBottom: '12px', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            ⚙️ One-time Setup Required for Leaderboard
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', lineHeight: '1.7', margin: '0 0 16px' }}>
            The leaderboard uses Cloud Firestore to store rankings across all users. Update your Firestore security rules:
          </p>
          <div style={{ background: 'var(--bg-input)', borderRadius: 'var(--radius-md)', padding: '16px 20px', border: '1px solid var(--border-color)', fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: '2' }}>
            <div><strong style={{ color: '#fff' }}>Step 1</strong> → Open <a href="https://console.firebase.google.com/project/investiq-ai-a1b2c/firestore/databases/-default-/rules" target="_blank" rel="noreferrer" style={{ color: 'var(--accent-green)', textDecoration: 'none', fontWeight: '700' }}>Firebase Console → Firestore → Rules</a></div>
            <div><strong style={{ color: '#fff' }}>Step 2</strong> → Replace all rules with this and click <strong style={{ color: 'var(--accent-amber)' }}>Publish</strong>:</div>
            <div style={{ background: 'var(--bg-secondary)', borderRadius: '6px', padding: '10px 14px', fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--accent-green)', margin: '4px 0', border: '1px solid var(--border-color)', whiteSpace: 'pre-wrap' }}>
{`rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /leaderboard/{userId} {
      allow read, write: if true;
    }
  }
}`}
            </div>
            <div><strong style={{ color: '#fff' }}>Step 3</strong> → Come back here and click <strong>Refresh</strong> ✅</div>
          </div>
        </div>
      )}

      {/* Leaderboard table */}
      {!rtdbError && (
        <div className="glass-card" style={{ overflow: 'hidden' }}>
          {loading ? (
            <div style={{ padding: '64px', textAlign: 'center', color: 'var(--text-muted)' }}>
              <RefreshCw size={32} style={{ animation: 'spin 1s linear infinite', marginBottom: '16px', opacity: 0.3 }} />
              <div>Loading rankings...</div>
            </div>
          ) : entries.length === 0 ? (
            <div style={{ padding: '64px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
              <Trophy size={44} style={{ opacity: 0.15, marginBottom: '16px' }} />
              <div style={{ fontWeight: '800', color: '#fff', marginBottom: '8px', fontSize: '1.05rem' }}>No traders on the board yet</div>
              <div style={{ fontSize: '0.86rem' }}>Start paper trading to be the first on the leaderboard!</div>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: 'var(--bg-secondary)' }}>
                    {['Rank', 'Trader', 'Total Assets', 'Profit / Loss', 'Return %', 'Holdings', 'Trades', 'Last Active'].map(h => (
                      <th key={h} style={{ padding: '11px 16px', textAlign: 'left', fontSize: '0.72rem', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', whiteSpace: 'nowrap' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {entries.map((e, i) => {
                    const pnl = (e.totalAssets || 0) - STARTING;
                    const retPct = (pnl / STARTING) * 100;
                    const badge = getRankBadge(i);
                    const isMe = e.name === myName;
                    return (
                      <tr key={i}
                        style={{ borderTop: '1px solid var(--border-color)', background: isMe ? 'rgba(16,185,129,0.05)' : 'transparent', transition: 'background 0.2s' }}
                        onMouseEnter={ev => ev.currentTarget.style.background = 'var(--bg-card-hover)'}
                        onMouseLeave={ev => ev.currentTarget.style.background = isMe ? 'rgba(16,185,129,0.05)' : 'transparent'}
                      >
                        {/* Rank */}
                        <td style={{ padding: '14px 16px' }}>
                          <div style={{ width: '30px', height: '30px', borderRadius: '8px', background: badge.bg, border: `1px solid ${badge.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            {badge.icon}
                          </div>
                        </td>

                        {/* Trader */}
                        <td style={{ padding: '14px 16px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            {e.picture
                              ? <img src={e.picture} alt="" referrerPolicy="no-referrer" style={{ width: '34px', height: '34px', borderRadius: '50%', border: `2px solid ${isMe ? 'var(--accent-green)' : 'var(--border-color)'}`, flexShrink: 0 }} />
                              : <div style={{ width: '34px', height: '34px', borderRadius: '50%', background: 'var(--bg-input)', border: '2px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.88rem', color: 'var(--text-muted)', fontWeight: '700', flexShrink: 0 }}>{(e.name || '?')[0]}</div>
                            }
                            <div>
                              <div style={{ fontWeight: '700', color: '#fff', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                {e.name}
                                {isMe && <span style={{ fontSize: '0.66rem', color: 'var(--accent-green)', fontWeight: '800', background: 'rgba(16,185,129,0.15)', padding: '1px 6px', borderRadius: 'var(--radius-full)', border: '1px solid rgba(16,185,129,0.3)' }}>YOU</span>}
                              </div>
                            </div>
                          </div>
                        </td>

                        {/* Total Assets */}
                        <td style={{ padding: '14px 16px', fontWeight: '800', fontFamily: 'var(--font-mono)', color: '#fff', fontSize: '0.95rem' }}>
                          {fmt(e.totalAssets || 0)}
                        </td>

                        {/* P&L */}
                        <td style={{ padding: '14px 16px', fontWeight: '700', fontFamily: 'var(--font-mono)', color: pnl >= 0 ? 'var(--accent-green)' : '#f87171' }}>
                          {pnl >= 0 ? '+' : '-'}{fmt(pnl)}
                        </td>

                        {/* Return % */}
                        <td style={{ padding: '14px 16px' }}>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontWeight: '800', color: retPct >= 0 ? 'var(--accent-green)' : '#f87171', fontSize: '0.9rem' }}>
                            {retPct >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                            {retPct >= 0 ? '+' : ''}{retPct.toFixed(2)}%
                          </span>
                        </td>

                        {/* Holdings */}
                        <td style={{ padding: '14px 16px', color: 'var(--text-muted)', fontSize: '0.86rem' }}>{e.holdings || 0} stocks</td>

                        {/* Trades */}
                        <td style={{ padding: '14px 16px', color: 'var(--text-muted)', fontSize: '0.86rem' }}>{e.trades || 0} trades</td>

                        {/* Last active */}
                        <td style={{ padding: '14px 16px', color: 'var(--text-dim)', fontSize: '0.76rem', whiteSpace: 'nowrap' }}>
                          {e.lastUpdated ? new Date(e.lastUpdated).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' }) : '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {lastRefresh && !rtdbError && (
        <div style={{ textAlign: 'center', fontSize: '0.74rem', color: 'var(--text-dim)' }}>
          Last refreshed: {lastRefresh.toLocaleTimeString('en-IN')} • Auto-updates when traders make trades
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
