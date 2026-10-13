import React, { useState } from 'react';
import { Bot, Sparkles, RefreshCw, TrendingUp, TrendingDown, ShieldAlert, Lightbulb, Target } from 'lucide-react';

const GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent';
const fmt = (n) => `$${Math.abs(n).toLocaleString('en-US', { maximumFractionDigits: 0 })}`;

// Simple markdown renderer
function RichText({ text }) {
  const lines = text.split('\n');
  return (
    <div style={{ lineHeight: '1.75', fontSize: '0.9rem' }}>
      {lines.map((line, i) => {
        const render = (t) => t.replace(/\*\*(.*?)\*\*/g, (_, m) => `<strong>${m}</strong>`);
        if (!line.trim()) return <div key={i} style={{ height: '6px' }} />;
        if (line.startsWith('## ')) return <h3 key={i} style={{ color: 'var(--accent-green)', fontWeight: '800', fontSize: '1rem', margin: '18px 0 8px', display: 'flex', alignItems: 'center', gap: '6px' }} dangerouslySetInnerHTML={{ __html: render(line.slice(3)) }} />;
        if (line.startsWith('# ')) return <h2 key={i} style={{ color: '#fff', fontWeight: '800', fontSize: '1.1rem', margin: '20px 0 10px' }} dangerouslySetInnerHTML={{ __html: render(line.slice(2)) }} />;
        if (line.startsWith('- ') || line.startsWith('• ')) return <div key={i} style={{ display: 'flex', gap: '8px', margin: '4px 0', color: 'var(--text-secondary)' }}><span style={{ color: 'var(--accent-green)', flexShrink: 0, marginTop: '2px' }}>•</span><span dangerouslySetInnerHTML={{ __html: render(line.slice(2)) }} /></div>;
        if (line.match(/^\d+\./)) return <div key={i} style={{ color: '#fff', fontWeight: '600', margin: '8px 0 4px' }} dangerouslySetInnerHTML={{ __html: render(line) }} />;
        return <p key={i} style={{ color: 'var(--text-secondary)', margin: '3px 0' }} dangerouslySetInnerHTML={{ __html: render(line) }} />;
      })}
    </div>
  );
}

export default function PortfolioAdvisor({ holdings, transactions, virtualBalance, livePrices, totalAssets, currency = '$' }) {
  const isUSD = currency === '$';
  const fmt = (n) => `${currency}${Math.abs(n).toLocaleString(isUSD ? 'en-US' : 'en-IN', { maximumFractionDigits: 0 })}`;
  const startingCapital = isUSD ? 100000 : 1000000;
  const startingCapitalStr = isUSD ? '$100,000' : '₹10,00,000';

  const [analysis, setAnalysis] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const portfolioValue = holdings.reduce((s, h) => s + h.quantity * (livePrices[h.ticker] || h.avgBuyPrice), 0);
  const totalInvested = holdings.reduce((s, h) => s + h.quantity * h.avgBuyPrice, 0);
  const unrealizedPnL = portfolioValue - totalInvested;
  const sellTxns = transactions.filter(t => t.type === 'SELL' && t.realizedPnL != null);
  const realizedPnL = sellTxns.reduce((s, t) => s + t.realizedPnL, 0);
  const winRate = sellTxns.length > 0 ? (sellTxns.filter(t => t.realizedPnL > 0).length / sellTxns.length * 100).toFixed(0) : 0;
  const overallReturn = ((totalAssets - startingCapital) / startingCapital * 100);

  const analyze = async () => {
    setLoading(true);
    setError('');
    const apiKey = import.meta.env.VITE_GEMINI_API_KEY;

    const holdingsText = holdings.length === 0
      ? 'No current holdings — all virtual cash is idle.'
      : holdings.map(h => {
          const lp = livePrices[h.ticker] || h.avgBuyPrice;
          const pnl = (lp - h.avgBuyPrice) * h.quantity;
          const pct = ((lp - h.avgBuyPrice) / h.avgBuyPrice * 100).toFixed(1);
          return `  • ${h.ticker} (${h.name}) | ${h.quantity} shares | Avg Buy ${currency}${h.avgBuyPrice.toFixed(2)} | Now ${currency}${lp.toFixed(2)} | P&L: ${currency}${pnl.toFixed(0)} (${pct}%) | Sector: ${h.sector}`;
        }).join('\n');

    const prompt = `You are a senior ${isUSD ? 'US' : 'Indian'} stock market portfolio advisor. Analyze this paper trading portfolio thoroughly and give expert advice.

═══ PORTFOLIO SNAPSHOT ═══
• Virtual Cash Available: ${fmt(virtualBalance)}
• Portfolio Value (holdings): ${fmt(portfolioValue)}
• Total Assets: ${fmt(totalAssets)}
• Starting Capital: ${startingCapitalStr}
• Overall Return: ${overallReturn >= 0 ? '+' : ''}${overallReturn.toFixed(2)}%
• Unrealized P&L: ${unrealizedPnL >= 0 ? '+' : ''}${fmt(unrealizedPnL)}
• Realized P&L: ${realizedPnL >= 0 ? '+' : ''}${fmt(realizedPnL)}
• Total Trades: ${transactions.length} (${transactions.filter(t => t.type === 'BUY').length} buys, ${sellTxns.length} sells)
• Win Rate: ${winRate}% (on completed sell trades)

═══ CURRENT HOLDINGS ═══
${holdingsText}

Provide a COMPLETE analysis with these sections:

## 1. Portfolio Health Score
Give a score out of 10 and a one-line verdict.

## 2. Diversification Analysis
Comment on sector spread, concentration risk, and balance.

## 3. Winners & Losers
Call out the best and worst performing positions specifically.

## 4. Risk Assessment
Evaluate the risk level. Is the portfolio too aggressive, too conservative, or well-balanced?

## 5. Specific Recommendations
Give 3-5 specific, actionable BUY / SELL / HOLD recommendations with reasons.

## 6. Cash Deployment Plan
The user has ${fmt(virtualBalance)} idle. Where should it go?

## 7. Top 3 Immediate Actions
Number them clearly. Be bold and specific.

Use ${isUSD ? 'US' : 'Indian'} market context. Keep it conversational, data-driven, and actionable.`;

    try {
      const res = await fetch(GEMINI_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-goog-api-key': apiKey },
        body: JSON.stringify({
          contents: [{ role: 'user', parts: [{ text: prompt }] }],
          generationConfig: { temperature: 0.7, maxOutputTokens: 8192 }
        })
      });
      const data = await res.json();
      const text = data?.candidates?.[0]?.content?.parts?.[0]?.text;
      if (!text) throw new Error('No response');
      setAnalysis(text);
    } catch {
      setError('Failed to get analysis. Check your internet connection and try again.');
    } finally {
      setLoading(false);
    }
  };

  const statCards = [
    { label: 'Holdings', value: holdings.length, sub: 'positions', icon: Target },
    { label: 'Unrealised P&L', value: `${unrealizedPnL >= 0 ? '+' : '-'}${fmt(unrealizedPnL)}`, color: unrealizedPnL >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', icon: unrealizedPnL >= 0 ? TrendingUp : TrendingDown },
    { label: 'Realised P&L', value: `${realizedPnL >= 0 ? '+' : '-'}${fmt(realizedPnL)}`, color: realizedPnL >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', icon: realizedPnL >= 0 ? TrendingUp : TrendingDown },
    { label: 'Win Rate', value: `${winRate}%`, sub: `${sellTxns.length} completed trades`, icon: ShieldAlert },
    { label: 'Overall Return', value: `${overallReturn >= 0 ? '+' : ''}${overallReturn.toFixed(2)}%`, color: overallReturn >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', icon: overallReturn >= 0 ? TrendingUp : TrendingDown },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

      {/* Header CTA */}
      <div className="glass-card" style={{ padding: '20px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', border: '1px solid rgba(16,185,129,0.2)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ width: '44px', height: '44px', borderRadius: '12px', background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <Bot size={22} color="var(--accent-green)" />
          </div>
          <div>
            <div style={{ fontWeight: '800', fontSize: '1.05rem', color: '#fff' }}>Portfolio AI Advisor</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Powered by Gemini AI • Analyzes your entire paper trading portfolio</div>
          </div>
        </div>
        <button onClick={analyze} disabled={loading} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '11px 22px', borderRadius: 'var(--radius-md)', fontWeight: '800', fontSize: '0.9rem', background: loading ? 'var(--bg-input)' : 'linear-gradient(135deg, #10b981, #059669)', border: 'none', color: '#fff', cursor: loading ? 'wait' : 'pointer', transition: 'all 0.2s', boxShadow: loading ? 'none' : '0 4px 20px rgba(16,185,129,0.3)' }}>
          {loading ? <RefreshCw size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <Sparkles size={16} />}
          {loading ? 'Analyzing Portfolio...' : analysis ? 'Re-Analyze' : 'Analyze My Portfolio'}
        </button>
      </div>

      {/* Quick stat cards */}
      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
        {statCards.map(s => (
          <div key={s.label} className="glass-card" style={{ flex: '1 1 130px', padding: '14px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{s.label}</span>
              {s.icon && <s.icon size={14} color={s.color || 'var(--text-muted)'} />}
            </div>
            <div style={{ fontWeight: '800', fontSize: '1.1rem', color: s.color || '#fff', fontFamily: 'var(--font-mono)' }}>{s.value}</div>
            {s.sub && <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '3px' }}>{s.sub}</div>}
          </div>
        ))}
      </div>

      {/* Empty state */}
      {!analysis && !loading && !error && (
        <div className="glass-card" style={{ padding: '64px 20px', textAlign: 'center' }}>
          <Lightbulb size={48} style={{ color: 'rgba(16,185,129,0.25)', marginBottom: '16px' }} />
          <div style={{ fontWeight: '800', color: '#fff', marginBottom: '8px', fontSize: '1.1rem' }}>Get Your Portfolio Reviewed by AI</div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.88rem', maxWidth: '400px', margin: '0 auto', lineHeight: '1.7' }}>
            Click <strong style={{ color: 'var(--accent-green)' }}>"Analyze My Portfolio"</strong> to receive a complete risk assessment, diversification analysis, and personalized stock recommendations from Gemini AI.
          </div>
        </div>
      )}

      {/* Error */}
      {error && <div className="glass-card" style={{ padding: '20px', border: '1px solid rgba(239,68,68,0.3)', color: '#f87171', textAlign: 'center', fontSize: '0.88rem' }}>{error}</div>}

      {/* AI Analysis Result */}
      {analysis && (
        <div className="glass-card" style={{ padding: '24px 28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px', paddingBottom: '16px', borderBottom: '1px solid var(--border-color)' }}>
            <Sparkles size={16} color="var(--accent-green)" />
            <span style={{ fontWeight: '700', color: 'var(--accent-green)', fontSize: '0.85rem' }}>AI Analysis Complete</span>
          </div>
          <RichText text={analysis} />
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
