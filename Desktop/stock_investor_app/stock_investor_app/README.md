# Investwithsrijan — AI Stock Portfolio Advisor & Real-Time Paper Trading Platform 📈🌐

**Investwithsrijan** is an intelligent, dual-market financial advisor and paper trading web application powered by **Google Gemini AI**, **IndianAPI.in**, **Finnhub WebSocket**, and **Firebase**.

🌐 **Live Deployed Application:** [https://investiq-ai-a1b2c.web.app](https://investiq-ai-a1b2c.web.app)

---

## 🚀 Key Features

### 1. 💱 Dual Market Architecture (US $ ⇋ India ₹)
- **1-Click Market Switching:** Instantly transforms the entire dashboard between **US Stock Markets (NYSE/Nasdaq)** and **Indian Stock Markets (NSE/BSE)**.
- **Dynamic Formatting:** Converts currencies (`$` vs `₹`), numbers (Millions/Billions vs Lakhs/Crores), tax calculations (US Capital Gains vs Indian LTCG/STCG), and investment plans (401k/IRA vs SIP/ELSS 80C).

### 2. ⚡ Real-Time Market Data Feeds
- **Indian Stocks (NSE/BSE):** Powered by **IndianAPI.in** with live tick prices, daily percentage movements, and financial metrics across 50 top bluechips & ETFs (Reliance, TCS, HDFC Bank, Infosys, Tata Motors, NiftyBEES, etc.).
- **US Stocks (NYSE/Nasdaq):** Powered by **Finnhub WebSocket (`wss://ws.finnhub.io`)** and REST quote APIs for instant trade updates across 50 leading US companies & ETFs (SPY, QQQ, Apple, Microsoft, Nvidia, Tesla, etc.).
- **24/7 Active Simulation Engine:** Realistic order book micro-ticks simulate continuous live market price action even during after-hours, holidays, and market pauses.

### 3. 🤖 AI Investment Advisor (Gemini 3.5 Flash)
- **Natural Language Advisory:** Discuss financial goals, investment horizons, and risk tolerance in plain English.
- **Mathematical Compound Growth Schedules:** Computes precise year-by-year projections, monthly SIP contributions, expected CAGR returns, and dividend cash flows.
- **Multi-Model Auto Failover:** Built on `gemini-3.5-flash` with automatic fallback to ensure 99.9% uptime.

### 4. 💼 Real-Time Paper Trading Workbench
- **Virtual Starting Capital:** $100,000 for US markets / ₹10,00,000 for Indian markets.
- **Holdings & Portfolio Tracking:** Tracks live portfolio valuation, realized/unrealized profit & loss (P&L), and percentage gainers/losers.
- **Smart Price Alerts & Auto-Execution:** Configure price triggers that alert you or automatically execute BUY/SELL orders when target prices are reached.
- **Global Leaderboard:** Synchronized community leaderboard tracking top-performing paper traders via Firebase Firestore.

### 5. 📊 Chartsheet & Strategy Playbooks
- **Strategy Hub:** Pre-built, battle-tested investment playbooks (S&P 500 Core Compounder, Nasdaq AI Growth, Nifty Bluechip Compounder, High-Yield Dividend Machines).
- **Interactive Charts & CSV Export:** Download complete multi-year investment chartsheets as CSV files.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, Vite, Vanilla CSS Design System |
| **Icons & UI** | Lucide React |
| **Charts** | Chart.js & React-Chartjs-2 |
| **AI Engine** | Google Gemini API (`gemini-3.5-flash`) |
| **Live Market Feeds** | IndianAPI.in (NSE/BSE) & Finnhub WebSocket (NYSE/Nasdaq) |
| **Backend & Cloud** | Firebase Hosting, Firestore & Google Cloud Identity |

---

## 📦 Project Directory Structure

```
stock_investor_app/
├── index.html                 # Main HTML entry point with SEO metadata
├── package.json               # Dependencies and scripts
├── vite.config.js             # Vite build configuration
├── firebase.json              # Firebase Hosting configuration
├── .firebaserc                # Firebase Project ID configuration
├── deploy.sh                  # Automated production build & deploy script
├── .env                       # Environment variables (API keys)
└── src/
    ├── main.jsx               # React DOM root mounting
    ├── App.jsx                # Global App state & Market sync router
    ├── index.css              # Glassmorphic premium CSS design tokens
    ├── components/
    │   ├── Navbar.jsx         # Currency switcher, navigation & user profile
    │   ├── LoginPage.jsx      # Google OAuth login interface
    │   ├── Chatbot.jsx        # AI Investment Advisor chat interface
    │   ├── Planner.jsx        # Lumpsum & SIP portfolio allocation planner
    │   ├── PaperTrading.jsx   # Live stock trading workbench with real-time P&L
    │   ├── Leaderboard.jsx    # Real-time community leaderboard
    │   ├── StockManager.jsx   # Custom stock database management
    │   ├── StrategyHub.jsx    # US & Indian market strategy playbooks
    │   ├── ChartsheetHub.jsx  # Multi-year investment table & CSV exporter
    │   ├── PortfolioAdvisor.jsx # AI Portfolio recommendation generator
    │   └── AlertsPanel.jsx    # Smart price alert manager
    ├── data/
    │   └── stockDatabase.js   # 50 US + 50 Indian stock database definitions
    └── utils/
        ├── financialEngine.js # Compound interest, CAGR, and SIP calculation engine
        └── geminiService.js   # Gemini AI API integration with dual market prompts
```

---

## 💻 Local Setup & Installation

### 1. Prerequisites
- **Node.js**: v18.0.0 or higher
- **npm**: v9.0.0 or higher

### 2. Installation
```bash
# Navigate to the project directory
cd stock_investor_app

# Install all required dependencies
npm install
```

### 3. Environment Variables Setup
Create or update your `.env` file in the project root:
```env
VITE_GEMINI_API_KEY=your_gemini_api_key_here
VITE_GOOGLE_CLIENT_ID=your_google_oauth_client_id_here
```

### 4. Running Locally
```bash
# Start the local development server
npm run dev
```
Open your browser at `http://localhost:5173`.

### 5. Production Build
```bash
# Build production bundle
npm run build
```

---

## ☁️ Deployment to Firebase Hosting

To deploy your live changes to Firebase Hosting:

```bash
# Make deploy script executable (if not already)
chmod +x deploy.sh

# Run automated deployment
./deploy.sh
```

---

## 📄 License
This project is open-source under the MIT License.
