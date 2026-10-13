import React from 'react';
import { Compass, ShieldCheck, Zap, TrendingUp, DollarSign, ArrowRight, CheckCircle2 } from 'lucide-react';
import { generatePortfolioRecommendation, formatCurrency } from '../utils/financialEngine';

export default function StrategyHub({ stocks, currency = '$', onApplyPortfolio, setActiveTab }) {
  const isUSD = currency === '$';

  const usStrategies = [
    {
      id: 'short-term-us',
      title: '1 to 3 Year Capital Safety & Bluechip Blueprint',
      subtitle: 'Low risk wealth preservation for short term goals and savings',
      horizon: 3,
      risk: 'Conservative',
      expectedCAGR: '8.5% - 10.5%',
      icon: ShieldCheck,
      color: 'var(--accent-green)',
      allocationText: '40% SPY, 20% BRK.B, 20% JNJ, 20% PG',
      description: 'Prioritizes liquidity and capital preservation while handily beating high-yield savings accounts.',
      highlights: [
        'Outperforms standard bank savings accounts & CDs',
        'Defensive anchor in Berkshire Hathaway and Johnson & Johnson',
        'S&P 500 foundation with minimal drawdown'
      ]
    },
    {
      id: 'medium-term-us',
      title: '3 to 7 Year S&P 500 & Tech Core Compounder',
      subtitle: 'The gold standard for medium-term American wealth creation',
      horizon: 5,
      risk: 'Moderate',
      expectedCAGR: '12.5% - 16.0%',
      icon: TrendingUp,
      color: 'var(--accent-blue)',
      allocationText: '35% SPY, 20% AAPL, 20% MSFT, 15% JPM, 10% AMZN',
      description: 'Designed for 5-year US equity compounding. Captures corporate America earnings growth across tech, enterprise software, and banking.',
      highlights: [
        'Strong exposure to mega-cap cashflow engines (Apple, Microsoft)',
        'Balanced financial anchor with JPMorgan Chase',
        'Optimized for automated monthly investment compounding'
      ]
    },
    {
      id: 'long-term-us',
      title: '7 to 15 Year Nasdaq 100 & AI Growth Blueprint',
      subtitle: 'Maximized capital growth targeting the frontier of artificial intelligence',
      horizon: 10,
      risk: 'Aggressive',
      expectedCAGR: '18.5% - 25.0%',
      icon: Zap,
      color: 'var(--accent-amber)',
      allocationText: '30% QQQ, 25% NVDA, 20% TSLA, 15% AMD, 10% META',
      description: 'Maximizes exponential compounding by investing in the world leaders of GPUs, AI hardware, electric mobility, and software platforms.',
      highlights: [
        'High CAGR momentum powered by Nvidia GPU dominance',
        'Nasdaq 100 benchmark capturing high-growth tech innovators',
        'Aggressive multi-year compounding potential'
      ]
    },
    {
      id: 'dividend-us',
      title: 'High Yield US Dividend & Cashflow Machine',
      subtitle: 'Generates predictable quarterly dividend payouts with dividend aristocrats',
      horizon: 7,
      risk: 'Income',
      expectedCAGR: '10.5% - 13.5%',
      icon: DollarSign,
      color: 'var(--accent-purple)',
      allocationText: '35% SCHD, 25% XOM, 20% JNJ, 10% KO, 10% PEP',
      description: 'Focuses on high dividend yield champions with decades of uninterrupted dividend growth and inflation protection.',
      highlights: [
        'Weighted dividend cash yield of ~3.5% - 4.0% annually',
        'Strong defensive moat during market pullbacks',
        'Automatic Dividend Reinvestment Plan (DRIP) compounding effect'
      ]
    }
  ];

  const indianStrategies = [
    {
      id: 'short-term-india',
      title: '1 to 3 Year Capital Safety & Gold Blueprint',
      subtitle: 'Low risk preservation for home down payment or emergency corpus in India',
      horizon: 3,
      risk: 'Conservative',
      expectedCAGR: '9.5% - 11.5%',
      icon: ShieldCheck,
      color: 'var(--accent-green)',
      allocationText: '35% NIFTYBEES, 20% GOLDBEES, 15% HDFCBANK, 15% ITC, 15% RELIANCE',
      description: 'Prioritizes liquidity, capital safety, and gold inflation hedge while easily outperforming standard Indian bank fixed deposits.',
      highlights: [
        'Outperforms FD interest rates after tax indexation benefits',
        'Physical gold hedge via GoldBEES for geopolitical stability',
        'Rock-solid Nifty 50 bluechip anchor'
      ]
    },
    {
      id: 'medium-term-india',
      title: '3 to 7 Year Balanced Indian Wealth Compounder',
      subtitle: 'The gold standard for medium-term Indian wealth creation',
      horizon: 5,
      risk: 'Moderate',
      expectedCAGR: '13.5% - 16.0%',
      icon: TrendingUp,
      color: 'var(--accent-blue)',
      allocationText: '35% NIFTYBEES, 20% RELIANCE, 15% TCS, 15% ICICIBANK, 15% BANKBEES',
      description: 'Designed for 5-year Indian equity market compounding. Captures corporate India earnings growth across banking, tech, and energy.',
      highlights: [
        'Strong alignment with India $5 Trillion GDP expansion story',
        'Combines private banking growth (ICICI, HDFC) with IT cashflow',
        'Automated SIP compound multiplier'
      ]
    },
    {
      id: 'long-term-india',
      title: '7 to 15 Year High Growth & Multibagger Blueprint',
      subtitle: 'Maximized capital growth for long-term Indian market compounding',
      horizon: 10,
      risk: 'Aggressive',
      expectedCAGR: '17.5% - 22.0%',
      icon: Zap,
      color: 'var(--accent-amber)',
      allocationText: '25% JUNIORBEES, 20% TATAMOTORS, 20% BAJFINANCE, 18% TCS, 17% MON100',
      description: 'Maximizes exponential compounding by focusing on high-growth Indian sectors: EV mobility, retail credit, IT services, and global tech (Nasdaq 100 in INR).',
      highlights: [
        'High CAGR momentum from Tata Motors EV and Bajaj Finance',
        'Nifty Next 50 exposure capturing future bluechips early',
        'Includes global tech diversification in INR (MON100)'
      ]
    },
    {
      id: 'dividend-india',
      title: 'High Yield Indian Dividend & Cashflow Machine',
      subtitle: 'Generates predictable dividend payouts from Indian cash cow PSUs & FMCG',
      horizon: 7,
      risk: 'Income',
      expectedCAGR: '11.5% - 13.5%',
      icon: DollarSign,
      color: 'var(--accent-purple)',
      allocationText: '30% COALINDIA, 25% ITC, 20% NTPC, 15% INFY, 10% HDFCBANK',
      description: 'Focuses on high dividend yield PSU monopolies (Coal India, NTPC) and FMCG cash cows (ITC) to generate passive quarterly dividend income.',
      highlights: [
        'Weighted dividend cash yield of ~4.2% annually',
        'Consistent dividend payouts backed by government PSU cashflows',
        'Dividend Reinvestment Plan (DRIP) compounding effect'
      ]
    }
  ];

  const activeStrategies = isUSD ? usStrategies : indianStrategies;

  const handleSelectStrategy = (strat) => {
    const defaultInitial = isUSD
      ? (strat.horizon === 3 ? 20000 : strat.horizon === 5 ? 50000 : 100000)
      : (strat.horizon === 3 ? 200000 : strat.horizon === 5 ? 500000 : 1000000);
    const defaultSIP = isUSD ? (strat.horizon === 3 ? 300 : 500) : (strat.horizon === 3 ? 3000 : 5000);

    const rec = generatePortfolioRecommendation(
      defaultInitial,
      defaultSIP,
      strat.horizon,
      strat.risk,
      strat.title,
      stocks
    );
    onApplyPortfolio(rec);
    setActiveTab('chartsheet');
  };

  return (
    <div style={{ maxWidth: '1300px', margin: '0 auto', padding: '24px 16px', display: 'flex', flexDirection: 'column', gap: '28px' }}>
      
      {/* Header */}
      <div className="glass-card" style={{ padding: '24px 28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-green)', fontWeight: '700', fontSize: '0.88rem' }}>
          <Compass size={18} />
          <span>{isUSD ? 'US' : 'INDIAN'} MARKET STRATEGY PLAYBOOKS</span>
        </div>
        <h2 style={{ fontSize: '1.75rem', marginTop: '4px' }}>Proven {isUSD ? 'US' : 'Indian'} Investment Blueprints</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem', marginTop: '2px' }}>
          Select an investment strategy playbook to simulate spend allocations, dividend payouts, and year-by-year financial chartsheets.
        </p>
      </div>

      {/* Grid of Strategy Playbooks */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '24px' }}>
        {activeStrategies.map((strat) => {
          const Icon = strat.icon;
          return (
            <div
              key={strat.id}
              className="glass-card"
              style={{
                padding: '28px',
                display: 'flex',
                flexDirection: 'column',
                justify: 'space-between',
                gap: '20px',
                borderTop: `4px solid ${strat.color}`
              }}
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ width: '44px', height: '44px', borderRadius: '12px', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Icon size={22} color={strat.color} />
                  </div>
                  <span className="badge badge-green">Target: {strat.horizon} Years</span>
                </div>

                <div>
                  <h3 style={{ fontSize: '1.25rem' }}>{strat.title}</h3>
                  <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)', marginTop: '4px' }}>{strat.subtitle}</p>
                </div>

                <div style={{ background: 'var(--bg-primary)', padding: '12px 16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.74rem', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: '600' }}>Expected Historical Return</div>
                  <div style={{ fontSize: '1.2rem', fontWeight: '800', color: strat.color, marginTop: '2px' }}>
                    {strat.expectedCAGR}
                  </div>
                </div>

                <p style={{ fontSize: '0.88rem', color: 'var(--text-main)', lineHeight: '1.6' }}>
                  {strat.description}
                </p>

                <div>
                  <div style={{ fontSize: '0.78rem', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>Target Allocation Mix</div>
                  <div style={{ fontSize: '0.84rem', color: '#ffffff', fontWeight: '600', background: 'var(--bg-input)', padding: '10px 14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                    {strat.allocationText}
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {strat.highlights.map((h, idx) => (
                    <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                      <CheckCircle2 size={14} color="var(--accent-green)" />
                      <span>{h}</span>
                    </div>
                  ))}
                </div>
              </div>

              <button
                onClick={() => handleSelectStrategy(strat)}
                className="btn btn-primary"
                style={{ width: '100%', marginTop: '12px' }}
              >
                <span>Load Strategy & Open Chartsheet</span>
                <ArrowRight size={16} />
              </button>
            </div>
          );
        })}
      </div>

    </div>
  );
}
