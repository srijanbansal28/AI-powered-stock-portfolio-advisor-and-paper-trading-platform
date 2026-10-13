import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Send, Bot, User, Sparkles, ArrowRight, Trash2, Copy, Check,
  AlertCircle, Key, ExternalLink, ChevronDown, TrendingUp
} from 'lucide-react';
import { callGeminiAPI } from '../utils/geminiService';
import { generatePortfolioRecommendation, formatCurrency } from '../utils/financialEngine';

// Renders markdown-like text with bold, tables and line breaks
function RichText({ text }) {
  if (!text) return null;

  // Render markdown table if found
  const renderTable = (tableLines) => {
    const rows = tableLines
      .filter(line => line.trim().startsWith('|') && !line.match(/^\|[-| :]+\|$/))
      .map(line =>
        line.trim().split('|').filter((_, i, a) => i > 0 && i < a.length - 1).map(c => c.trim())
      );

    if (rows.length === 0) return null;
    const [header, ...body] = rows;

    return (
      <div className="custom-table-container" style={{ marginTop: '10px', marginBottom: '10px' }}>
        <table className="custom-table">
          <thead>
            <tr>{header.map((h, i) => <th key={i}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {body.map((row, ri) => (
              <tr key={ri}>
                {row.map((cell, ci) => {
                  const isAmount = cell.includes('₹') || cell.includes('%');
                  return (
                    <td key={ci} style={{ color: isAmount ? 'var(--accent-green)' : undefined, fontWeight: isAmount ? '700' : undefined }}>
                      {cell}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  const lines = text.split('\n');
  const elements = [];
  let tableBuffer = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    
    // Collect table lines
    if (line.trim().startsWith('|')) {
      tableBuffer.push(line);
      i++;
      continue;
    } else if (tableBuffer.length > 0) {
      const tableEl = renderTable(tableBuffer);
      if (tableEl) elements.push(<div key={`table-${i}`}>{tableEl}</div>);
      tableBuffer = [];
    }

    if (!line.trim()) {
      elements.push(<br key={i} />);
    } else if (line.startsWith('## ')) {
      elements.push(<div key={i} style={{ fontWeight: '700', fontSize: '1rem', color: '#ffffff', marginTop: '12px', marginBottom: '4px' }}>{line.slice(3)}</div>);
    } else if (line.startsWith('### ')) {
      elements.push(<div key={i} style={{ fontWeight: '700', fontSize: '0.92rem', color: 'var(--accent-green)', marginTop: '10px', marginBottom: '4px' }}>{line.slice(4)}</div>);
    } else if (line.startsWith('- ') || line.startsWith('* ')) {
      const content = formatInlineMarkdown(line.slice(2));
      elements.push(
        <div key={i} style={{ display: 'flex', gap: '8px', alignItems: 'flex-start', marginBottom: '4px' }}>
          <span style={{ color: 'var(--accent-green)', marginTop: '2px', flexShrink: 0 }}>▸</span>
          <span style={{ fontSize: '0.93rem', lineHeight: '1.6' }}>{content}</span>
        </div>
      );
    } else if (/^\d+\. /.test(line)) {
      const num = line.match(/^(\d+)\. /)[1];
      const content = formatInlineMarkdown(line.replace(/^\d+\. /, ''));
      elements.push(
        <div key={i} style={{ display: 'flex', gap: '8px', alignItems: 'flex-start', marginBottom: '4px' }}>
          <span style={{ color: 'var(--accent-green)', fontWeight: '700', flexShrink: 0, minWidth: '18px' }}>{num}.</span>
          <span style={{ fontSize: '0.93rem', lineHeight: '1.6' }}>{content}</span>
        </div>
      );
    } else {
      elements.push(<div key={i} style={{ fontSize: '0.93rem', lineHeight: '1.65', marginBottom: '4px' }}>{formatInlineMarkdown(line)}</div>);
    }
    i++;
  }

  if (tableBuffer.length > 0) {
    const tableEl = renderTable(tableBuffer);
    if (tableEl) elements.push(<div key="final-table">{tableEl}</div>);
  }

  return <div>{elements}</div>;
}

function formatInlineMarkdown(text) {
  // Split on bold (**text**) and render as JSX spans
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={idx} style={{ color: '#ffffff', fontWeight: '700' }}>{part.slice(2, -2)}</strong>;
    }
    // Highlight ₹/$ amounts
    if (part.includes('₹') || part.includes('$')) {
      return <span key={idx} style={{ color: '#f9fafb' }}>{part}</span>;
    }
    return part;
  });
}

export default function Chatbot({ stocks, currency = '$', onApplyPortfolio, setActiveTab, user }) {
  const firstName = user?.name?.split(' ')[0] || 'there';
  const isUSD = currency === '$';

  const getWelcomeText = () => isUSD ? `Hello, **${firstName}**! 👋 I'm **Investwithsrijan** — your personal US stock market advisor powered by Gemini AI.

I'm trained on US market dynamics, S&P 500/Nasdaq stocks, investing strategies, tax rules (Long/Short term capital gains, 401k, IRA), and portfolio building for the American investor.

**You can ask me anything**, for example:
- *"I have $50,000 to invest for 5 years, what should I buy?"*
- *"Is Apple a good buy right now?"*
- *"Explain Index Funds vs Individual Stocks for a beginner"*
- *"Compare SPY vs QQQ"*
- *"What happens to my $10,000 in SPY after 10 years?"*
- *"Is it better to invest in stocks or bonds?"*

Tell me your budget, goal, and time horizon — I'll build your complete investment plan! 📈` : `Namaste, **${firstName}**! 🙏 I'm **Investwithsrijan** — your personal Indian stock market advisor powered by Gemini AI.

I'm trained on Indian market dynamics, NSE/BSE stocks, SIP strategies, tax rules (LTCG/STCG, ELSS 80C), and portfolio building for the Indian investor.

**You can ask me anything**, for example:
- *"I have ₹5 Lakhs to invest for 5 years, what should I buy?"*
- *"Is Reliance a good buy right now?"*
- *"Explain SIP vs Lump Sum for a beginner"*
- *"Compare NiftyBEES vs JuniorBEES"*
- *"What happens to my ₹1 Lakh in NIFTYBEES after 10 years?"*
- *"Is it better to invest in stocks or PPF?"*

Tell me your budget, goal, and time horizon — I'll build your complete investment plan! 📈`;

  const [messages, setMessages] = useState(() => [
    {
      id: 'welcome',
      role: 'model',
      text: getWelcomeText(),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);

  // Update welcome message if conversation is fresh and currency changed
  useEffect(() => {
    setMessages(prev => {
      if (prev.length === 1 && prev[0].id === 'welcome') {
        return [{
          id: 'welcome',
          role: 'model',
          text: getWelcomeText(),
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }];
      }
      return prev;
    });
  }, [currency]);

  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [apiKeyError, setApiKeyError] = useState(false);
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [savedKey, setSavedKey] = useState(import.meta.env.VITE_GEMINI_API_KEY || '');
  const [copied, setCopied] = useState(false);
  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  const quickPrompts = isUSD ? [
    "I have $50,000 to invest for 5 years, moderate risk. Where should I invest?",
    "Suggest a good dividend income portfolio with $20,000 for 7 years",
    "Best aggressive stocks for $100,000 over 10 years",
    "Explain Index Funds vs Individual Stocks in simple terms",
    "Is Microsoft a better investment than Apple right now?",
    "How much will $10,000 grow in SPY after 15 years?"
  ] : [
    "I have ₹5 Lakhs to invest for 5 years, moderate risk. Where should I invest?",
    "Suggest a good dividend income portfolio with ₹2 Lakhs for 7 years",
    "Best aggressive stocks for ₹10 Lakhs over 10 years",
    "Explain SIP vs Lump Sum investment in simple terms",
    "Is Reliance a better investment than TCS right now?",
    "How much will ₹1,00,000 grow in NiftyBEES after 15 years?"
  ];

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const buildConversationHistory = useCallback((msgs) => {
    // Convert messages (skip the initial welcome if model) to Gemini history format
    return msgs
      .filter(m => m.id !== 'welcome')
      .map(m => ({
        role: m.role === 'model' ? 'model' : 'user',
        text: m.text.replace(/\*\*/g, '') // strip markdown for API context
      }));
  }, []);

  const handleSendMessage = useCallback(async (textToSend) => {
    const query = (textToSend || input).trim();
    if (!query || isLoading) return;

    const userMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setInput('');
    setIsLoading(true);
    setApiKeyError(false);

    try {
      const history = buildConversationHistory(updatedMessages);
      const responseText = await callGeminiAPI(history, stocks, currency);

      // Detect if the response contains a portfolio recommendation to parse
      let recommendation = null;
      const hasPortfolioKeywords = responseText.toLowerCase().includes('allocation') && 
        (responseText.includes('$') || responseText.includes('₹') || responseText.includes('%')) &&
        responseText.includes('|');

      if (hasPortfolioKeywords) {
        // Try to extract budget/years/risk from conversation to build chartsheet data
        const fullContext = query + ' ' + responseText;
        const dollarMatch = fullContext.match(/\$\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:k|m)?/i);
        const lakhMatch = fullContext.match(/(\d+(?:\.\d+)?)\s*(?:lakhs?|lacs?)/i);
        const crMatch = fullContext.match(/(\d+(?:\.\d+)?)\s*(?:crores?|cr)/i);
        const yearsMatch = fullContext.match(/(\d+)\s*(?:years?|yrs?)/i);
        const isAggressive = fullContext.toLowerCase().includes('aggressive');
        const isConservative = fullContext.toLowerCase().includes('conservative');
        const isDividend = fullContext.toLowerCase().includes('dividend');

        let budget = isUSD ? 50000 : 500000;
        if (crMatch) budget = parseFloat(crMatch[1]) * 10000000;
        else if (lakhMatch) budget = parseFloat(lakhMatch[1]) * 100000;
        else if (dollarMatch) {
          let val = parseFloat(dollarMatch[1].replace(/,/g, ''));
          if (dollarMatch[0].toLowerCase().includes('k')) val *= 1000;
          if (dollarMatch[0].toLowerCase().includes('m')) val *= 1000000;
          budget = val;
        }

        const years = yearsMatch ? Math.min(30, parseInt(yearsMatch[1])) : 5;
        const risk = isAggressive ? 'Aggressive' : isConservative ? 'Conservative' : isDividend ? 'Income' : 'Moderate';

        recommendation = generatePortfolioRecommendation(budget, isUSD ? 500 : 5000, years, risk, 'Investment Growth', stocks);
      }

      const aiMsg = {
        id: `ai-${Date.now()}`,
        role: 'model',
        text: responseText,
        recommendation,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages(prev => [...prev, aiMsg]);
    } catch (err) {
      if (err.message === 'MISSING_API_KEY') {
        setApiKeyError(true);
        setMessages(prev => prev.filter(m => m.id !== userMsg.id));
        setInput(query);
      } else {
        const errMsg = {
          id: `err-${Date.now()}`,
          role: 'model',
          text: `⚠️ Error reaching AI: ${err.message}. Please check your API key or network connection and try again.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        setMessages(prev => [...prev, errMsg]);
      }
    } finally {
      setIsLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [input, isLoading, messages, stocks, buildConversationHistory]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleClearChat = () => {
    setMessages([messages[0]]); // Keep welcome message
    setApiKeyError(false);
  };

  const handleCopyLast = () => {
    const lastAI = [...messages].reverse().find(m => m.role === 'model' && m.id !== 'welcome');
    if (lastAI) {
      navigator.clipboard.writeText(lastAI.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleSaveKey = () => {
    if (apiKeyInput.trim()) {
      // Write key to localStorage for session persistence (user typed it in)
      localStorage.setItem('investiq_gemini_key', apiKeyInput.trim());
      setSavedKey(apiKeyInput.trim());
      setApiKeyError(false);
      setApiKeyInput('');
    }
  };

  // Check localStorage for key saved in a previous session
  useEffect(() => {
    const stored = localStorage.getItem('investiq_gemini_key');
    if (stored && (!savedKey || savedKey === 'your_gemini_api_key_here')) {
      setSavedKey(stored);
    }
  }, []);

  // Override the API call to use localStorage key if env key is missing
  useEffect(() => {
    if (savedKey && savedKey !== 'your_gemini_api_key_here') {
      // Patch the env resolution fallback
      window.__INVESTIQ_GEMINI_KEY__ = savedKey;
    }
  }, [savedKey]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '1200px', margin: '0 auto', padding: '24px 16px' }}>

      {/* API Key Error Banner */}
      {apiKeyError && (
        <div className="glass-card animate-fade-in" style={{ padding: '20px 24px', border: '1px solid var(--accent-amber)', background: 'rgba(245, 158, 11, 0.06)' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', marginBottom: '14px' }}>
            <Key size={20} color="var(--accent-amber)" style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>
              <div style={{ fontWeight: '700', color: 'var(--accent-amber)', marginBottom: '4px' }}>Gemini API Key Required</div>
              <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)', lineHeight: '1.5' }}>
                Paste your Google Gemini API key below to enable the AI chatbot. Get a free key at{' '}
                <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer"
                  style={{ color: 'var(--accent-green)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                  aistudio.google.com/app/apikey <ExternalLink size={12} />
                </a>
              </p>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <input
              type="text"
              className="input-field"
              placeholder="AIzaSy...paste your Gemini API key here"
              value={apiKeyInput}
              onChange={e => setApiKeyInput(e.target.value)}
              style={{ flex: 1 }}
            />
            <button
              onClick={handleSaveKey}
              className="btn btn-primary"
              disabled={!apiKeyInput.trim()}
            >
              <Key size={16} />
              <span>Save & Enable AI</span>
            </button>
          </div>
          <p style={{ fontSize: '0.76rem', color: 'var(--text-dim)', marginTop: '8px' }}>
            Your key is stored locally in your browser and never sent anywhere except directly to Google's API.
          </p>
        </div>
      )}

      {/* Quick Prompts */}
      <div className="glass-card" style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.82rem', fontWeight: '700', color: 'var(--text-muted)' }}>
          <Sparkles size={15} color="var(--accent-green)" />
          <span>QUICK QUESTIONS — click to ask instantly</span>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {quickPrompts.map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => handleSendMessage(prompt)}
              disabled={isLoading}
              style={{
                background: 'var(--bg-input)',
                border: '1px solid var(--border-color)',
                color: isLoading ? 'var(--text-dim)' : 'var(--text-main)',
                padding: '7px 14px',
                borderRadius: 'var(--radius-full)',
                fontSize: '0.82rem',
                fontWeight: '500',
                cursor: isLoading ? 'not-allowed' : 'pointer',
                transition: 'all 0.2s ease',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
              onMouseEnter={(e) => {
                if (!isLoading) {
                  e.currentTarget.style.borderColor = 'var(--accent-green)';
                  e.currentTarget.style.background = 'var(--bg-card-hover)';
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-color)';
                e.currentTarget.style.background = 'var(--bg-input)';
              }}
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>

      {/* Chat Window */}
      <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', minHeight: '560px', maxHeight: '720px', overflow: 'hidden' }}>
        
        {/* Chat Header */}
        <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border-color)', background: 'var(--bg-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: isLoading ? 'var(--accent-amber)' : 'var(--accent-green)', boxShadow: `0 0 8px ${isLoading ? 'var(--accent-amber)' : 'var(--accent-green)'}`, transition: 'all 0.3s' }}></div>
            <span style={{ fontWeight: '700', color: '#ffffff' }}>Investwithsrijan — Indian Market Advisor</span>
            <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)', background: 'var(--bg-input)', padding: '3px 8px', borderRadius: 'var(--radius-full)', border: '1px solid var(--border-color)' }}>
              Powered by Gemini AI
            </span>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={handleCopyLast}
              title="Copy last response"
              style={{ background: 'transparent', border: '1px solid var(--border-color)', color: 'var(--text-muted)', padding: '6px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            >
              {copied ? <Check size={15} color="var(--accent-green)" /> : <Copy size={15} />}
            </button>
            <button
              onClick={handleClearChat}
              title="Clear chat history"
              style={{ background: 'transparent', border: '1px solid var(--border-color)', color: 'var(--text-muted)', padding: '6px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            >
              <Trash2 size={15} />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px 20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {messages.map((msg) => (
            <div
              key={msg.id}
              className="animate-fade-in"
              style={{
                display: 'flex',
                gap: '12px',
                flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                alignItems: 'flex-start'
              }}
            >
              {/* Avatar */}
              <div style={{
                width: '36px', height: '36px', borderRadius: '10px', flexShrink: 0,
                background: msg.role === 'user' ? 'var(--accent-blue)' : 'var(--accent-green-glow)',
                border: msg.role === 'model' ? '1px solid var(--accent-green)' : 'none',
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                {msg.role === 'user'
                  ? <User size={19} color="#ffffff" />
                  : <Bot size={19} color="var(--accent-green)" />
                }
              </div>

              {/* Bubble */}
              <div style={{
                maxWidth: '82%',
                background: msg.role === 'user' ? 'var(--accent-blue)' : 'var(--bg-secondary)',
                border: msg.role === 'model' ? '1px solid var(--border-color)' : 'none',
                borderRadius: '16px',
                borderTopRightRadius: msg.role === 'user' ? '4px' : '16px',
                borderTopLeftRadius: msg.role === 'model' ? '4px' : '16px',
                padding: '14px 18px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
                color: '#f9fafb'
              }}>
                <RichText text={msg.text} />

                {/* Portfolio Chartsheet CTA button if recommendation was detected */}
                {msg.recommendation && (
                  <div style={{ marginTop: '14px', paddingTop: '14px', borderTop: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <TrendingUp size={14} color="var(--accent-green)" />
                      <span>Portfolio calculated based on your message. View the full compound chartsheet:</span>
                    </div>
                    <button
                      onClick={() => {
                        onApplyPortfolio(msg.recommendation);
                        setActiveTab('chartsheet');
                      }}
                      className="btn btn-primary"
                      style={{ fontSize: '0.86rem', padding: '10px 16px' }}
                    >
                      <span>Open Interactive Chartsheet & Year-by-Year Matrix</span>
                      <ArrowRight size={15} />
                    </button>
                  </div>
                )}

                <div style={{ fontSize: '0.7rem', color: msg.role === 'user' ? 'rgba(255,255,255,0.6)' : 'var(--text-dim)', textAlign: 'right', marginTop: '8px' }}>
                  {msg.timestamp}
                </div>
              </div>
            </div>
          ))}

          {/* Typing Indicator */}
          {isLoading && (
            <div className="animate-fade-in" style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
              <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: 'var(--accent-green-glow)', border: '1px solid var(--accent-green)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <Bot size={19} color="var(--accent-green)" />
              </div>
              <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '16px', borderTopLeftRadius: '4px', padding: '16px 20px' }}>
                <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                  {[0, 1, 2].map(i => (
                    <div key={i} style={{
                      width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent-green)',
                      animation: 'pulse 1.2s infinite',
                      animationDelay: `${i * 0.2}s`,
                      opacity: 0.7
                    }} />
                  ))}
                  <span style={{ fontSize: '0.84rem', color: 'var(--text-muted)', marginLeft: '6px' }}>Analyzing Indian markets...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Input Bar */}
        <div style={{ padding: '14px 18px', background: 'var(--bg-secondary)', borderTop: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end' }}>
            <textarea
              ref={inputRef}
              className="input-field"
              placeholder="Ask anything about Indian stocks, SIP, portfolio planning, NIFTY, Sensex... (Press Enter to send, Shift+Enter for new line)"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={2}
              disabled={isLoading}
              style={{ resize: 'none', flex: 1, lineHeight: '1.5' }}
            />
            <button
              onClick={() => handleSendMessage()}
              className="btn btn-primary"
              disabled={!input.trim() || isLoading}
              style={{ padding: '12px 18px', flexShrink: 0, opacity: (!input.trim() || isLoading) ? 0.5 : 1, alignSelf: 'flex-end' }}
            >
              <Send size={18} />
              <span>Send</span>
            </button>
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '6px' }}>
            ⚠️ AI-generated financial advice is for educational purposes only. Please consult a SEBI-registered advisor before investing.
          </div>
        </div>
      </div>

      {/* Pulse animation style */}
      <style>{`
        @keyframes pulse {
          0%, 100% { transform: scale(0.75); opacity: 0.5; }
          50% { transform: scale(1.1); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
