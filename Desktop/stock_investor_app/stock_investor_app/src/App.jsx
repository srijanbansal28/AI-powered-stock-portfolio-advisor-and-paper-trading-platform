import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Chatbot from './components/Chatbot';
import Planner from './components/Planner';
import ChartsheetHub from './components/ChartsheetHub';
import StockManager from './components/StockManager';
import StrategyHub from './components/StrategyHub';
import LoginPage from './components/LoginPage';
import PaperTrading from './components/PaperTrading';
import Leaderboard from './components/Leaderboard';

import { getStoredStocks, resetStockDatabase } from './data/stockDatabase';
import { generatePortfolioRecommendation } from './utils/financialEngine';

const USER_STORAGE_KEY = 'investiq_user_session';

export default function App() {
  const [currency, setCurrency] = useState('$');
  const [stocks, setStocks] = useState(() => getStoredStocks('$'));
  const [activeTab, setActiveTab] = useState('chat');
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem(USER_STORAGE_KEY);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [googleClientId, setGoogleClientId] = useState(
    (import.meta.env.VITE_GOOGLE_CLIENT_ID !== 'YOUR_GOOGLE_CLIENT_ID_HERE'
      ? import.meta.env.VITE_GOOGLE_CLIENT_ID
      : null) || localStorage.getItem('investiq_google_client_id') || ''
  );

  const [currentPortfolio, setCurrentPortfolio] = useState(() =>
    generatePortfolioRecommendation(
      currency === '$' ? 50000 : 500000,
      currency === '$' ? 500 : 5000,
      5,
      'Moderate',
      'Wealth Growth',
      getStoredStocks(currency)
    )
  );

  // Sync stocks & portfolio when currency / market changes
  useEffect(() => {
    const loadedStocks = getStoredStocks(currency);
    setStocks(loadedStocks);
    const isUSD = currency === '$';
    setCurrentPortfolio(
      generatePortfolioRecommendation(
        isUSD ? 50000 : 500000,
        isUSD ? 500 : 5000,
        5,
        'Moderate',
        'Wealth Growth',
        loadedStocks
      )
    );
  }, [currency]);

  const handleLogin = (userData) => {
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(userData));
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem(USER_STORAGE_KEY);
    setUser(null);
    if (window.google?.accounts?.id) {
      window.google.accounts.id.disableAutoSelect();
    }
  };

  const handleResetData = () => {
    const marketName = currency === '$' ? 'US' : 'Indian';
    if (confirm(`Reset ${marketName} stock database back to factory defaults?`)) {
      const reset = resetStockDatabase(currency);
      setStocks(reset);
      const isUSD = currency === '$';
      setCurrentPortfolio(
        generatePortfolioRecommendation(
          isUSD ? 50000 : 500000,
          isUSD ? 500 : 5000,
          5,
          'Moderate',
          'Wealth Growth',
          reset
        )
      );
    }
  };

  // Show Login page if not authenticated
  if (!user) {
    return (
      <LoginPage
        onLogin={handleLogin}
        onClientIdSave={(id) => setGoogleClientId(id)}
      />
    );
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg-primary)' }}>
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        currency={currency}
        setCurrency={setCurrency}
        onResetData={handleResetData}
        user={user}
        onLogout={handleLogout}
      />

      <main style={{ flex: 1, padding: '16px 0 40px 0' }}>
        {activeTab === 'chat' && (
          <Chatbot stocks={stocks} currency={currency} onApplyPortfolio={setCurrentPortfolio} setActiveTab={setActiveTab} user={user} />
        )}
        {activeTab === 'planner' && (
          <Planner stocks={stocks} currency={currency} currentPortfolio={currentPortfolio} onApplyPortfolio={setCurrentPortfolio} setActiveTab={setActiveTab} />
        )}
        {activeTab === 'chartsheet' && (
          <ChartsheetHub portfolio={currentPortfolio} currency={currency} />
        )}
        {activeTab === 'database' && (
          <StockManager stocks={stocks} setStocks={setStocks} onReset={handleResetData} currency={currency} />
        )}
        {activeTab === 'strategies' && (
          <StrategyHub stocks={stocks} currency={currency} onApplyPortfolio={setCurrentPortfolio} setActiveTab={setActiveTab} />
        )}
        {activeTab === 'paper' && (
          <PaperTrading stocks={stocks} user={user} currency={currency} />
        )}
        {activeTab === 'leaderboard' && (
          <Leaderboard user={user} currency={currency} />
        )}
      </main>

      <footer style={{ borderTop: '1px solid var(--border-color)', background: 'var(--bg-secondary)', padding: '18px 24px', textAlign: 'center', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
        Investwithsrijan AI {currency === '$' ? 'US' : 'Indian'} Stock Advisor • Market Analytics • Logged in as <strong style={{ color: '#fff' }}>{user.email}</strong>
      </footer>
    </div>
  );
}
