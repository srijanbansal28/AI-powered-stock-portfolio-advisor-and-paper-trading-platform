import React, { useState, useEffect } from 'react';
import { Sliders, Shield, TrendingUp, Calendar, DollarSign, PieChart, ArrowRight, Layers, Sparkles } from 'lucide-react';
import { generatePortfolioRecommendation, formatCurrency } from '../utils/financialEngine';

export default function Planner({ stocks, currency, currentPortfolio, onApplyPortfolio, setActiveTab }) {
  const [initialAmount, setInitialAmount] = useState(currentPortfolio?.initialAmount || 50000);
  const [monthlySIP, setMonthlySIP] = useState(currentPortfolio?.monthlySIP || 500);
  const [horizonYears, setHorizonYears] = useState(currentPortfolio?.horizonYears || 5);
  const [riskProfile, setRiskProfile] = useState(currentPortfolio?.riskProfile || 'Moderate');
  const [goal, setGoal] = useState(currentPortfolio?.goal || 'Wealth Growth');

  const [recommendation, setRecommendation] = useState(
    currentPortfolio || generatePortfolioRecommendation(50000, 500, 5, 'Moderate', 'Wealth Growth', stocks)
  );

  useEffect(() => {
    const rec = generatePortfolioRecommendation(initialAmount, monthlySIP, horizonYears, riskProfile, goal, stocks);
    setRecommendation(rec);
  }, [initialAmount, monthlySIP, horizonYears, riskProfile, goal, stocks]);

  const handleApply = () => {
    onApplyPortfolio(recommendation);
    setActiveTab('chartsheet');
  };

  return (
    <div style={{ maxWidth: '1300px', margin: '0 auto', padding: '24px 16px', display: 'flex', flexDirection: 'column', gap: '28px' }}>
      
      {/* Top Banner Header */}
      <div className="glass-card" style={{ padding: '24px 28px', background: 'linear-gradient(135deg, var(--bg-card) 0%, var(--bg-secondary) 100%)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-green)', fontWeight: '700', fontSize: '0.88rem' }}>
            <Sliders size={18} />
            <span>{currency === '$' ? 'US' : 'INDIAN'} MARKET FINANCIAL WORKBENCH</span>
          </div>
          <h2 style={{ fontSize: '1.75rem', marginTop: '4px' }}>{currency === '$' ? 'US' : 'Indian'} Stock Portfolio & SIP Planner</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem', marginTop: '4px' }}>
            Adjust your time horizon, lump-sum budget, and monthly SIP to compute stock allocation and wealth growth.
          </p>
        </div>

        <button onClick={handleApply} className="btn btn-primary" style={{ padding: '12px 24px', fontSize: '0.95rem' }}>
          <span>Generate Full Chartsheet</span>
          <ArrowRight size={18} />
        </button>
      </div>

      {/* Main Grid: Controls vs Realtime Results */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '24px' }}>
        
        {/* Controls Column */}
        <div className="glass-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <h3 style={{ fontSize: '1.1rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Layers size={18} color="var(--accent-green)" />
            <span>Investment Parameters</span>
          </h3>

          {/* Initial Budget Input */}
          <div className="input-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label className="input-label">Initial Lump-Sum Spend ({currency})</label>
              <span style={{ fontWeight: '700', color: 'var(--accent-green)', fontSize: '1rem' }}>
                {formatCurrency(initialAmount, currency)}
              </span>
            </div>
            <input
              type="range"
              min="10000"
              max="10000000"
              step="10000"
              value={initialAmount}
              onChange={(e) => setInitialAmount(Number(e.target.value))}
              style={{ accentColor: 'var(--accent-green)', cursor: 'pointer' }}
            />
            <input
              type="number"
              className="input-field"
              value={initialAmount}
              onChange={(e) => setInitialAmount(Math.max(0, Number(e.target.value)))}
              style={{ marginTop: '6px' }}
            />
          </div>

          {/* Monthly SIP Input */}
          <div className="input-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label className="input-label">Monthly SIP Contribution ({currency}/mo)</label>
              <span style={{ fontWeight: '700', color: 'var(--accent-blue)', fontSize: '1rem' }}>
                {formatCurrency(monthlySIP, currency)}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="200000"
              step="1000"
              value={monthlySIP}
              onChange={(e) => setMonthlySIP(Number(e.target.value))}
              style={{ accentColor: 'var(--accent-blue)', cursor: 'pointer' }}
            />
            <input
              type="number"
              className="input-field"
              value={monthlySIP}
              onChange={(e) => setMonthlySIP(Math.max(0, Number(e.target.value)))}
              style={{ marginTop: '6px' }}
            />
          </div>

          {/* Horizon Years Slider */}
          <div className="input-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label className="input-label">Investment Horizon (Years)</label>
              <span style={{ fontWeight: '800', color: 'var(--accent-amber)', fontSize: '1.1rem' }}>
                {horizonYears} {horizonYears === 1 ? 'Year' : 'Years'}
              </span>
            </div>
            <input
              type="range"
              min="1"
              max="30"
              step="1"
              value={horizonYears}
              onChange={(e) => setHorizonYears(Number(e.target.value))}
              style={{ accentColor: 'var(--accent-amber)', cursor: 'pointer' }}
            />
          </div>

          {/* Risk Level Selector */}
          <div className="input-group">
            <label className="input-label">Risk Tolerance Profile</label>
            <select
              className="select-field"
              value={riskProfile}
              onChange={(e) => setRiskProfile(e.target.value)}
            >
              <option value="Conservative">{currency === '$' ? 'Conservative (SPY, TLT & JNJ)' : 'Conservative (NiftyBEES & GoldBEES)'}</option>
              <option value="Moderate">{currency === '$' ? 'Moderate (S&P 500, Apple, Microsoft & JPM)' : 'Moderate (Nifty 50, Reliance & TCS)'}</option>
              <option value="Aggressive">{currency === '$' ? 'Aggressive (Nasdaq 100, Tesla & Nvidia)' : 'Aggressive (JuniorBEES, Tata Motors & L&T)'}</option>
              <option value="Very Aggressive">{currency === '$' ? 'Very Aggressive (Multibaggers & High Growth)' : 'Very Aggressive (Midcap Multibaggers & Tech)'}</option>
              <option value="Income">{currency === '$' ? 'High Dividend Income Engine (SCHD, XOM, JNJ)' : 'High Dividend PSU & Cashflow Engine (ITC, Coal India)'}</option>
            </select>
          </div>

          {/* Goal Selector */}
          <div className="input-group">
            <label className="input-label">Primary Financial Objective</label>
            <select
              className="select-field"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
            >
              <option value="Wealth Growth">Long-Term Wealth Compounding</option>
              <option value="Retirement">Retirement Corpus Building</option>
              <option value="Passive Income">Passive Dividend Income Flow</option>
              <option value="Capital Preservation">Capital Protection & Safety</option>
            </select>
          </div>
        </div>

        {/* Real-time Results & Spend Allocation Summary */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Key Stat Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
            
            <div className="glass-card" style={{ padding: '20px' }}>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '600' }}>
                Total Invested Capital
              </div>
              <div style={{ fontSize: '1.4rem', fontWeight: '800', color: '#ffffff', marginTop: '4px' }}>
                {formatCurrency(recommendation.totalInvested, currency)}
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                {formatCurrency(initialAmount, currency)} initial + {formatCurrency(monthlySIP * 12 * horizonYears, currency)} SIP
              </div>
            </div>

            <div className="glass-card" style={{ padding: '20px', border: '1px solid var(--accent-green)' }}>
              <div style={{ fontSize: '0.78rem', color: 'var(--accent-green)', textTransform: 'uppercase', fontWeight: '600' }}>
                {horizonYears}-Year Projected Portfolio Value
              </div>
              <div style={{ fontSize: '1.4rem', fontWeight: '800', color: 'var(--accent-green)', marginTop: '4px' }}>
                {formatCurrency(recommendation.projectedFinalValue, currency)}
              </div>
              <div style={{ fontSize: '0.78rem', color: '#34d399', fontWeight: '600', marginTop: '4px' }}>
                + {formatCurrency(recommendation.netProfit, currency)} profit ({((recommendation.netProfit / Math.max(1, recommendation.totalInvested)) * 100).toFixed(0)}%)
              </div>
            </div>

          </div>

          {/* Allocation & Spend Table Card */}
          <div className="glass-card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h4 style={{ fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <PieChart size={18} color="var(--accent-green)" />
                <span>Recommended Stock Allocation & Spend</span>
              </h4>
              <span className="badge badge-green">Weighted CAGR: {recommendation.weightedCAGR}%</span>
            </div>

            <div className="custom-table-container">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Stock / ETF</th>
                    <th>Sector</th>
                    <th>Allocation</th>
                    <th>How Much to Spend</th>
                    <th>Est. Shares</th>
                  </tr>
                </thead>
                <tbody>
                  {recommendation.allocations.map((alloc) => (
                    <tr key={alloc.ticker}>
                      <td>
                        <div style={{ fontWeight: '700', color: '#ffffff' }}>{alloc.ticker}</div>
                        <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>{alloc.name}</div>
                      </td>
                      <td><span className="badge badge-blue">{alloc.sector}</span></td>
                      <td style={{ fontWeight: '700', color: 'var(--accent-green)' }}>{alloc.weightPercentage}%</td>
                      <td style={{ fontWeight: '700', color: '#ffffff' }}>{formatCurrency(alloc.spendAmount, currency)}</td>
                      <td style={{ color: 'var(--text-muted)' }}>{alloc.sharesToBuy} units</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '8px' }}>
              <button onClick={handleApply} className="btn btn-outline" style={{ width: '100%' }}>
                <span>View Complete Year-by-Year Compound Matrix</span>
                <ArrowRight size={16} />
              </button>
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}
