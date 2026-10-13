import React, { useEffect, useRef, useState } from 'react';
import { LineChart, TrendingUp, Shield, Bot, BarChart2 } from 'lucide-react';

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

export default function LoginPage({ onLogin }) {
  const googleBtnRef = useRef(null);
  const [scriptReady, setScriptReady] = useState(false);
  const [error, setError] = useState('');

  // Wait for the Google GSI script to be ready, then initialize
  useEffect(() => {
    const initGoogle = () => {
      if (!window.google?.accounts?.id) return;

      window.google.accounts.id.initialize({
        client_id: CLIENT_ID,
        callback: handleCredentialResponse,
        auto_select: false,
        cancel_on_tap_outside: true
      });

      if (googleBtnRef.current) {
        window.google.accounts.id.renderButton(googleBtnRef.current, {
          theme: 'outline',
          size: 'large',
          width: 348,
          text: 'continue_with',
          shape: 'rectangular',
          logo_alignment: 'center'
        });
      }

      setScriptReady(true);
    };

    // If google is already loaded (script was fast)
    if (window.google?.accounts?.id) {
      initGoogle();
    } else {
      // Poll until script is ready (it's loaded async in index.html)
      const interval = setInterval(() => {
        if (window.google?.accounts?.id) {
          clearInterval(interval);
          initGoogle();
        }
      }, 100);
      return () => clearInterval(interval);
    }
  }, []);

  const handleCredentialResponse = (response) => {
    try {
      // Decode the JWT credential payload
      const base64Payload = response.credential.split('.')[1];
      const payload = JSON.parse(atob(base64Payload));
      onLogin({
        name: payload.name,
        email: payload.email,
        picture: payload.picture,
        sub: payload.sub
      });
    } catch (err) {
      setError('Failed to read Google account info. Please try again.');
    }
  };

  const features = [
    { icon: Bot, label: 'AI Investment Advisor', desc: 'Powered by Gemini AI — trained on US markets' },
    { icon: TrendingUp, label: 'S&P 500 & Nasdaq Stocks', desc: 'Top US stocks & ETFs in your portfolio engine' },
    { icon: BarChart2, label: 'Multi-Year Chartsheets', desc: 'Year-by-year SIP compound growth projections' },
    { icon: Shield, label: 'Secure & Private', desc: 'Your data stays local — nothing uploaded to any server' }
  ];

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg-primary)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px',
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* Background glows */}
      <div style={{ position: 'absolute', top: '-10%', left: '50%', transform: 'translateX(-50%)', width: '700px', height: '400px', background: 'radial-gradient(ellipse at center, rgba(16,185,129,0.07) 0%, transparent 70%)', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', bottom: '-5%', right: '-5%', width: '500px', height: '400px', background: 'radial-gradient(ellipse at center, rgba(59,130,246,0.05) 0%, transparent 70%)', pointerEvents: 'none' }} />

      <div style={{ display: 'flex', gap: '64px', alignItems: 'center', maxWidth: '1100px', width: '100%', flexWrap: 'wrap', justifyContent: 'center' }}>

        {/* Left: Branding & Features */}
        <div style={{ flex: '1 1 380px', display: 'flex', flexDirection: 'column', gap: '28px' }}>
          {/* Logo */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{ background: 'linear-gradient(135deg, #10b981 0%, #047857 100%)', width: '52px', height: '52px', borderRadius: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 6px 20px rgba(16,185,129,0.4)' }}>
              <LineChart size={28} color="#ffffff" />
            </div>
            <div>
              <div style={{ fontSize: '1.75rem', fontWeight: '800', letterSpacing: '-0.04em', color: '#ffffff' }}>
                Investwithsrijan
              </div>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: '500' }}>
                AI-Powered US Stock Portfolio Advisor
              </div>
            </div>
          </div>

          <div>
            <h1 style={{ fontSize: '2.4rem', fontWeight: '800', letterSpacing: '-0.04em', lineHeight: '1.2', color: '#ffffff' }}>
              Invest smarter<br />in <span style={{ color: 'var(--accent-green)' }}>US</span> markets
            </h1>
            <p style={{ fontSize: '1rem', color: 'var(--text-muted)', marginTop: '12px', lineHeight: '1.6' }}>
              AI-powered stock recommendations, exact $ spend allocations, and year-by-year wealth projections for US investors.
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {features.map(({ icon: Icon, label, desc }) => (
              <div key={label} style={{ display: 'flex', gap: '14px', alignItems: 'flex-start' }}>
                <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: 'var(--accent-green-glow)', border: '1px solid rgba(16,185,129,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <Icon size={18} color="var(--accent-green)" />
                </div>
                <div>
                  <div style={{ fontWeight: '700', color: '#ffffff', fontSize: '0.92rem' }}>{label}</div>
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '2px' }}>{desc}</div>
                </div>
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {['S&P 500', 'Nasdaq', 'Dow Jones', 'Tech Giants', 'SIP', 'ETF', 'Dividends'].map(tag => (
              <span key={tag} className="badge badge-blue" style={{ fontSize: '0.74rem' }}>{tag}</span>
            ))}
          </div>
        </div>

        {/* Right: Login Card */}
        <div className="glass-card" style={{ flex: '0 0 420px', padding: '40px 36px', border: '1px solid rgba(16,185,129,0.25)', boxShadow: '0 0 60px rgba(16,185,129,0.08), var(--shadow-card)', display: 'flex', flexDirection: 'column', gap: '24px', alignItems: 'center' }}>
          
          <div style={{ textAlign: 'center' }}>
            <h2 style={{ fontSize: '1.4rem', fontWeight: '800' }}>Welcome to Investwithsrijan</h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', marginTop: '6px' }}>
              Sign in with your Google account to access your personalized US stock portfolio advisor
            </p>
          </div>

          {/* Google Sign-In Button rendered by Google itself */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px', width: '100%' }}>
            {!scriptReady && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-muted)', fontSize: '0.88rem', padding: '14px' }}>
                <div style={{ width: '18px', height: '18px', border: '2px solid var(--accent-green)', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                Loading Google Sign-In...
              </div>
            )}
            {/* Google renders its native button here */}
            <div ref={googleBtnRef} style={{ minHeight: '44px' }} />
          </div>

          {error && (
            <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '10px', padding: '10px 14px', fontSize: '0.84rem', color: '#f87171', textAlign: 'center' }}>
              {error}
            </div>
          )}

          <div style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: '12px', width: '100%' }}>
            <div style={{ flex: 1, height: '1px', background: 'var(--border-color)' }} />
            <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)', fontWeight: '500' }}>SECURE LOGIN</span>
            <div style={{ flex: 1, height: '1px', background: 'var(--border-color)' }} />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '100%' }}>
            {[
              '🔒 We never store your passwords',
              '✅ Only your name, email & photo are used',
              '🇮🇳 Your portfolio data stays on your device'
            ].map(item => (
              <div key={item} style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>{item}</div>
            ))}
          </div>

          <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textAlign: 'center', lineHeight: '1.5' }}>
            By continuing, you agree to Investwithsrijan's terms. This app uses Google OAuth only for identity verification.
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
