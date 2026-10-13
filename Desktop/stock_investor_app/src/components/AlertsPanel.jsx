import React, { useState, useEffect } from 'react';
import { Bell, BellOff, Plus, Trash2, CheckCircle, ArrowUpRight, ArrowDownRight, AlertTriangle, Volume2, ShoppingCart, Zap } from 'lucide-react';

const ALERTS_KEY = (user, currency = '$') => `investwithsrijan_alerts_${currency === '$' ? 'us' : 'in'}_${user?.sub || user?.email || 'guest'}`;
export const loadAlerts = (user, currency = '$') => { try { return JSON.parse(localStorage.getItem(ALERTS_KEY(user, currency)) || '[]'); } catch { return []; } };
export const saveAlerts = (user, alerts, currency = '$') => localStorage.setItem(ALERTS_KEY(user, currency), JSON.stringify(alerts));

// ── Sound alert using Web Audio API ──
export const playAlertSound = () => {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    // Play 3 ascending beeps
    [0, 0.15, 0.3].forEach((delay, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = 'sine';
      osc.frequency.value = 600 + i * 200; // 600, 800, 1000 Hz
      gain.gain.setValueAtTime(0.3, ctx.currentTime + delay);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + delay + 0.12);
      osc.start(ctx.currentTime + delay);
      osc.stop(ctx.currentTime + delay + 0.12);
    });
  } catch {}
};

export default function AlertsPanel({ stocks, livePrices, user, alerts, setAlerts, triggeredAlerts, onClearTriggered, holdings = [], currency = '$' }) {
  const isUSD = currency === '$';
  const fmt2 = (n) => n.toLocaleString(isUSD ? 'en-US' : 'en-IN', { maximumFractionDigits: 2 });
  const [form, setForm] = useState({ ticker: stocks[0]?.ticker || '', condition: 'BELOW', targetPrice: '', autoAction: 'NONE', autoQty: 10 });
  const [notifPerm, setNotifPerm] = useState(() => {
    try { return Notification.permission; } catch { return 'denied'; }
  });
  const [soundEnabled, setSoundEnabled] = useState(true);

  useEffect(() => { saveAlerts(user, alerts, currency); }, [alerts, user, currency]);

  const requestNotif = async () => {
    try {
      const p = await Notification.requestPermission();
      setNotifPerm(p);
    } catch {}
  };

  const addAlert = () => {
    const price = parseFloat(form.targetPrice);
    if (!form.ticker || isNaN(price) || price <= 0) return;

    if (form.autoAction === 'SELL') {
      const holding = holdings.find(h => h.ticker === form.ticker);
      if (!holding || holding.quantity <= 0) {
        alert(`Cannot create Auto-SELL alert for ${form.ticker} because you don't own any shares of it.`);
        return;
      }
      const qtyToSell = Math.max(1, parseInt(form.autoQty) || 10);
      if (qtyToSell > holding.quantity) {
        alert(`Cannot create Auto-SELL alert for ${qtyToSell} shares of ${form.ticker} because you only own ${holding.quantity} shares.`);
        return;
      }
    }

    const stock = stocks.find(s => s.ticker === form.ticker);
    setAlerts(prev => [{
      id: Date.now(),
      ticker: form.ticker,
      name: stock?.name || form.ticker,
      sector: stock?.sector || '',
      condition: form.condition,
      targetPrice: price,
      autoAction: form.autoAction, // 'NONE' | 'BUY' | 'SELL'
      autoQty: form.autoAction !== 'NONE' ? Math.max(1, parseInt(form.autoQty) || 10) : 0,
      active: true,
      triggered: false,
      executed: false,
      createdAt: new Date().toLocaleString('en-IN')
    }, ...prev]);
    setForm(f => ({ ...f, targetPrice: '' }));
  };

  const toggleAlert = (id) => setAlerts(prev => prev.map(a => a.id === id ? { ...a, active: !a.active, triggered: false, executed: false } : a));
  const deleteAlert = (id) => setAlerts(prev => prev.filter(a => a.id !== id));

  const testSound = () => playAlertSound();

  const currentStock = stocks.find(s => s.ticker === form.ticker);
  const currentLive = livePrices[form.ticker];

  const chipStyle = (active, color) => ({
    padding: '7px 14px', borderRadius: 'var(--radius-md)', fontSize: '0.8rem', fontWeight: '700',
    border: `1px solid ${active ? color : 'var(--border-color)'}`,
    background: active ? `${color}18` : 'var(--bg-input)',
    color: active ? '#fff' : 'var(--text-muted)',
    cursor: 'pointer', transition: 'all 0.15s'
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

      {/* Notification + Sound banner */}
      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
        {notifPerm !== 'granted' && (
          <div className="glass-card" style={{ flex: '1 1 300px', padding: '14px 18px', border: '1px solid rgba(245,158,11,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Bell size={17} color="var(--accent-amber)" />
              <span style={{ color: 'var(--accent-amber)', fontWeight: '600', fontSize: '0.86rem' }}>
                Enable notifications for background alerts
              </span>
            </div>
            <button onClick={requestNotif} style={{ padding: '7px 14px', background: 'var(--accent-amber)', border: 'none', color: '#000', borderRadius: 'var(--radius-md)', fontWeight: '800', cursor: 'pointer', fontSize: '0.82rem', flexShrink: 0 }}>
              Enable
            </button>
          </div>
        )}
        <div className="glass-card" style={{ flex: '0 0 auto', padding: '14px 18px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Volume2 size={17} color={soundEnabled ? 'var(--accent-green)' : 'var(--text-dim)'} />
          <span style={{ fontSize: '0.86rem', fontWeight: '600', color: soundEnabled ? '#fff' : 'var(--text-muted)' }}>Sound Alerts</span>
          <button onClick={() => setSoundEnabled(p => !p)} style={{ width: '42px', height: '24px', borderRadius: '12px', border: 'none', cursor: 'pointer', background: soundEnabled ? 'var(--accent-green)' : 'var(--bg-input)', position: 'relative', transition: 'all 0.2s' }}>
            <div style={{ width: '18px', height: '18px', borderRadius: '50%', background: '#fff', position: 'absolute', top: '3px', left: soundEnabled ? '21px' : '3px', transition: 'left 0.2s', boxShadow: '0 1px 4px rgba(0,0,0,0.3)' }} />
          </button>
          <button onClick={testSound} style={{ padding: '5px 10px', background: 'var(--bg-input)', border: '1px solid var(--border-color)', color: 'var(--text-muted)', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: '0.72rem', fontWeight: '700' }}>Test 🔊</button>
        </div>
      </div>

      {/* Recent triggered alerts */}
      {triggeredAlerts.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {triggeredAlerts.map(t => (
            <div key={t.id} className="glass-card animate-fade-in" style={{ padding: '12px 18px', border: `1px solid ${t.executed ? 'rgba(59,130,246,0.4)' : 'rgba(16,185,129,0.4)'}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                <CheckCircle size={18} color={t.executed ? '#3b82f6' : 'var(--accent-green)'} />
                <span style={{ color: '#fff', fontWeight: '600', fontSize: '0.88rem' }}>
                  🔔 <strong>{t.ticker}</strong> price {t.condition === 'BELOW' ? 'dropped below' : 'rose above'} {currency}{fmt2(t.targetPrice)}!
                  {t.executed && <span style={{ color: '#60a5fa', marginLeft: '8px' }}>⚡ Auto-{t.autoAction === 'BUY' ? 'bought' : 'sold'} {t.autoQty} shares</span>}
                </span>
              </div>
              <button onClick={() => onClearTriggered(t.id)} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '1rem', lineHeight: 1 }}>✕</button>
            </div>
          ))}
        </div>
      )}

      {/* Add Alert Form */}
      <div className="glass-card" style={{ padding: '20px 24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <Bell size={17} color="var(--accent-green)" />
          <span style={{ fontWeight: '800', color: '#fff', fontSize: '0.95rem' }}>Set New Price Alert</span>
        </div>

        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          {/* Stock */}
          <div style={{ flex: '1 1 180px' }}>
            <label style={{ fontSize: '0.76rem', color: 'var(--text-muted)', fontWeight: '700', display: 'block', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Stock</label>
            <select value={form.ticker} onChange={e => setForm(f => ({ ...f, ticker: e.target.value }))} className="input-field" style={{ width: '100%' }}>
              {stocks.map(s => <option key={s.ticker} value={s.ticker}>{s.ticker} — {s.name.slice(0, 22)}</option>)}
            </select>
          </div>

          {/* Condition */}
          <div style={{ flex: '0 0 auto' }}>
            <label style={{ fontSize: '0.76rem', color: 'var(--text-muted)', fontWeight: '700', display: 'block', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Alert When</label>
            <div style={{ display: 'flex', gap: '4px' }}>
              {[{ v: 'BELOW', icon: '↓', label: 'Below' }, { v: 'ABOVE', icon: '↑', label: 'Above' }].map(c => (
                <button key={c.v} onClick={() => setForm(f => ({ ...f, condition: c.v }))} style={chipStyle(form.condition === c.v, c.v === 'BELOW' ? '#ef4444' : '#10b981')}>
                  {c.icon} {c.label}
                </button>
              ))}
            </div>
          </div>

          {/* Target Price */}
          <div style={{ flex: '1 1 150px' }}>
            <label style={{ fontSize: '0.76rem', color: 'var(--text-muted)', fontWeight: '700', display: 'block', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Target Price ({currency})
              {currentLive && <span style={{ fontWeight: '400', textTransform: 'none', color: 'var(--text-dim)', marginLeft: '6px' }}>(Live: {currency}{fmt2(currentLive)})</span>}
            </label>
            <input
              type="number"
              placeholder={currentStock ? `e.g. ${(currentStock.price * (form.condition === 'BELOW' ? 0.95 : 1.05)).toFixed(0)}` : '250'}
              value={form.targetPrice}
              onChange={e => setForm(f => ({ ...f, targetPrice: e.target.value }))}
              onKeyDown={e => e.key === 'Enter' && addAlert()}
              className="input-field"
              style={{ width: '100%' }}
            />
          </div>
        </div>

        {/* Auto Action Row */}
        <div style={{ marginTop: '14px', padding: '14px 16px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
            <Zap size={14} color="#60a5fa" />
            <span style={{ fontSize: '0.8rem', fontWeight: '700', color: '#fff' }}>Auto Trade on Alert</span>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>(optional)</span>
          </div>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
            {[
              { v: 'NONE', label: 'No Action', color: 'var(--border-color)' },
              { v: 'BUY', label: '⚡ Auto BUY', color: '#10b981' },
              { v: 'SELL', label: '⚡ Auto SELL', color: '#ef4444' }
            ].map(a => (
              <button key={a.v} onClick={() => setForm(f => ({ ...f, autoAction: a.v }))} style={chipStyle(form.autoAction === a.v, a.color)}>
                {a.label}
              </button>
            ))}

            {form.autoAction !== 'NONE' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: '8px' }}>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: '600' }}>Qty:</span>
                {[5, 10, 25, 50].map(n => (
                  <button key={n} onClick={() => setForm(f => ({ ...f, autoQty: n }))} style={{
                    padding: '4px 10px', borderRadius: 'var(--radius-full)', fontSize: '0.76rem', fontWeight: '700',
                    border: `1px solid ${form.autoQty === n ? '#60a5fa' : 'var(--border-color)'}`,
                    background: form.autoQty === n ? 'rgba(59,130,246,0.15)' : 'var(--bg-input)',
                    color: form.autoQty === n ? '#60a5fa' : 'var(--text-muted)', cursor: 'pointer', transition: 'all 0.15s'
                  }}>{n}</button>
                ))}
                <input type="number" min="1" value={form.autoQty}
                  onChange={e => setForm(f => ({ ...f, autoQty: Math.max(1, parseInt(e.target.value) || 1) }))}
                  className="input-field" style={{ width: '65px', textAlign: 'center', padding: '5px 8px', fontSize: '0.84rem', fontWeight: '700' }}
                />
              </div>
            )}
          </div>
          {form.autoAction === 'SELL' && (
            <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px dashed var(--border-color)' }}>
              <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', fontWeight: '700', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Your Holdings
              </div>
              {holdings.length === 0 ? (
                <div style={{ fontSize: '0.8rem', color: '#ef4444', fontWeight: '500' }}>You don't own any stocks to sell.</div>
              ) : (
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {holdings.filter(h => h.quantity > 0).map(h => (
                    <button
                      key={h.ticker}
                      onClick={() => setForm(f => ({ ...f, ticker: h.ticker }))}
                      style={{
                        padding: '6px 12px', borderRadius: 'var(--radius-full)', fontSize: '0.78rem', fontWeight: '700',
                        border: `1px solid ${form.ticker === h.ticker ? '#ef4444' : 'var(--border-color)'}`,
                        background: form.ticker === h.ticker ? 'rgba(239,68,68,0.15)' : 'var(--bg-input)',
                        color: form.ticker === h.ticker ? '#ef4444' : 'var(--text-secondary)',
                        cursor: 'pointer', transition: 'all 0.15s', display: 'flex', alignItems: 'center', gap: '6px'
                      }}
                    >
                      {h.ticker} <span style={{ background: 'rgba(239,68,68,0.2)', padding: '2px 6px', borderRadius: 'var(--radius-full)', fontSize: '0.7rem' }}>{h.quantity}</span>
                    </button>
                  ))}
                  {!holdings.find(h => h.ticker === form.ticker && h.quantity > 0) && (
                    <div style={{ fontSize: '0.78rem', color: '#ef4444', display: 'flex', alignItems: 'center', marginLeft: '4px' }}>
                      <AlertTriangle size={14} style={{ marginRight: '4px' }} />
                      You don't own {form.ticker}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Submit */}
        <button onClick={addAlert} disabled={!form.targetPrice} style={{ marginTop: '14px', padding: '12px 22px', background: !form.targetPrice ? 'var(--bg-input)' : 'var(--accent-green)', border: 'none', color: '#fff', borderRadius: 'var(--radius-md)', fontWeight: '800', cursor: !form.targetPrice ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', gap: '8px', opacity: !form.targetPrice ? 0.5 : 1, transition: 'all 0.2s', width: '100%', justifyContent: 'center', fontSize: '0.92rem' }}>
          <Plus size={17} />
          {form.autoAction !== 'NONE'
            ? `Add Alert with Auto-${form.autoAction} (${form.autoQty} shares)`
            : 'Add Price Alert'}
        </button>
      </div>

      {/* Alerts List */}
      <div className="glass-card" style={{ overflow: 'hidden' }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent-green)', animation: 'pulse 1.5s infinite' }} />
            <span style={{ fontWeight: '700', color: '#fff', fontSize: '0.9rem' }}>
              Active Alerts ({alerts.filter(a => a.active && !a.triggered).length})
            </span>
          </div>
          <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>Checked every 2s • {soundEnabled ? '🔊 Sound ON' : '🔇 Sound OFF'}</span>
        </div>

        {alerts.length === 0 ? (
          <div style={{ padding: '56px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <BellOff size={38} style={{ opacity: 0.25, marginBottom: '12px' }} />
            <div style={{ fontWeight: '700', color: '#fff', marginBottom: '6px' }}>No alerts yet</div>
            <div style={{ fontSize: '0.84rem' }}>Set a price alert above to get notified when a stock hits your target</div>
          </div>
        ) : (
          <div>
            {alerts.map(alert => {
              const lp = livePrices[alert.ticker];
              const distPct = lp ? ((lp - alert.targetPrice) / alert.targetPrice * 100) : null;
              const isClose = distPct !== null && Math.abs(distPct) < 3;
              const isTriggered = alert.triggered;

              return (
                <div key={alert.id} style={{ padding: '14px 20px', borderBottom: '1px solid var(--border-color)', opacity: alert.active && !isTriggered ? 1 : 0.5, transition: 'opacity 0.3s' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                    {/* Toggle */}
                    <button onClick={() => toggleAlert(alert.id)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: alert.active && !isTriggered ? 'var(--accent-green)' : 'var(--text-muted)', flexShrink: 0, padding: '4px' }}>
                      {alert.active && !isTriggered ? <Bell size={18} /> : <BellOff size={18} />}
                    </button>

                    {/* Info */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: '700', color: '#fff', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                        <span>{alert.ticker}</span>
                        <span style={{ color: alert.condition === 'BELOW' ? '#f87171' : 'var(--accent-green)', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '2px' }}>
                          {alert.condition === 'BELOW' ? <ArrowDownRight size={14} /> : <ArrowUpRight size={14} />}
                          {alert.condition === 'BELOW' ? 'below' : 'above'}
                        </span>
                        <span style={{ fontFamily: 'var(--font-mono)', color: alert.condition === 'BELOW' ? '#f87171' : 'var(--accent-green)', fontWeight: '800' }}>
                          {currency}{fmt2(alert.targetPrice)}
                        </span>
                        {/* Auto-trade badge */}
                        {alert.autoAction && alert.autoAction !== 'NONE' && (
                          <span style={{ background: alert.autoAction === 'BUY' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)', border: `1px solid ${alert.autoAction === 'BUY' ? 'rgba(16,185,129,0.4)' : 'rgba(239,68,68,0.4)'}`, color: alert.autoAction === 'BUY' ? 'var(--accent-green)' : '#f87171', fontSize: '0.68rem', fontWeight: '800', padding: '2px 7px', borderRadius: 'var(--radius-full)', display: 'flex', alignItems: 'center', gap: '3px' }}>
                            <Zap size={9} /> Auto-{alert.autoAction} {alert.autoQty}
                          </span>
                        )}
                        {isTriggered && <span style={{ background: 'rgba(16,185,129,0.15)', border: '1px solid var(--accent-green)', color: 'var(--accent-green)', fontSize: '0.7rem', fontWeight: '800', padding: '2px 7px', borderRadius: 'var(--radius-full)' }}>{alert.executed ? 'EXECUTED ✓' : 'TRIGGERED ✓'}</span>}
                        {isClose && !isTriggered && alert.active && <span style={{ background: 'rgba(245,158,11,0.15)', border: '1px solid var(--accent-amber)', color: 'var(--accent-amber)', fontSize: '0.7rem', fontWeight: '800', padding: '2px 7px', borderRadius: 'var(--radius-full)', display: 'flex', alignItems: 'center', gap: '3px' }}><AlertTriangle size={10} />NEAR TARGET</span>}
                      </div>
                      <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '3px' }}>{alert.name.slice(0, 30)} • Set {alert.createdAt}</div>
                    </div>

                    {/* Live price + distance */}
                    {lp && (
                      <div style={{ textAlign: 'right', flexShrink: 0 }}>
                        <div style={{ fontFamily: 'var(--font-mono)', fontWeight: '700', color: '#fff', fontSize: '0.9rem' }}>{currency}{fmt2(lp)}</div>
                        <div style={{ fontSize: '0.72rem', color: isClose ? 'var(--accent-amber)' : 'var(--text-muted)', marginTop: '2px' }}>
                          {distPct !== null ? `${distPct >= 0 ? '+' : ''}${distPct.toFixed(1)}% from target` : ''}
                        </div>
                      </div>
                    )}

                    {/* Delete */}
                    <button onClick={() => deleteAlert(alert.id)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-dim)', padding: '4px', flexShrink: 0, transition: 'color 0.2s' }} onMouseEnter={e => e.currentTarget.style.color = '#ef4444'} onMouseLeave={e => e.currentTarget.style.color = 'var(--text-dim)'}>
                      <Trash2 size={15} />
                    </button>
                  </div>

                  {/* Progress bar toward target */}
                  {lp && !isTriggered && alert.active && (
                    <div style={{ marginTop: '10px', height: '3px', background: 'var(--bg-input)', borderRadius: '2px', overflow: 'hidden' }}>
                      <div style={{
                        height: '100%',
                        width: `${Math.min(100, Math.max(2, 100 - Math.abs(distPct || 0) * 5))}%`,
                        background: isClose ? 'var(--accent-amber)' : alert.condition === 'BELOW' ? '#ef4444' : 'var(--accent-green)',
                        borderRadius: '2px', transition: 'width 0.5s'
                      }} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
      <style>{`@keyframes pulse { 0%,100%{opacity:.5;transform:scale(.8)} 50%{opacity:1;transform:scale(1)} }`}</style>
    </div>
  );
}
