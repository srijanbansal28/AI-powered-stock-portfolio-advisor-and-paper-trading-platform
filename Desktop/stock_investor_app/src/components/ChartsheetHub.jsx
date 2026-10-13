import React, { useState } from 'react';
import { Table, Download, Copy, TrendingUp, PieChart, ShieldCheck, DollarSign, Check } from 'lucide-react';
import { formatCurrency } from '../utils/financialEngine';

export default function ChartsheetHub({ portfolio, currency }) {
  const [copied, setCopied] = useState(false);

  if (!portfolio) {
    return (
      <div style={{ maxWidth: '1200px', margin: '60px auto', textAlign: 'center', padding: '40px' }} className="glass-card">
        <h3>No active portfolio loaded</h3>
        <p style={{ color: 'var(--text-muted)', marginTop: '8px' }}>Please use the AI Chatbot or Investment Planner to generate a recommendation first.</p>
      </div>
    );
  }

  const {
    initialAmount,
    monthlySIP,
    horizonYears,
    riskProfile,
    goal,
    weightedCAGR,
    weightedDivYield,
    totalInvested,
    projectedFinalValue,
    conservativeFinalValue,
    optimisticFinalValue,
    netProfit,
    annualDividendIncomeProjected,
    allocations,
    sectorBreakdown,
    baseSchedule,
    consSchedule,
    optSchedule
  } = portfolio;

  // CSV Export logic
  const handleExportCSV = () => {
    let csv = "Year,Starting Balance,Annual Contribution,Total Invested,Interest Earned,Annual Dividend,End Balance,Cumulative Growth\n";
    baseSchedule.forEach(row => {
      csv += `${row.year},${row.startBalance},${row.annualContribution},${row.totalContributions},${row.interestEarned},${row.annualDividendIncome},${row.endBalance},${row.totalGrowth}\n`;
    });

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `Investwithsrijan_Investment_Chartsheet_${horizonYears}Y.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Copy to Clipboard logic
  const handleCopyTable = () => {
    let text = `Investwithsrijan Portfolio Summary (${horizonYears} Years - ${riskProfile})\n`;
    text += `Initial Capital: ${formatCurrency(initialAmount, currency)}\n`;
    text += `Monthly SIP: ${formatCurrency(monthlySIP, currency)}\n`;
    text += `Projected End Balance: ${formatCurrency(projectedFinalValue, currency)}\n\n`;
    text += `Year | Total Invested | Interest Earned | End Balance\n`;
    baseSchedule.forEach(r => {
      text += `Yr ${r.year} | ${formatCurrency(r.totalContributions, currency)} | ${formatCurrency(r.interestEarned, currency)} | ${formatCurrency(r.endBalance, currency)}\n`;
    });

    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Max value for visual bar scaling
  const maxEndVal = Math.max(...optSchedule.map(s => s.endBalance));

  return (
    <div style={{ maxWidth: '1350px', margin: '0 auto', padding: '24px 16px', display: 'flex', flexDirection: 'column', gap: '28px' }}>
      
      {/* Top Portfolio Header Card */}
      <div className="glass-card" style={{ padding: '24px 28px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="badge badge-green">{riskProfile} Profile</span>
            <span className="badge badge-blue">{horizonYears} Years Horizon</span>
            <span className="badge badge-purple">{goal}</span>
          </div>
          <h2 style={{ fontSize: '1.75rem', marginTop: '8px' }}>
            Investment Plan Chartsheet & Portfolio Analysis
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem', marginTop: '2px' }}>
            Detailed compound returns matrix, ticker spend breakdown, and multi-scenario asset trajectories.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button onClick={handleCopyTable} className="btn btn-secondary">
            {copied ? <Check size={18} color="var(--accent-green)" /> : <Copy size={18} />}
            <span>{copied ? 'Copied to Clipboard' : 'Copy Summary'}</span>
          </button>
          <button onClick={handleExportCSV} className="btn btn-primary">
            <Download size={18} />
            <span>Download CSV Chartsheet</span>
          </button>
        </div>
      </div>

      {/* Highlights Metrics Bar */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
        
        <div className="glass-card" style={{ padding: '20px' }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '600' }}>
            Initial Spend & Contributions
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: '800', color: '#ffffff', marginTop: '4px' }}>
            {formatCurrency(totalInvested, currency)}
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginTop: '4px' }}>
            {formatCurrency(initialAmount, currency)} lump sum + {formatCurrency(monthlySIP, currency)}/mo
          </div>
        </div>

        <div className="glass-card" style={{ padding: '20px', border: '1px solid var(--accent-green)' }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--accent-green)', textTransform: 'uppercase', fontWeight: '600' }}>
            Base Case Value ({horizonYears} Yrs)
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: '800', color: 'var(--accent-green)', marginTop: '4px' }}>
            {formatCurrency(projectedFinalValue, currency)}
          </div>
          <div style={{ fontSize: '0.78rem', color: '#34d399', fontWeight: '600', marginTop: '4px' }}>
            Net Growth: {formatCurrency(netProfit, currency)} ({weightedCAGR}% CAGR)
          </div>
        </div>

        <div className="glass-card" style={{ padding: '20px' }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '600' }}>
            Optimistic Case (+3.5%)
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: '800', color: 'var(--accent-amber)', marginTop: '4px' }}>
            {formatCurrency(optimisticFinalValue, currency)}
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginTop: '4px' }}>
            {(weightedCAGR + 3.5).toFixed(1)}% annual rate
          </div>
        </div>

        <div className="glass-card" style={{ padding: '20px' }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '600' }}>
            Est. Annual Dividend Income
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: '800', color: 'var(--accent-purple)', marginTop: '4px' }}>
            {formatCurrency(annualDividendIncomeProjected, currency)}/yr
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginTop: '4px' }}>
            {weightedDivYield}% weighted yield
          </div>
        </div>

      </div>

      {/* Visual Multi-Scenario Compound Growth Visualizer */}
      <div className="glass-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <h3 style={{ fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <TrendingUp size={20} color="var(--accent-green)" />
            <span>Multi-Scenario Portfolio Trajectory ({horizonYears} Years)</span>
          </h3>

          <div style={{ display: 'flex', gap: '16px', fontSize: '0.82rem', fontWeight: '600' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '12px', height: '12px', background: 'var(--accent-green)', borderRadius: '3px' }}></span>
              <span>Expected Base ({weightedCAGR}%)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '12px', height: '12px', background: 'var(--accent-amber)', borderRadius: '3px' }}></span>
              <span>Optimistic ({(weightedCAGR + 3.5).toFixed(1)}%)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '12px', height: '12px', background: 'var(--accent-blue)', borderRadius: '3px' }}></span>
              <span>Total Principal Invested</span>
            </div>
          </div>
        </div>

        {/* Visual Bar Timeline chart representation */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '8px' }}>
          {baseSchedule.map((row, idx) => {
            const optVal = optSchedule[idx]?.endBalance || row.endBalance;
            const consVal = consSchedule[idx]?.endBalance || row.endBalance;

            const basePercent = Math.min(100, Math.round((row.endBalance / maxEndVal) * 100));
            const optPercent = Math.min(100, Math.round((optVal / maxEndVal) * 100));
            const principalPercent = Math.min(100, Math.round((row.totalContributions / maxEndVal) * 100));

            return (
              <div key={row.year} style={{ display: 'grid', gridTemplateColumns: '60px 1fr 140px', alignItems: 'center', gap: '14px' }}>
                <div style={{ fontSize: '0.85rem', fontWeight: '700', color: 'var(--text-muted)' }}>
                  Year {row.year}
                </div>

                <div style={{ position: 'relative', height: '26px', background: 'var(--bg-primary)', borderRadius: '6px', overflow: 'hidden', border: '1px solid var(--border-color)' }}>
                  {/* Optimistic Shadow */}
                  <div style={{ position: 'absolute', top: 0, left: 0, bottom: 0, width: `${optPercent}%`, background: 'rgba(245, 158, 11, 0.25)', transition: 'width 0.5s ease' }}></div>
                  {/* Base Case Bar */}
                  <div style={{ position: 'absolute', top: 0, left: 0, bottom: 0, width: `${basePercent}%`, background: 'linear-gradient(90deg, #059669 0%, #10b981 100%)', borderRadius: '6px', transition: 'width 0.5s ease' }}></div>
                  {/* Principal Bar overlay */}
                  <div style={{ position: 'absolute', top: '4px', left: 0, bottom: '4px', width: `${principalPercent}%`, background: 'var(--accent-blue)', opacity: 0.6, borderRadius: '4px' }}></div>
                </div>

                <div style={{ fontSize: '0.88rem', fontWeight: '700', color: '#ffffff', textAlign: 'right' }}>
                  {formatCurrency(row.endBalance, currency)}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Asset Spend Breakdown Cards */}
      <div className="glass-card" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '1.1rem', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <PieChart size={20} color="var(--accent-green)" />
          <span>Exact Stock Purchase Breakdown & Recommended Holdings</span>
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
          {allocations.map((alloc) => (
            <div key={alloc.ticker} style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '18px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ fontSize: '1.1rem', fontWeight: '800', color: '#ffffff' }}>{alloc.ticker}</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{alloc.name}</div>
                </div>
                <span className="badge badge-green">{alloc.weightPercentage}% Split</span>
              </div>

              <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '10px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Amount to Spend</div>
                  <div style={{ fontSize: '1.05rem', fontWeight: '800', color: 'var(--accent-green)' }}>
                    {formatCurrency(alloc.spendAmount, currency)}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Est. Share Quantity</div>
                  <div style={{ fontSize: '1.05rem', fontWeight: '700', color: '#ffffff' }}>
                    {alloc.sharesToBuy} units
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                <span>Unit Price: ${alloc.price}</span>
                <span>Expected CAGR: {alloc.cagr}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Complete Year-by-Year Compound Schedule Table ("Chartsheet") */}
      <div className="glass-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Table size={20} color="var(--accent-green)" />
            <span>Complete Multi-Year Investment Growth Matrix ("Chartsheet")</span>
          </h3>
          <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Compounded Monthly @ {weightedCAGR}% CAGR</span>
        </div>

        <div className="custom-table-container">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Timeline Year</th>
                <th>Starting Balance</th>
                <th>Annual Contribution</th>
                <th>Total Invested</th>
                <th>Compound Growth Earned</th>
                <th>Est. Dividend Income</th>
                <th>Ending Balance</th>
                <th>Total Profit</th>
              </tr>
            </thead>
            <tbody>
              {baseSchedule.map((row) => (
                <tr key={row.year}>
                  <td style={{ fontWeight: '700', color: 'var(--accent-green)' }}>Year {row.year}</td>
                  <td>{formatCurrency(row.startBalance, currency)}</td>
                  <td>{formatCurrency(row.annualContribution, currency)}</td>
                  <td style={{ color: 'var(--text-muted)' }}>{formatCurrency(row.totalContributions, currency)}</td>
                  <td style={{ color: 'var(--accent-amber)', fontWeight: '600' }}>+ {formatCurrency(row.interestEarned, currency)}</td>
                  <td style={{ color: 'var(--accent-purple)' }}>{formatCurrency(row.annualDividendIncome, currency)}</td>
                  <td style={{ fontWeight: '800', color: '#ffffff' }}>{formatCurrency(row.endBalance, currency)}</td>
                  <td style={{ color: '#34d399', fontWeight: '700' }}>+ {formatCurrency(row.totalGrowth, currency)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
