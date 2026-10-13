import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  TrendingUp, TrendingDown, Plus, Minus, RefreshCw, Clock,
  Wallet, BarChart2, ArrowUpRight, ArrowDownRight,
  X, AlertCircle, CheckCircle, Activity, DollarSign, Trash2, Bot, Bell
} from 'lucide-react';
import PortfolioAdvisor from './PortfolioAdvisor';
import AlertsPanel, { loadAlerts, saveAlerts, playAlertSound } from './AlertsPanel';
import { syncToLeaderboard } from './Leaderboard';

// ─── Helpers ─────────────────────────────────────────────────────────────────

const VIRTUAL_BALANCE_DEFAULT = (curr = '$') => curr === '$' ? 100000 : 1000000;
const STORAGE_PREFIX = (curr = '$') => `investwithsrijan_paper_${curr === '$' ? 'us' : 'in'}_`;

const getUserKey = (user, curr = '$') => `${STORAGE_PREFIX(curr)}${user?.sub || user?.email || 'guest'}`;

const fmt = (n, curr = '$') => new Intl.NumberFormat(curr === '$' ? 'en-US' : 'en-IN', { style: 'currency', currency: curr === '$' ? 'USD' : 'INR', maximumFractionDigits: 2 }).format(n);
const fmtNum = (n, curr = '$') => new Intl.NumberFormat(curr === '$' ? 'en-US' : 'en-IN', { maximumFractionDigits: 2 }).format(n);
const fmtPct = (n) => `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;

const loadUserData = (user, curr = '$') => {
  try {
    const raw = localStorage.getItem(getUserKey(user, curr));
    if (raw) return JSON.parse(raw);
  } catch {}
  return {
    virtualBalance: VIRTUAL_BALANCE_DEFAULT(curr),
    holdings: [],
    transactions: []
  };
};

const saveUserData = (user, data, curr = '$') => {
  localStorage.setItem(getUserKey(user, curr), JSON.stringify(data));
};

// ─── Sub-components ──────────────────────────────────────────────────────────

function StatCard({ label, value, sub, color, icon: Icon, blink }) {
  return (
    <div className="glass-card" style={{ padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: '6px', flex: '1 1 180px', minWidth: 0 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '0.76rem', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</span>
        {Icon && <Icon size={16} color={color || 'var(--text-muted)'} />}
      </div>
      <div style={{ fontSize: '1.35rem', fontWeight: '800', color: color || '#ffffff', transition: 'color 0.3s', letterSpacing: '-0.02em' }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{sub}</div>}
    </div>
  );
}

function PriceTag({ price, prevPrice, currency = '$' }) {
  const up = price >= prevPrice;
  const color = price === prevPrice ? 'var(--text-muted)' : up ? 'var(--accent-green)' : 'var(--accent-red)';
  return (
    <span style={{ color, fontWeight: '700', fontSize: '0.92rem', transition: 'color 0.4s', fontFamily: 'var(--font-mono)' }}>
      {fmt(price, currency)}
    </span>
  );
}

// ─── BUY / SELL Modal ────────────────────────────────────────────────────────

function TradeModal({ stock, livePrice, type, virtualBalance, holdings, onConfirm, onClose, currency = '$' }) {
  const [qty, setQty] = useState(1);
  const holding = holdings.find(h => h.ticker === stock.ticker);
  const maxSell = holding?.quantity || 0;
  const total = livePrice * qty;
  const canBuy = type === 'BUY' && total <= virtualBalance;
  const canSell = type === 'SELL' && qty <= maxSell;
  const canConfirm = type === 'BUY' ? canBuy && qty > 0 : canSell && qty > 0;

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '16px' }}>
      <div className="glass-card animate-fade-in" style={{ width: '100%', maxWidth: '420px', padding: '28px', border: `1px solid ${type === 'BUY' ? 'rgba(16,185,129,0.4)' : 'rgba(239,68,68,0.4)'}` }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <div style={{ fontWeight: '800', fontSize: '1.1rem', color: '#fff' }}>
              <span style={{ color: type === 'BUY' ? 'var(--accent-green)' : 'var(--accent-red)' }}>{type}</span> {stock.ticker}
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{stock.name}</div>
          </div>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
            <X size={20} />
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 16px', background: 'var(--bg-input)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>Live Price</span>
            <span style={{ fontWeight: '800', color: '#fff', fontFamily: 'var(--font-mono)' }}>{fmt(livePrice, currency)}</span>
          </div>

          <div>
            <label style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: '600', display: 'block', marginBottom: '8px' }}>
              {type === 'SELL' ? `Quantity (max: ${maxSell})` : 'Quantity'}
            </label>

            {/* Input row with – and + */}
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '10px' }}>
              <button onClick={() => setQty(q => Math.max(1, q - 1))} style={{ padding: '10px 14px', background: 'var(--bg-input)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: 'var(--radius-md)', cursor: 'pointer', flexShrink: 0 }}>
                <Minus size={16} />
              </button>
              <input
                type="number" min="1" max={type === 'SELL' ? maxSell : 99999}
                value={qty}
                onChange={e => setQty(Math.max(1, parseInt(e.target.value) || 1))}

                className="input-field"
                style={{ textAlign: 'center', flex: 1, fontWeight: '700', fontSize: '1.1rem' }}
              />
              <button onClick={() => setQty(q => type === 'SELL' ? Math.min(maxSell, q + 1) : q + 1)} style={{ padding: '10px 14px', background: 'var(--bg-input)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: 'var(--radius-md)', cursor: 'pointer', flexShrink: 0 }}>
                <Plus size={16} />
              </button>
            </div>

            {/* Quick-add chips */}
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {[5, 10, 25, 50].map(n => {
                const maxAllowed = type === 'SELL' ? maxSell : Math.floor(virtualBalance / livePrice);
                const disabled = type === 'SELL' ? n > maxSell : n * livePrice > virtualBalance;
                return (
                  <button
                    key={n}
                    disabled={disabled}
                    onClick={() => setQty(q => type === 'SELL' ? Math.min(maxSell, q + n) : q + n)}
                    style={{
                      padding: '5px 12px', borderRadius: 'var(--radius-full)', fontSize: '0.78rem', fontWeight: '700',
                      border: `1px solid ${type === 'BUY' ? 'rgba(16,185,129,0.4)' : 'rgba(239,68,68,0.4)'}`,
                      background: type === 'BUY' ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)',
                      color: disabled ? 'var(--text-dim)' : type === 'BUY' ? 'var(--accent-green)' : '#f87171',
                      cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.4 : 1,
                      transition: 'all 0.15s'
                    }}
                  >+{n}</button>
                );
              })}
              {/* SET button — max affordable / max holdings */}
              <button
                onClick={() => {
                  if (type === 'SELL') setQty(maxSell);
                  else setQty(Math.max(1, Math.floor(virtualBalance / livePrice)));
                }}
                style={{
                  padding: '5px 12px', borderRadius: 'var(--radius-full)', fontSize: '0.78rem', fontWeight: '700',
                  border: '1px solid var(--border-color)', background: 'var(--bg-input)',
                  color: 'var(--text-muted)', cursor: 'pointer', marginLeft: 'auto', transition: 'all 0.15s'
                }}
              >{type === 'SELL' ? 'MAX' : 'MAX AFFORD'}</button>
            </div>
          </div>


          <div style={{ padding: '16px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Total Value</span>
              <span style={{ fontWeight: '800', fontSize: '1.1rem', color: type === 'BUY' ? 'var(--accent-green)' : 'var(--accent-red)', fontFamily: 'var(--font-mono)' }}>{fmt(total)}</span>
            </div>
            {type === 'BUY' && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>Remaining Balance</span>
                <span style={{ fontSize: '0.85rem', color: canBuy ? 'var(--text-muted)' : 'var(--accent-red)', fontFamily: 'var(--font-mono)' }}>
                  {fmt(virtualBalance - total)}
                </span>
              </div>
            )}
          </div>

          {!canConfirm && (
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', color: 'var(--accent-red)', fontSize: '0.82rem' }}>
              <AlertCircle size={14} />
              {type === 'BUY' ? 'Insufficient virtual balance' : `You only have ${maxSell} shares`}
            </div>
          )}

          <button
            onClick={() => canConfirm && onConfirm(qty, livePrice)}
            disabled={!canConfirm}
            style={{
              padding: '14px', borderRadius: 'var(--radius-md)', fontWeight: '800', fontSize: '0.95rem',
              border: 'none', cursor: canConfirm ? 'pointer' : 'not-allowed', opacity: canConfirm ? 1 : 0.4,
              background: type === 'BUY' ? 'var(--accent-green)' : '#ef4444',
              color: '#fff', transition: 'all 0.2s', width: '100%'
            }}
          >
            {type === 'BUY' ? `Buy ${qty} share${qty > 1 ? 's' : ''} for ${fmt(total)}` : `Sell ${qty} share${qty > 1 ? 's' : ''} for ${fmt(total)}`}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────

export default function PaperTrading({ stocks, user, currency = '$' }) {
  const isUSD = currency === '$';
  const [userData, setUserData] = useState(() => loadUserData(user, currency));
  
  // Reload userData when user or currency changes
  useEffect(() => {
    setUserData(loadUserData(user, currency));
  }, [user, currency]);

  const [livePrices, setLivePrices] = useState(() => {
    const init = {};
    stocks.forEach(s => { init[s.ticker] = s.price; });
    return init;
  });

  const [liveChanges, setLiveChanges] = useState({});

  useEffect(() => {
    const init = {};
    stocks.forEach(s => { init[s.ticker] = s.price; });
    setLivePrices(init);
  }, [stocks]);

  const prevPrices = useRef({ ...livePrices });
  const [modal, setModal] = useState(null);
  const [toast, setToast] = useState(null);
  const [activeTab, setActiveTab] = useState('market');
  const [searchQuery, setSearchQuery] = useState('');
  const [resetConfirm, setResetConfirm] = useState(false);
  const [alerts, setAlerts] = useState(() => loadAlerts(user, currency));
  
  useEffect(() => {
    setAlerts(loadAlerts(user, currency));
  }, [user, currency]);

  const [triggeredAlerts, setTriggeredAlerts] = useState([]);
  const userDataRef = useRef(userData);

  // Save whenever userData changes
  useEffect(() => {
    userDataRef.current = userData;
    saveUserData(user, userData, currency);
  }, [userData, user, currency]);

  const livePricesRef = useRef(livePrices);
  useEffect(() => {
    livePricesRef.current = livePrices;
  }, [livePrices]);

  const [apiStatus, setApiStatus] = useState({ connected: false, message: 'Connecting...' });

  // Live Prices API Effect (Finnhub for US $, IndianAPI for IN ₹) + Real-Time Micro-Tick Stream
  useEffect(() => {
    let ws = null;
    let isMounted = true;

    if (isUSD) {
      const apiKey = 'd9uup9pr01qv408i8iugd9uup9pr01qv408i8iv0';
      
      const fetchInitial = async () => {
        let successCount = 0;
        // Prioritize held stocks first
        const prioritized = [...stocks].sort((a, b) => {
          const aHeld = userData.holdings.some(h => h.ticker === a.ticker);
          const bHeld = userData.holdings.some(h => h.ticker === b.ticker);
          return (bHeld ? 1 : 0) - (aHeld ? 1 : 0);
        });

        for (let i = 0; i < prioritized.length; i += 3) {
          if (!isMounted) break;
          const chunk = prioritized.slice(i, i + 3);
          await Promise.all(chunk.map(async (s) => {
            try {
              const res = await fetch(`https://finnhub.io/api/v1/quote?symbol=${s.ticker}&token=${apiKey}`);
              if (res.ok) {
                const data = await res.json();
                if (data && data.c && data.c > 0) {
                  setLivePrices(prev => {
                    if (prev[s.ticker] !== data.c) {
                      prevPrices.current[s.ticker] = prev[s.ticker] || s.price;
                      return { ...prev, [s.ticker]: data.c };
                    }
                    return prev;
                  });
                  if (data.dp !== undefined) {
                    setLiveChanges(prev => ({ ...prev, [s.ticker]: data.dp }));
                  }
                  successCount++;
                }
              }
            } catch (err) {}
          }));
          await new Promise(r => setTimeout(r, 150));
        }

        if (isMounted) {
          setApiStatus({ connected: true, message: `Finnhub Live (${successCount} stocks synced)` });
        }
      };
      fetchInitial();

      try {
        ws = new WebSocket(`wss://ws.finnhub.io?token=${apiKey}`);
        
        ws.addEventListener('open', () => {
          stocks.forEach(s => {
            ws.send(JSON.stringify({ 'type': 'subscribe', 'symbol': s.ticker }));
          });
        });

        ws.addEventListener('message', (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'trade' && isMounted) {
              setLivePrices(prev => {
                const next = { ...prev };
                let changed = false;
                data.data.forEach(trade => {
                  if (next[trade.s] !== undefined && next[trade.s] !== trade.p) {
                    prevPrices.current[trade.s] = next[trade.s];
                    next[trade.s] = trade.p;
                    changed = true;
                  }
                });
                return changed ? next : prev;
              });
            }
          } catch (err) {}
        });
      } catch (err) {}
    } else {
      // Indian Market Real-Time Data (Calling IndianAPI.in with user key)
      const apiKey = 'sk-live-5tgick95oHFMxlp8pROf6BWTI19tzOv9DYy6hlqX';

      const getIndianApiQuery = (s) => {
        const clean = s.ticker.replace('.NS', '').replace('.BO', '');
        if (clean === 'TCS') return 'TCS';
        if (clean === 'DRREDDY') return 'DRREDDY';
        if (clean === 'POWERGRID') return 'Power Grid';
        if (clean === 'NIFTYBEES') return 'Nifty 50';
        if (clean === 'JUNIORBEES') return 'Junior BeES';
        if (clean === 'BANKBEES') return 'Bank BeES';
        if (clean === 'GOLDBEES') return 'Gold BeES';
        if (clean === 'LT') return 'Larsen';
        if (clean === 'BHARTIARTL') return 'Bharti Airtel';
        if (clean === 'HDFCBANK') return 'HDFC Bank';
        if (clean === 'ICICIBANK') return 'ICICI Bank';
        if (clean === 'SBIN') return 'State Bank of India';
        if (clean === 'BAJFINANCE') return 'Bajaj Finance';
        if (clean === 'RELIANCE') return 'Reliance';
        if (clean === 'TATAMOTORS') return 'Tata Motors';
        if (clean === 'HINDUNILVR') return 'Hindustan Unilever';
        if (clean === 'ASIANPAINT') return 'Asian Paints';
        if (clean === 'TITAN') return 'Titan';
        if (clean === 'MARUTI') return 'Maruti Suzuki';
        if (clean === 'M&M') return 'Mahindra & Mahindra';
        if (clean === 'SUNPHARMA') return 'Sun Pharma';
        if (clean === 'CIPLA') return 'Cipla';
        if (clean === 'APOLLOHOSP') return 'Apollo Hospitals';
        if (clean === 'ULTRACEMCO') return 'UltraTech Cement';
        if (clean === 'ADANIENT') return 'Adani Enterprises';
        if (clean === 'ADANIPORTS') return 'Adani Ports';
        return s.name.replace(/ Limited| Corporation| Ltd| Company/gi, '').trim() || clean;
      };

      const fetchIndianQuotes = async () => {
        let successCount = 0;
        let lastError = null;

        // Process in sequential batches of 3 to prevent 429 Rate Limit
        for (let i = 0; i < stocks.length; i += 3) {
          if (!isMounted) break;
          const chunk = stocks.slice(i, i + 3);
          await Promise.all(chunk.map(async (s) => {
            const query = getIndianApiQuery(s);
            try {
              const res = await fetch(`https://stock.indianapi.in/stock?name=${encodeURIComponent(query)}`, {
                headers: {
                  'x-api-key': apiKey,
                  'Accept': 'application/json'
                }
              });
              if (res.status === 429) {
                lastError = 'Rate limit reached, pausing';
                return;
              }
              const data = await res.json();
              const price = parseFloat(data?.currentPrice?.NSE || data?.currentPrice?.BSE || data?.stockPrice);
              const pct = parseFloat(data?.percentChange);
              if (price && !isNaN(price) && price > 0) {
                setLivePrices(prev => {
                  if (prev[s.ticker] !== price) {
                    prevPrices.current[s.ticker] = prev[s.ticker];
                    return { ...prev, [s.ticker]: price };
                  }
                  return prev;
                });
                if (!isNaN(pct)) {
                  setLiveChanges(prev => ({ ...prev, [s.ticker]: pct }));
                }
                successCount++;
              } else if (data?.message || data?.error) {
                lastError = data.message || data.error;
              }
            } catch (err) {
              lastError = err.message;
            }
          }));

          // Small 250ms spacing between chunks
          await new Promise(r => setTimeout(r, 250));
        }

        if (isMounted) {
          if (successCount > 0) {
            setApiStatus({ connected: true, message: `IndianAPI.in Live (${successCount} stocks synced)` });
          } else {
            setApiStatus({ connected: false, message: lastError ? `API: ${lastError}` : 'Waiting for IndianAPI.in...' });
          }
        }
      };

      fetchIndianQuotes();
      const interval = setInterval(fetchIndianQuotes, 30000);
    }

    // Active Live Micro-Tick Streamer (every 2.5 seconds)
    // Ensures real-time order-book fluctuations, live P&L changes, and active simulated trading 24/7
    const tickInterval = setInterval(() => {
      if (!isMounted) return;
      setLivePrices(prev => {
        const next = { ...prev };
        let anyChanged = false;
        const countToTick = Math.min(stocks.length, Math.floor(Math.random() * 4) + 3);
        const shuffled = [...stocks].sort(() => 0.5 - Math.random()).slice(0, countToTick);

        shuffled.forEach(stock => {
          const current = next[stock.ticker] || stock.price;
          const beta = stock.beta || 1.0;
          // Micro-movement: ±0.08% to ±0.2%
          const deltaPct = (Math.random() * 0.003 - 0.0015) * beta;
          const newPrice = Math.max(0.5, Number((current * (1 + deltaPct)).toFixed(2)));
          if (newPrice !== current) {
            prevPrices.current[stock.ticker] = current;
            next[stock.ticker] = newPrice;
            anyChanged = true;
          }
        });

        return anyChanged ? next : prev;
      });
    }, 2500);

    return () => {
      isMounted = false;
      if (ws) ws.close();
      clearInterval(tickInterval);
    };
  }, [stocks, currency, isUSD, userData.holdings]);

  // Check smart alerts periodically
  useEffect(() => {
    const interval = setInterval(() => {
      const currentPrices = livePricesRef.current;

      // Check smart alerts against new prices
      setAlerts(prevAlerts => {
        let anyTriggered = false;
        const updated = prevAlerts.map(alert => {
          if (!alert.active || alert.triggered) return alert;
          const price = currentPrices[alert.ticker];
          if (!price) return alert;
          const hit = alert.condition === 'BELOW' ? price <= alert.targetPrice : price >= alert.targetPrice;
          if (!hit) return alert;

          anyTriggered = true;

          // 🔊 Play sound alert
          try { playAlertSound(); } catch {}

          // ⚡ Auto-trade logic using latest state via ref
          let executed = false;
          let actualQty = alert.autoQty || 10;
          let tradeMsg = '';
          const currentData = userDataRef.current;

          if (alert.autoAction === 'BUY') {
            if (currentData.virtualBalance >= price) {
              if (currentData.virtualBalance < actualQty * price) {
                actualQty = Math.floor(currentData.virtualBalance / price);
              }
              executed = true;
              tradeMsg = ` • Auto-bought ${actualQty} shares!`;
            }
          } else if (alert.autoAction === 'SELL') {
            const holding = currentData.holdings.find(h => h.ticker === alert.ticker);
            if (holding && holding.quantity > 0) {
              if (holding.quantity < actualQty) {
                actualQty = holding.quantity;
              }
              executed = true;
              tradeMsg = ` • Auto-sold ${actualQty} shares!`;
            }
          }

          // Browser notification
          try {
            if (Notification.permission === 'granted') {
              new Notification(`🔔 ${alert.ticker} Price Alert!`, {
                body: `${alert.ticker} is now $${price.toFixed(2)} — ${alert.condition === 'BELOW' ? 'below' : 'above'} your target of $${alert.targetPrice.toLocaleString('en-US')}${tradeMsg}`,
                icon: '/favicon.ico'
              });
            }
          } catch {}

          // Update actual state if executed
          if (executed) {
            setUserData(prev => {
              const upd = { ...prev };
              const txn = {
                id: Date.now() + Math.random(),
                type: alert.autoAction,
                ticker: alert.ticker,
                name: alert.name,
                quantity: actualQty,
                price: price,
                total: actualQty * price,
                avgBuyPrice: alert.autoAction === 'SELL' ? (prev.holdings.find(h => h.ticker === alert.ticker)?.avgBuyPrice || 0) : price,
                realizedPnL: alert.autoAction === 'SELL' ? (price - (prev.holdings.find(h => h.ticker === alert.ticker)?.avgBuyPrice || 0)) * actualQty : null,
                timestamp: `⚡ Auto | ${new Date().toLocaleString('en-US')}`
              };

              if (alert.autoAction === 'BUY') {
                upd.virtualBalance = prev.virtualBalance - (actualQty * price);
                upd.transactions = [txn, ...prev.transactions].slice(0, 200);
                const existIdx = prev.holdings.findIndex(h => h.ticker === alert.ticker);
                if (existIdx >= 0) {
                  const existing = prev.holdings[existIdx];
                  const newQty = existing.quantity + actualQty;
                  const newAvg = (existing.quantity * existing.avgBuyPrice + actualQty * price) / newQty;
                  upd.holdings = prev.holdings.map((h, i) => i === existIdx ? { ...h, quantity: newQty, avgBuyPrice: newAvg } : h);
                } else {
                  upd.holdings = [...prev.holdings, { ticker: alert.ticker, name: alert.name, sector: alert.sector || '', quantity: actualQty, avgBuyPrice: price }];
                }
              } else if (alert.autoAction === 'SELL') {
                upd.virtualBalance = prev.virtualBalance + (actualQty * price);
                upd.transactions = [txn, ...prev.transactions].slice(0, 200);
                upd.holdings = prev.holdings
                  .map(h => h.ticker === alert.ticker ? { ...h, quantity: h.quantity - actualQty } : h)
                  .filter(h => h.quantity > 0);
              }
              return upd;
            });
          }

          setTriggeredAlerts(t => [...t, { ...alert, triggeredPrice: price, executed, autoQty: executed ? actualQty : alert.autoQty }]);
          setToast({ type: alert.autoAction !== 'NONE' && executed ? alert.autoAction : 'ALERT', ticker: alert.ticker, qty: actualQty, price });

          return { ...alert, triggered: true, active: false, executed, autoQty: executed ? actualQty : alert.autoQty };
        });

        return anyTriggered ? updated : prevAlerts;
      });
    }, 2000);
    return () => clearInterval(interval);
  }, [stocks]);

  // Sync to leaderboard whenever portfolio changes
  useEffect(() => {
    const t = setTimeout(() => {
      const portfolioValue = userData.holdings.reduce((s, h) => s + h.quantity * (livePrices[h.ticker] || h.avgBuyPrice), 0);
      const totalAssets = userData.virtualBalance + portfolioValue;
      syncToLeaderboard(user, {
        totalAssets,
        virtualBalance: userData.virtualBalance,
        holdings: userData.holdings.length,
        trades: userData.transactions.length,
      });
    }, 3000); // debounce 3s
    return () => clearTimeout(t);
  }, [userData, user]);

  // Auto-dismiss toast
  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(null), 3500);
      return () => clearTimeout(t);
    }
  }, [toast]);

  // ── Portfolio calculations ──
  const portfolioValue = userData.holdings.reduce((sum, h) => {
    return sum + h.quantity * (livePrices[h.ticker] || h.avgBuyPrice);
  }, 0);

  const totalInvested = userData.holdings.reduce((sum, h) => sum + h.quantity * h.avgBuyPrice, 0);
  const totalPnL = portfolioValue - totalInvested;
  const totalPnLPct = totalInvested > 0 ? (totalPnL / totalInvested) * 100 : 0;
  const totalAssets = userData.virtualBalance + portfolioValue;
  const startingCapital = VIRTUAL_BALANCE_DEFAULT(currency);
  const overallReturn = ((totalAssets - startingCapital) / startingCapital) * 100;

  // ── Trade handlers ──
  const handleTrade = useCallback((qty, price) => {
    const { stock, type } = modal;
    setUserData(prev => {
      const updated = { ...prev };
      const holding = prev.holdings.find(h => h.ticker === stock.ticker);
      const txn = {
        id: Date.now(),
        type,
        ticker: stock.ticker,
        name: stock.name,
        quantity: qty,
        price,
        total: qty * price,
        // For SELL: store buy price and realized P&L
        avgBuyPrice: type === 'SELL' ? (holding?.avgBuyPrice || 0) : price,
        realizedPnL: type === 'SELL' ? (price - (holding?.avgBuyPrice || 0)) * qty : null,
        timestamp: new Date().toLocaleString('en-US')
      };

      updated.transactions = [txn, ...prev.transactions].slice(0, 200);

      if (type === 'BUY') {
        updated.virtualBalance = prev.virtualBalance - qty * price;
        const existingIdx = prev.holdings.findIndex(h => h.ticker === stock.ticker);
        if (existingIdx >= 0) {
          const existing = prev.holdings[existingIdx];
          const newQty = existing.quantity + qty;
          const newAvg = (existing.quantity * existing.avgBuyPrice + qty * price) / newQty;
          updated.holdings = prev.holdings.map((h, i) =>
            i === existingIdx ? { ...h, quantity: newQty, avgBuyPrice: newAvg } : h
          );
        } else {
          updated.holdings = [...prev.holdings, {
            ticker: stock.ticker,
            name: stock.name,
            sector: stock.sector,
            quantity: qty,
            avgBuyPrice: price
          }];
        }
      } else {
        updated.virtualBalance = prev.virtualBalance + qty * price;
        updated.holdings = prev.holdings
          .map(h => h.ticker === stock.ticker ? { ...h, quantity: h.quantity - qty } : h)
          .filter(h => h.quantity > 0);
      }

      return updated;
    });

    setToast({ type, ticker: stock.ticker, qty, price });
    setModal(null);
  }, [modal]);

  const handleReset = () => {
    const fresh = { virtualBalance: VIRTUAL_BALANCE_DEFAULT(currency), holdings: [], transactions: [] };
    setUserData(fresh);
    saveUserData(user, fresh, currency);
    setResetConfirm(false);
    setToast({ type: 'RESET' });
  };

  const filteredStocks = stocks.filter(s =>
    s.ticker.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.sector.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '24px 16px', display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Toast */}
      {toast && (
        <div className="animate-fade-in" style={{
          position: 'fixed', top: '80px', right: '20px', zIndex: 999,
          background: toast.type === 'RESET' ? 'var(--bg-secondary)' : toast.type === 'BUY' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
          border: `1px solid ${toast.type === 'BUY' ? 'var(--accent-green)' : toast.type === 'SELL' ? '#ef4444' : 'var(--border-color)'}`,
          borderRadius: 'var(--radius-md)', padding: '12px 18px',
          display: 'flex', alignItems: 'center', gap: '10px',
          boxShadow: 'var(--shadow-card)', maxWidth: '320px'
        }}>
          <CheckCircle size={18} color={toast.type === 'BUY' ? 'var(--accent-green)' : toast.type === 'SELL' ? '#ef4444' : 'var(--text-muted)'} />
          <span style={{ fontSize: '0.88rem', color: '#fff', fontWeight: '600' }}>
            {toast.type === 'RESET' ? `Portfolio reset to ${isUSD ? '$100,000' : '₹10,00,000'}!` :
              `${toast.type === 'BUY' ? 'Bought' : 'Sold'} ${toast.qty}x ${toast.ticker} @ ${fmt(toast.price, currency)}`}
          </span>
        </div>
      )}

      {/* Trade Modal */}
      {modal && (
        <TradeModal
          stock={modal.stock}
          type={modal.type}
          livePrice={livePrices[modal.stock.ticker] || modal.stock.price}
          virtualBalance={userData.virtualBalance}
          holdings={userData.holdings}
          onConfirm={handleTrade}
          onClose={() => setModal(null)}
          currency={currency}
        />
      )}

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Activity size={22} color="var(--accent-green)" />
            <h1 style={{ fontSize: '1.4rem', fontWeight: '800', margin: 0 }}>Paper Trading</h1>
            <span style={{ background: 'rgba(245,158,11,0.15)', border: '1px solid var(--accent-amber)', color: 'var(--accent-amber)', fontSize: '0.7rem', fontWeight: '700', padding: '3px 8px', borderRadius: 'var(--radius-full)' }}>SIMULATED</span>
            <span style={{ background: apiStatus.connected ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)', border: `1px solid ${apiStatus.connected ? 'var(--accent-green)' : 'rgba(239,68,68,0.4)'}`, color: apiStatus.connected ? 'var(--accent-green)' : '#f87171', fontSize: '0.7rem', fontWeight: '700', padding: '3px 8px', borderRadius: 'var(--radius-full)' }}>
              {apiStatus.message}
            </span>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.84rem', margin: '4px 0 0 0' }}>
            Practice investing with {isUSD ? '$100,000' : '₹10,00,000'} virtual money • Real-time {isUSD ? 'Finnhub' : 'Market Data'} Prices
          </p>
        </div>
        <button
          onClick={() => setResetConfirm(true)}
          style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: '#f87171', padding: '8px 14px', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontSize: '0.84rem', fontWeight: '600' }}
        >
          <RefreshCw size={15} />
          Reset Portfolio
        </button>
      </div>

      {/* Reset confirm */}
      {resetConfirm && (
        <div className="glass-card animate-fade-in" style={{ padding: '16px 20px', border: '1px solid rgba(239,68,68,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
          <span style={{ color: '#f87171', fontWeight: '600', fontSize: '0.9rem' }}>⚠️ This will erase all your paper trades and reset to {isUSD ? '$100,000' : '₹10,00,000'}. Are you sure?</span>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button onClick={() => setResetConfirm(false)} style={{ padding: '8px 14px', background: 'var(--bg-input)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontSize: '0.84rem' }}>Cancel</button>
            <button onClick={handleReset} style={{ padding: '8px 14px', background: '#ef4444', border: 'none', color: '#fff', borderRadius: 'var(--radius-md)', cursor: 'pointer', fontSize: '0.84rem', fontWeight: '700' }}>Yes, Reset</button>
          </div>
        </div>
      )}

      {/* Stats Row */}
      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
        <StatCard label="Virtual Cash" value={fmt(userData.virtualBalance, currency)} icon={Wallet} color="var(--accent-green)" sub="Available to invest" />
        <StatCard label="Portfolio Value" value={fmt(portfolioValue, currency)} icon={BarChart2} color="var(--accent-blue)" sub={`${userData.holdings.length} positions`} />
        <StatCard
          label="Unrealised P&L"
          value={fmt(totalPnL, currency)}
          icon={totalPnL >= 0 ? TrendingUp : TrendingDown}
          color={totalPnL >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'}
          sub={fmtPct(totalPnLPct)}
        />
        <StatCard
          label="Total Assets"
          value={fmt(totalAssets, currency)}
          icon={DollarSign}
          color={overallReturn >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'}
          sub={`${fmtPct(overallReturn)} overall return`}
        />
      </div>

      {/* Tab Switcher */}
      <div style={{ display: 'flex', gap: '4px', background: 'var(--bg-secondary)', padding: '4px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', width: 'fit-content' }}>
        {[
        { id: 'market', label: '📈 Market' },
        { id: 'holdings', label: `💼 Holdings (${userData.holdings.length})` },
        { id: 'history', label: `📋 History (${userData.transactions.length})` },
        { id: 'advisor', label: '🤖 AI Advisor', highlight: true },
        { id: 'alerts', label: `🔔 Alerts (${alerts.filter(a => a.active && !a.triggered).length})` },
      ].map(t => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            style={{
              padding: '8px 18px', borderRadius: '8px', border: 'none', cursor: 'pointer', fontWeight: '700',
              fontSize: '0.84rem', fontFamily: 'var(--font-sans)', transition: 'all 0.2s',
              background: activeTab === t.id ? (t.highlight ? 'linear-gradient(135deg,#10b981,#059669)' : 'var(--accent-green)') : 'transparent',
              color: activeTab === t.id ? '#fff' : t.highlight ? 'var(--accent-green)' : 'var(--text-muted)',
              boxShadow: activeTab === t.id && t.highlight ? '0 4px 14px rgba(16,185,129,0.35)' : 'none'
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── MARKET TAB ── */}
      {activeTab === 'market' && (
        <div className="glass-card" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <input
              className="input-field"
              placeholder="Search stocks (ticker, name, sector)..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{ flex: 1, minWidth: '200px' }}
            />
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem', color: 'var(--accent-green)' }}>
              <div style={{ width: '7px', height: '7px', borderRadius: '50%', background: 'var(--accent-green)', animation: 'pulse 1.5s infinite' }} />
              Live prices (2s)
            </div>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: 'var(--bg-secondary)' }}>
                  {['Stock', 'Sector', 'Live Price', 'Change', 'CAGR', 'Risk', 'Action'].map(h => (
                    <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontSize: '0.74rem', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', whiteSpace: 'nowrap' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredStocks.map((stock, i) => {
                  const lp = livePrices[stock.ticker] || stock.price;
                  const pp = prevPrices.current[stock.ticker] || stock.price;
                  const change = liveChanges[stock.ticker] !== undefined 
                    ? liveChanges[stock.ticker] 
                    : (((lp - stock.price) / stock.price) * 100);
                  const holding = userData.holdings.find(h => h.ticker === stock.ticker);
                  return (
                    <tr key={stock.ticker} style={{ borderTop: '1px solid var(--border-color)', transition: 'background 0.2s' }}
                      onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-card-hover)'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                    >
                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ fontWeight: '700', color: '#fff', fontSize: '0.9rem' }}>{stock.ticker}</div>
                        <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>{stock.name.slice(0, 28)}{stock.name.length > 28 ? '…' : ''}</div>
                        {holding && <div style={{ fontSize: '0.72rem', color: 'var(--accent-green)', marginTop: '2px' }}>Holding {holding.quantity} shares</div>}
                      </td>
                      <td style={{ padding: '12px 16px' }}><span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{stock.sector}</span></td>
                      <td style={{ padding: '12px 16px' }}><PriceTag price={lp} prevPrice={pp} currency={currency} /></td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{ color: change >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', fontSize: '0.84rem', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '3px' }}>
                          {change >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                          {fmtPct(change)}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px' }}><span style={{ color: 'var(--accent-green)', fontWeight: '700', fontSize: '0.84rem' }}>{stock.cagr}%</span></td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{ fontSize: '0.74rem', padding: '3px 8px', borderRadius: 'var(--radius-full)', fontWeight: '700',
                          background: stock.risk === 'Low' ? 'rgba(16,185,129,0.15)' : stock.risk === 'Moderate' ? 'rgba(59,130,246,0.15)' : 'rgba(245,158,11,0.15)',
                          color: stock.risk === 'Low' ? 'var(--accent-green)' : stock.risk === 'Moderate' ? 'var(--accent-blue)' : 'var(--accent-amber)'
                        }}>{stock.risk}</span>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                          <button onClick={() => setModal({ stock, type: 'BUY' })} style={{ padding: '6px 12px', background: 'rgba(16,185,129,0.15)', border: '1px solid var(--accent-green)', color: 'var(--accent-green)', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: '0.78rem', fontWeight: '700' }}>BUY</button>
                          {holding && holding.quantity > 0 && (
                            <button onClick={() => setModal({ stock, type: 'SELL' })} style={{ padding: '6px 12px', background: 'rgba(239,68,68,0.15)', border: '1px solid #ef4444', color: '#ef4444', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: '0.78rem', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '4px' }}>
                              SELL
                              <span style={{ background: 'rgba(239,68,68,0.3)', padding: '1px 5px', borderRadius: 'var(--radius-full)', fontSize: '0.68rem' }}>{holding.quantity}</span>
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── HOLDINGS TAB ── */}
      {activeTab === 'holdings' && (
        <div className="glass-card" style={{ overflow: 'hidden' }}>
          {userData.holdings.length === 0 ? (
            <div style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
              <BarChart2 size={40} style={{ opacity: 0.3, marginBottom: '12px' }} />
              <div style={{ fontWeight: '700', marginBottom: '6px', color: '#fff' }}>No holdings yet</div>
              <div style={{ fontSize: '0.85rem' }}>Go to the Market tab and buy your first stock!</div>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: 'var(--bg-secondary)' }}>
                    {['Stock', 'Qty', 'Avg Buy Price', 'Current Price', 'Invested', 'Current Value', 'P&L', 'P&L %', 'Action'].map(h => (
                      <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontSize: '0.74rem', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', whiteSpace: 'nowrap' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {userData.holdings.map(h => {
                    const lp = livePrices[h.ticker] || h.avgBuyPrice;
                    const pp = prevPrices.current[h.ticker] || h.avgBuyPrice;
                    const invested = h.quantity * h.avgBuyPrice;
                    const currentVal = h.quantity * lp;
                    const pnl = currentVal - invested;
                    const pnlPct = (pnl / invested) * 100;
                    const stock = stocks.find(s => s.ticker === h.ticker);
                    return (
                      <tr key={h.ticker} style={{ borderTop: '1px solid var(--border-color)', transition: 'background 0.2s' }}
                        onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-card-hover)'}
                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                      >
                        <td style={{ padding: '12px 16px' }}>
                          <div style={{ fontWeight: '700', color: '#fff', fontSize: '0.9rem' }}>{h.ticker}</div>
                          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>{h.sector}</div>
                        </td>
                        <td style={{ padding: '12px 16px', fontWeight: '700', color: '#fff', fontFamily: 'var(--font-mono)' }}>{h.quantity}</td>
                        <td style={{ padding: '12px 16px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.86rem' }}>{fmt(h.avgBuyPrice, currency)}</td>
                        <td style={{ padding: '12px 16px' }}><PriceTag price={lp} prevPrice={pp} currency={currency} /></td>
                        <td style={{ padding: '12px 16px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.86rem' }}>{fmt(invested, currency)}</td>
                        <td style={{ padding: '12px 16px', fontWeight: '700', color: '#fff', fontFamily: 'var(--font-mono)' }}>{fmt(currentVal, currency)}</td>
                        <td style={{ padding: '12px 16px', fontWeight: '800', color: pnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', fontFamily: 'var(--font-mono)' }}>
                          {pnl >= 0 ? '+' : ''}{fmt(pnl, currency)}
                        </td>
                        <td style={{ padding: '12px 16px' }}>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '3px', fontWeight: '700', color: pnlPct >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', fontSize: '0.86rem' }}>
                            {pnlPct >= 0 ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}
                            {Math.abs(pnlPct).toFixed(2)}%
                          </span>
                        </td>
                        <td style={{ padding: '12px 16px' }}>
                          {stock && h.quantity > 0 && (
                            <button onClick={() => setModal({ stock, type: 'SELL' })} style={{ padding: '6px 12px', background: 'rgba(239,68,68,0.15)', border: '1px solid #ef4444', color: '#ef4444', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: '0.78rem', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '4px' }}>
                              SELL
                              <span style={{ background: 'rgba(239,68,68,0.3)', padding: '1px 5px', borderRadius: 'var(--radius-full)', fontSize: '0.68rem' }}>{h.quantity}</span>
                            </button>
                          )}
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

      {/* ── HISTORY TAB ── */}
      {activeTab === 'history' && (() => {
        // Compute summary stats from transactions
        const sellTxns = userData.transactions.filter(t => t.type === 'SELL' && t.realizedPnL != null);
        const totalRealizedPnL = sellTxns.reduce((s, t) => s + t.realizedPnL, 0);
        const totalBuyAmount = userData.transactions.filter(t => t.type === 'BUY').reduce((s, t) => s + t.total, 0);
        const totalSellAmount = sellTxns.reduce((s, t) => s + t.total, 0);
        const winningTrades = sellTxns.filter(t => t.realizedPnL > 0).length;
        const losingTrades = sellTxns.filter(t => t.realizedPnL < 0).length;

        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

            {/* Summary Cards */}
            {userData.transactions.length > 0 && (
              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                <div className="glass-card" style={{ flex: '1 1 160px', padding: '16px 18px' }}>
                  <div style={{ fontSize: '0.72rem', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '6px' }}>Total Invested</div>
                  <div style={{ fontSize: '1.2rem', fontWeight: '800', color: '#fff', fontFamily: 'var(--font-mono)' }}>{fmt(totalBuyAmount, currency)}</div>
                  <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '4px' }}>{userData.transactions.filter(t => t.type === 'BUY').length} buy orders</div>
                </div>
                <div className="glass-card" style={{ flex: '1 1 160px', padding: '16px 18px' }}>
                  <div style={{ fontSize: '0.72rem', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '6px' }}>Total Sold</div>
                  <div style={{ fontSize: '1.2rem', fontWeight: '800', color: '#fff', fontFamily: 'var(--font-mono)' }}>{fmt(totalSellAmount, currency)}</div>
                  <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '4px' }}>{sellTxns.length} sell orders</div>
                </div>
                <div className="glass-card" style={{ flex: '1 1 160px', padding: '16px 18px', border: `1px solid ${totalRealizedPnL >= 0 ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}` }}>
                  <div style={{ fontSize: '0.72rem', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '6px' }}>Realised P&L</div>
                  <div style={{ fontSize: '1.2rem', fontWeight: '800', color: totalRealizedPnL >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', fontFamily: 'var(--font-mono)' }}>
                    {totalRealizedPnL >= 0 ? '+' : ''}{fmt(totalRealizedPnL, currency)}
                  </div>
                  <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                    {totalBuyAmount > 0 ? `${((totalRealizedPnL / totalBuyAmount) * 100).toFixed(2)}% return on sold` : 'No completed trades'}
                  </div>
                </div>
                <div className="glass-card" style={{ flex: '1 1 160px', padding: '16px 18px' }}>
                  <div style={{ fontSize: '0.72rem', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '6px' }}>Win / Loss</div>
                  <div style={{ fontSize: '1.2rem', fontWeight: '800', fontFamily: 'var(--font-mono)' }}>
                    <span style={{ color: 'var(--accent-green)' }}>{winningTrades}W</span>
                    <span style={{ color: 'var(--text-muted)', margin: '0 6px' }}>/</span>
                    <span style={{ color: 'var(--accent-red)' }}>{losingTrades}L</span>
                  </div>
                  <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                    {sellTxns.length > 0 ? `${((winningTrades / sellTxns.length) * 100).toFixed(0)}% win rate` : 'No completed trades'}
                  </div>
                </div>
              </div>
            )}

            {/* Transaction Table */}
            <div className="glass-card" style={{ overflow: 'hidden' }}>
              {userData.transactions.length === 0 ? (
                <div style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  <Clock size={40} style={{ opacity: 0.3, marginBottom: '12px' }} />
                  <div style={{ fontWeight: '700', marginBottom: '6px', color: '#fff' }}>No transactions yet</div>
                  <div style={{ fontSize: '0.85rem' }}>Your trade history will appear here</div>
                </div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ background: 'var(--bg-secondary)' }}>
                        {['Type', 'Stock', 'Qty', 'Buy Price', 'Sell Price', 'Amount', 'Profit / Loss', 'Date & Time'].map(h => (
                          <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontSize: '0.74rem', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', whiteSpace: 'nowrap' }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {userData.transactions.map(tx => {
                        const hasPnL = tx.type === 'SELL' && tx.realizedPnL != null;
                        const pnlPct = hasPnL && tx.avgBuyPrice > 0
                          ? ((tx.price - tx.avgBuyPrice) / tx.avgBuyPrice) * 100
                          : null;
                        return (
                          <tr key={tx.id}
                            style={{ borderTop: '1px solid var(--border-color)', transition: 'background 0.2s', background: hasPnL ? (tx.realizedPnL >= 0 ? 'rgba(16,185,129,0.03)' : 'rgba(239,68,68,0.03)') : 'transparent' }}
                            onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-card-hover)'}
                            onMouseLeave={e => e.currentTarget.style.background = hasPnL ? (tx.realizedPnL >= 0 ? 'rgba(16,185,129,0.03)' : 'rgba(239,68,68,0.03)') : 'transparent'}
                          >
                            <td style={{ padding: '12px 16px' }}>
                              <span style={{
                                padding: '4px 10px', borderRadius: 'var(--radius-full)', fontSize: '0.75rem', fontWeight: '800',
                                background: tx.type === 'BUY' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
                                color: tx.type === 'BUY' ? 'var(--accent-green)' : '#f87171'
                              }}>{tx.type}</span>
                            </td>
                            <td style={{ padding: '12px 16px' }}>
                              <div style={{ fontWeight: '700', color: '#fff', fontSize: '0.88rem' }}>{tx.ticker}</div>
                              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{tx.name?.slice(0, 22)}</div>
                            </td>
                            <td style={{ padding: '12px 16px', fontWeight: '700', color: '#fff', fontFamily: 'var(--font-mono)' }}>{tx.quantity}</td>

                            {/* Buy Price */}
                            <td style={{ padding: '12px 16px', fontFamily: 'var(--font-mono)', fontSize: '0.86rem' }}>
                              {tx.type === 'BUY'
                                ? <span style={{ color: 'var(--accent-green)', fontWeight: '700' }}>{fmt(tx.price, currency)}</span>
                                : <span style={{ color: 'var(--text-muted)' }}>{tx.avgBuyPrice ? fmt(tx.avgBuyPrice, currency) : '—'}</span>
                              }
                            </td>

                            {/* Sell Price */}
                            <td style={{ padding: '12px 16px', fontFamily: 'var(--font-mono)', fontSize: '0.86rem' }}>
                              {tx.type === 'SELL'
                                ? <span style={{ color: '#f87171', fontWeight: '700' }}>{fmt(tx.price, currency)}</span>
                                : <span style={{ color: 'var(--text-dim)' }}>—</span>
                              }
                            </td>

                            {/* Amount */}
                            <td style={{ padding: '12px 16px', fontWeight: '700', fontFamily: 'var(--font-mono)', color: tx.type === 'BUY' ? '#f87171' : 'var(--accent-green)' }}>
                              {tx.type === 'BUY' ? '-' : '+'}{fmt(tx.total, currency)}
                            </td>

                            {/* Profit / Loss — only for SELL */}
                            <td style={{ padding: '12px 16px' }}>
                              {hasPnL ? (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                  <span style={{ fontWeight: '800', fontFamily: 'var(--font-mono)', fontSize: '0.9rem', color: tx.realizedPnL >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                                    {tx.realizedPnL >= 0 ? '+' : ''}{fmt(tx.realizedPnL, currency)}
                                  </span>
                                  {pnlPct !== null && (
                                    <span style={{ fontSize: '0.74rem', color: tx.realizedPnL >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', display: 'flex', alignItems: 'center', gap: '2px' }}>
                                      {tx.realizedPnL >= 0 ? <ArrowUpRight size={11} /> : <ArrowDownRight size={11} />}
                                      {Math.abs(pnlPct).toFixed(2)}%
                                    </span>
                                  )}
                                </div>
                              ) : (
                                <span style={{ color: 'var(--text-dim)', fontSize: '0.82rem' }}>Open position</span>
                              )}
                            </td>

                            <td style={{ padding: '12px 16px', fontSize: '0.8rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{tx.timestamp}</td>
                          </tr>
                        );
                      })}
                    </tbody>

                    {/* Footer totals row */}
                    {sellTxns.length > 0 && (
                      <tfoot>
                        <tr style={{ background: 'var(--bg-secondary)', borderTop: '2px solid var(--border-color)' }}>
                          <td colSpan={5} style={{ padding: '12px 16px', fontWeight: '800', color: 'var(--text-muted)', fontSize: '0.82rem' }}>TOTAL REALISED P&L</td>
                          <td style={{ padding: '12px 16px' }}></td>
                          <td style={{ padding: '12px 16px', fontWeight: '800', fontFamily: 'var(--font-mono)', fontSize: '1rem', color: totalRealizedPnL >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                            {totalRealizedPnL >= 0 ? '+' : ''}{fmt(totalRealizedPnL, currency)}
                          </td>
                          <td></td>
                        </tr>
                      </tfoot>
                    )}
                  </table>
                </div>
              )}
            </div>
          </div>
        );
      })()}

      {/* ── AI ADVISOR TAB ── */}
      {activeTab === 'advisor' && (
        <PortfolioAdvisor
          holdings={userData.holdings}
          transactions={userData.transactions}
          virtualBalance={userData.virtualBalance}
          livePrices={livePrices}
          totalAssets={totalAssets}
          currency={currency}
        />
      )}

      {/* ── SMART ALERTS TAB ── */}
      {activeTab === 'alerts' && (
        <AlertsPanel
          stocks={stocks}
          livePrices={livePrices}
          user={user}
          alerts={alerts}
          setAlerts={setAlerts}
          triggeredAlerts={triggeredAlerts}
          onClearTriggered={(id) => setTriggeredAlerts(prev => prev.filter(t => t.id !== id))}
          holdings={userData.holdings}
          currency={currency}
        />
      )}

      <style>{`
        @keyframes pulse { 0%,100%{opacity:.5;transform:scale(.8)} 50%{opacity:1;transform:scale(1)} }
      `}</style>
    </div>
  );
}
