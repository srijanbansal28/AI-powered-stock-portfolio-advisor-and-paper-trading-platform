// Extended database of Top 50 US Stocks & ETFs
export const INITIAL_US_STOCKS = [
  // ETFs
  { ticker: "SPY", name: "SPDR S&P 500 ETF", sector: "Index Fund", price: 520.40, cagr: 10.5, dividendYield: 1.30, risk: "Moderate", beta: 1.0, peRatio: 24.5, description: "Tracks the top 500 largest US publicly traded companies." },
  { ticker: "QQQ", name: "Invesco QQQ Trust", sector: "Index Fund", price: 440.20, cagr: 15.5, dividendYield: 0.60, risk: "High", beta: 1.15, peRatio: 32.8, description: "Tracks the Nasdaq-100 Index. Heavy tech focus." },
  { ticker: "DIA", name: "SPDR Dow Jones Industrial Average", sector: "Index Fund", price: 390.10, cagr: 9.2, dividendYield: 1.80, risk: "Low", beta: 0.9, peRatio: 21.0, description: "Tracks the 30 blue-chip companies in the Dow Jones." },
  { ticker: "SCHD", name: "Schwab US Dividend Equity ETF", sector: "Dividend ETF", price: 80.50, cagr: 11.2, dividendYield: 3.40, risk: "Low", beta: 0.85, peRatio: 15.2, description: "Focuses on high-quality US companies with a strong history of paying dividends." },
  
  // Technology (Mega Cap)
  { ticker: "AAPL", name: "Apple Inc.", sector: "Technology", price: 175.50, cagr: 22.4, dividendYield: 0.55, risk: "Moderate", beta: 1.25, peRatio: 28.4, description: "Global tech leader in consumer electronics and software." },
  { ticker: "MSFT", name: "Microsoft Corporation", sector: "Technology", price: 410.80, cagr: 25.1, dividendYield: 0.70, risk: "Moderate", beta: 1.15, peRatio: 36.2, description: "Dominates enterprise software and cloud computing." },
  { ticker: "NVDA", name: "NVIDIA Corporation", sector: "Semiconductors", price: 850.30, cagr: 45.8, dividendYield: 0.02, risk: "Very High", beta: 1.80, peRatio: 75.4, description: "The primary engine of the AI revolution, producing advanced GPUs." },
  { ticker: "GOOGL", name: "Alphabet Inc.", sector: "Technology", price: 140.20, cagr: 18.5, dividendYield: 0.00, risk: "Moderate", beta: 1.05, peRatio: 25.1, description: "Parent company of Google and YouTube. Leader in search and AI." },
  { ticker: "AMZN", name: "Amazon.com, Inc.", sector: "Consumer Discretionary", price: 180.50, cagr: 18.2, dividendYield: 0.00, risk: "High", beta: 1.30, peRatio: 60.1, description: "E-commerce and cloud computing dominant player." },
  { ticker: "META", name: "Meta Platforms, Inc.", sector: "Communication", price: 505.20, cagr: 20.4, dividendYield: 0.40, risk: "High", beta: 1.25, peRatio: 31.5, description: "Owns Facebook, Instagram, and WhatsApp." },
  
  // Semiconductors & Hardware
  { ticker: "AMD", name: "Advanced Micro Devices", sector: "Semiconductors", price: 165.40, cagr: 32.1, dividendYield: 0.00, risk: "High", beta: 1.70, peRatio: 45.2, description: "Key competitor in CPUs and GPUs." },
  { ticker: "INTC", name: "Intel Corporation", sector: "Semiconductors", price: 43.20, cagr: 5.5, dividendYield: 1.15, risk: "High", beta: 1.10, peRatio: 85.0, description: "Legacy chipmaker focused on foundries." },
  { ticker: "TSM", name: "Taiwan Semiconductor", sector: "Semiconductors", price: 140.50, cagr: 19.8, dividendYield: 1.40, risk: "Moderate", beta: 1.20, peRatio: 22.5, description: "World's largest semiconductor foundry." },
  { ticker: "CSCO", name: "Cisco Systems", sector: "Hardware", price: 50.10, cagr: 8.5, dividendYield: 3.20, risk: "Low", beta: 0.90, peRatio: 15.4, description: "Enterprise networking equipment leader." },
  { ticker: "IBM", name: "International Business Machines", sector: "Hardware", price: 190.20, cagr: 7.5, dividendYield: 3.50, risk: "Low", beta: 0.85, peRatio: 20.1, description: "Legacy tech focused on hybrid cloud and AI." },

  // Software & Services
  { ticker: "CRM", name: "Salesforce, Inc.", sector: "Software", price: 300.50, cagr: 21.5, dividendYield: 0.50, risk: "High", beta: 1.20, peRatio: 45.8, description: "Leader in CRM software." },
  { ticker: "ADBE", name: "Adobe Inc.", sector: "Software", price: 510.30, cagr: 23.4, dividendYield: 0.00, risk: "Moderate", beta: 1.25, peRatio: 48.2, description: "Creative and document management software." },
  { ticker: "ORCL", name: "Oracle Corporation", sector: "Software", price: 125.40, cagr: 14.5, dividendYield: 1.30, risk: "Moderate", beta: 1.05, peRatio: 30.1, description: "Enterprise database and cloud systems." },
  { ticker: "NFLX", name: "Netflix, Inc.", sector: "Communication", price: 610.20, cagr: 28.5, dividendYield: 0.00, risk: "High", beta: 1.30, peRatio: 45.1, description: "Global streaming entertainment giant." },
  { ticker: "UBER", name: "Uber Technologies", sector: "Technology", price: 75.30, cagr: 35.2, dividendYield: 0.00, risk: "High", beta: 1.40, peRatio: 80.5, description: "Ride-hailing and food delivery platform." },

  // Financials
  { ticker: "BRK.B", name: "Berkshire Hathaway Inc.", sector: "Financials", price: 410.50, cagr: 9.8, dividendYield: 0.00, risk: "Low", beta: 0.85, peRatio: 22.1, description: "Warren Buffett's conglomerate." },
  { ticker: "JPM", name: "JPMorgan Chase & Co.", sector: "Financials", price: 195.30, cagr: 12.5, dividendYield: 2.30, risk: "Moderate", beta: 1.10, peRatio: 11.5, description: "The largest bank in the US." },
  { ticker: "V", name: "Visa Inc.", sector: "Financials", price: 280.40, cagr: 18.5, dividendYield: 0.75, risk: "Low", beta: 0.95, peRatio: 32.4, description: "Global payments technology company." },
  { ticker: "MA", name: "Mastercard Inc.", sector: "Financials", price: 460.20, cagr: 20.1, dividendYield: 0.55, risk: "Low", beta: 1.00, peRatio: 38.5, description: "Multinational financial services corporation." },
  { ticker: "BAC", name: "Bank of America", sector: "Financials", price: 36.50, cagr: 11.2, dividendYield: 2.60, risk: "Moderate", beta: 1.30, peRatio: 12.1, description: "Major multinational investment bank." },
  { ticker: "WFC", name: "Wells Fargo", sector: "Financials", price: 58.20, cagr: 10.5, dividendYield: 2.40, risk: "Moderate", beta: 1.15, peRatio: 13.5, description: "American multinational financial services." },
  { ticker: "GS", name: "Goldman Sachs", sector: "Financials", price: 405.30, cagr: 13.5, dividendYield: 2.70, risk: "High", beta: 1.40, peRatio: 15.2, description: "Leading global investment banking firm." },

  // Healthcare
  { ticker: "JNJ", name: "Johnson & Johnson", sector: "Healthcare", price: 155.40, cagr: 7.2, dividendYield: 3.10, risk: "Low", beta: 0.60, peRatio: 14.8, description: "Healthcare giant with reliable dividends." },
  { ticker: "UNH", name: "UnitedHealth Group", sector: "Healthcare", price: 490.50, cagr: 16.5, dividendYield: 1.50, risk: "Low", beta: 0.70, peRatio: 20.5, description: "Diversified healthcare and insurance company." },
  { ticker: "LLY", name: "Eli Lilly and Company", sector: "Healthcare", price: 750.30, cagr: 35.5, dividendYield: 0.65, risk: "High", beta: 0.95, peRatio: 115.4, description: "Pharmaceutical giant leading in diabetes/weight loss." },
  { ticker: "PFE", name: "Pfizer Inc.", sector: "Healthcare", price: 28.50, cagr: 4.5, dividendYield: 6.10, risk: "Moderate", beta: 0.65, peRatio: 18.5, description: "Multinational pharmaceutical and biotechnology corporation." },
  { ticker: "ABBV", name: "AbbVie Inc.", sector: "Healthcare", price: 178.20, cagr: 14.2, dividendYield: 3.40, risk: "Moderate", beta: 0.75, peRatio: 25.1, description: "Biopharmaceutical company known for Humira." },

  // Consumer Discretionary & Staples
  { ticker: "TSLA", name: "Tesla, Inc.", sector: "Automotive", price: 175.20, cagr: 38.5, dividendYield: 0.00, risk: "Very High", beta: 2.10, peRatio: 45.6, description: "Electric vehicle and clean energy company." },
  { ticker: "WMT", name: "Walmart Inc.", sector: "Consumer Staples", price: 60.50, cagr: 9.5, dividendYield: 1.40, risk: "Low", beta: 0.50, peRatio: 28.5, description: "Multinational retail corporation." },
  { ticker: "PG", name: "Procter & Gamble", sector: "Consumer Staples", price: 160.20, cagr: 8.5, dividendYield: 2.40, risk: "Low", beta: 0.40, peRatio: 26.5, description: "Consumer goods corporation." },
  { ticker: "KO", name: "Coca-Cola Company", sector: "Consumer Staples", price: 60.10, cagr: 7.5, dividendYield: 3.20, risk: "Low", beta: 0.55, peRatio: 24.1, description: "Global beverage giant." },
  { ticker: "PEP", name: "PepsiCo, Inc.", sector: "Consumer Staples", price: 170.40, cagr: 8.1, dividendYield: 2.90, risk: "Low", beta: 0.55, peRatio: 25.4, description: "Food, snack, and beverage corporation." },
  { ticker: "COST", name: "Costco Wholesale", sector: "Consumer Staples", price: 740.50, cagr: 18.5, dividendYield: 0.60, risk: "Low", beta: 0.75, peRatio: 50.1, description: "Membership-only warehouse club retail." },
  { ticker: "HD", name: "The Home Depot", sector: "Consumer Discretionary", price: 375.20, cagr: 15.5, dividendYield: 2.40, risk: "Moderate", beta: 1.00, peRatio: 25.5, description: "Largest home improvement retailer in the US." },
  { ticker: "MCD", name: "McDonald's Corp", sector: "Consumer Discretionary", price: 280.40, cagr: 11.5, dividendYield: 2.30, risk: "Low", beta: 0.70, peRatio: 24.5, description: "Global fast food chain." },
  { ticker: "SBUX", name: "Starbucks Corp", sector: "Consumer Discretionary", price: 90.50, cagr: 12.1, dividendYield: 2.50, risk: "Moderate", beta: 0.95, peRatio: 23.4, description: "Multinational chain of coffeehouses." },
  { ticker: "NKE", name: "NIKE, Inc.", sector: "Consumer Discretionary", price: 95.20, cagr: 10.5, dividendYield: 1.50, risk: "Moderate", beta: 1.10, peRatio: 28.5, description: "Athletic footwear and apparel." },

  // Energy & Industrials
  { ticker: "XOM", name: "Exxon Mobil Corporation", sector: "Energy", price: 115.80, cagr: 8.5, dividendYield: 3.20, risk: "Moderate", beta: 1.05, peRatio: 12.4, description: "Multinational oil and gas corporation." },
  { ticker: "CVX", name: "Chevron Corporation", sector: "Energy", price: 155.30, cagr: 8.2, dividendYield: 4.10, risk: "Moderate", beta: 1.05, peRatio: 13.5, description: "American multinational energy corporation." },
  { ticker: "GE", name: "General Electric", sector: "Industrials", price: 165.20, cagr: 12.5, dividendYield: 0.70, risk: "High", beta: 1.20, peRatio: 18.5, description: "Aviation and energy infrastructure." },
  { ticker: "CAT", name: "Caterpillar Inc.", sector: "Industrials", price: 360.50, cagr: 14.5, dividendYield: 1.40, risk: "Moderate", beta: 1.15, peRatio: 17.2, description: "World's largest construction-equipment manufacturer." },
  { ticker: "BA", name: "Boeing Company", sector: "Industrials", price: 180.50, cagr: 5.5, dividendYield: 0.00, risk: "High", beta: 1.40, peRatio: 0, description: "Multinational aerospace and defense corporation." },
  { ticker: "UNP", name: "Union Pacific", sector: "Industrials", price: 240.30, cagr: 11.5, dividendYield: 2.10, risk: "Moderate", beta: 1.05, peRatio: 22.1, description: "Freight-hauling railroad." },

  // Telecom & Others
  { ticker: "T", name: "AT&T Inc.", sector: "Communication", price: 17.50, cagr: 4.5, dividendYield: 6.50, risk: "Low", beta: 0.75, peRatio: 9.5, description: "Multinational telecommunications." },
  { ticker: "VZ", name: "Verizon Communications", sector: "Communication", price: 40.20, cagr: 5.1, dividendYield: 6.60, risk: "Low", beta: 0.65, peRatio: 14.5, description: "Broadband and telecommunications." }
];

export const INITIAL_INDIA_STOCKS = [
  // ETFs
  { ticker: "NIFTYBEES.NS", name: "Nippon India ETF Nifty 50 BeES", sector: "Index Fund", price: 270.85, cagr: 14.5, dividendYield: 1.2, risk: "Moderate", beta: 1.0, peRatio: 22.5, description: "Tracks the Nifty 50 Index. Core holding for Indian portfolios." },
  { ticker: "JUNIORBEES.NS", name: "Nippon India ETF Nifty Next 50", sector: "Index Fund", price: 808.24, cagr: 16.5, dividendYield: 0.8, risk: "High", beta: 1.15, peRatio: 26.8, description: "Tracks the next 50 largest companies after Nifty 50." },
  { ticker: "BANKBEES.NS", name: "Nippon India ETF Bank BeES", sector: "Sector ETF", price: 597.05, cagr: 15.2, dividendYield: 1.0, risk: "High", beta: 1.2, peRatio: 18.0, description: "Tracks the Nifty Bank Index." },
  { ticker: "GOLDBEES.NS", name: "Nippon India ETF Gold BeES", sector: "Commodity ETF", price: 124.91, cagr: 9.5, dividendYield: 0.0, risk: "Low", beta: 0.1, peRatio: 0, description: "Tracks the price of physical gold." },
  
  // IT / Tech
  { ticker: "TCS.NS", name: "Tata Consultancy Services", sector: "Technology", price: 2349.70, cagr: 18.4, dividendYield: 1.8, risk: "Moderate", beta: 0.8, peRatio: 28.5, description: "India's largest IT services company." },
  { ticker: "INFY.NS", name: "Infosys Limited", sector: "Technology", price: 1165.10, cagr: 16.1, dividendYield: 2.1, risk: "Moderate", beta: 0.85, peRatio: 24.2, description: "Global leader in next-generation digital services." },
  { ticker: "HCLTECH.NS", name: "HCL Technologies", sector: "Technology", price: 1363.20, cagr: 19.8, dividendYield: 2.5, risk: "Moderate", beta: 0.9, peRatio: 21.4, description: "Multinational IT services and consulting." },
  { ticker: "WIPRO.NS", name: "Wipro Limited", sector: "Technology", price: 184.24, cagr: 12.5, dividendYield: 0.8, risk: "Moderate", beta: 0.95, peRatio: 20.1, description: "Leading global IT, consulting and business process services company." },
  { ticker: "TECHM.NS", name: "Tech Mahindra", sector: "Technology", price: 1629.80, cagr: 14.2, dividendYield: 2.2, risk: "High", beta: 1.1, peRatio: 22.1, description: "IT services with a strong telecom vertical." },

  // Financials
  { ticker: "HDFCBANK.NS", name: "HDFC Bank Limited", sector: "Financials", price: 726.80, cagr: 15.8, dividendYield: 1.2, risk: "Moderate", beta: 1.05, peRatio: 16.1, description: "India's largest private sector bank." },
  { ticker: "ICICIBANK.NS", name: "ICICI Bank Limited", sector: "Financials", price: 1408.30, cagr: 22.5, dividendYield: 0.8, risk: "Moderate", beta: 1.1, peRatio: 18.5, description: "Major private sector bank with strong growth." },
  { ticker: "SBIN.NS", name: "State Bank of India", sector: "Financials", price: 1070.20, cagr: 18.5, dividendYield: 1.5, risk: "High", beta: 1.25, peRatio: 9.4, description: "India's largest public sector bank." },
  { ticker: "KOTAKBANK.NS", name: "Kotak Mahindra Bank", sector: "Financials", price: 393.05, cagr: 14.1, dividendYield: 0.2, risk: "Moderate", beta: 0.95, peRatio: 20.5, description: "Private bank known for prudent risk management." },
  { ticker: "AXISBANK.NS", name: "Axis Bank Limited", sector: "Financials", price: 1216.10, cagr: 16.2, dividendYield: 0.5, risk: "High", beta: 1.2, peRatio: 15.1, description: "Third largest private sector bank in India." },
  { ticker: "BAJFINANCE.NS", name: "Bajaj Finance Limited", sector: "Financials", price: 1087.80, cagr: 35.5, dividendYield: 0.4, risk: "Very High", beta: 1.35, peRatio: 32.5, description: "Leading non-banking financial company." },

  // Energy & Utilities
  { ticker: "RELIANCE.NS", name: "Reliance Industries", sector: "Conglomerate", price: 1304.80, cagr: 21.2, dividendYield: 0.3, risk: "Moderate", beta: 1.05, peRatio: 28.8, description: "Massive conglomerate spanning oil, retail, and telecom." },
  { ticker: "ONGC.NS", name: "Oil & Natural Gas Corp", sector: "Energy", price: 235.70, cagr: 8.5, dividendYield: 5.5, risk: "Moderate", beta: 1.1, peRatio: 6.5, description: "Largest crude oil and natural gas company in India." },
  { ticker: "NTPC.NS", name: "NTPC Limited", sector: "Utilities", price: 344.25, cagr: 14.5, dividendYield: 2.5, risk: "Low", beta: 0.85, peRatio: 15.4, description: "India's largest power utility." },
  { ticker: "POWERGRID.NS", name: "Power Grid Corp", sector: "Utilities", price: 266.80, cagr: 12.5, dividendYield: 4.5, risk: "Low", beta: 0.75, peRatio: 14.1, description: "State-owned electric utility." },
  { ticker: "COALINDIA.NS", name: "Coal India Limited", sector: "Materials", price: 406.80, cagr: 9.5, dividendYield: 6.5, risk: "Moderate", beta: 0.9, peRatio: 8.5, description: "Largest coal producer in the world. High dividend." },

  // Consumer Discretionary & FMCG
  { ticker: "ITC.NS", name: "ITC Limited", sector: "Consumer Staples", price: 277.00, cagr: 11.5, dividendYield: 3.5, risk: "Low", beta: 0.65, peRatio: 25.1, description: "FMCG, hotels, packaging, and agribusiness conglomerate." },
  { ticker: "HINDUNILVR.NS", name: "Hindustan Unilever", sector: "Consumer Staples", price: 2082.40, cagr: 12.5, dividendYield: 1.8, risk: "Low", beta: 0.55, peRatio: 52.5, description: "India's largest FMCG company." },
  { ticker: "NESTLEIND.NS", name: "Nestle India", sector: "Consumer Staples", price: 1505.20, cagr: 15.5, dividendYield: 1.2, risk: "Low", beta: 0.6, peRatio: 75.1, description: "Leading food and beverage company." },
  { ticker: "TITAN.NS", name: "Titan Company", sector: "Consumer Discretionary", price: 5055.30, cagr: 25.5, dividendYield: 0.4, risk: "High", beta: 1.05, peRatio: 85.5, description: "Lifestyle company dominating jewelry and watches." },
  { ticker: "ASIANPAINT.NS", name: "Asian Paints", sector: "Materials", price: 2702.80, cagr: 18.5, dividendYield: 1.1, risk: "Moderate", beta: 0.85, peRatio: 55.4, description: "India's largest paint company." },

  // Automobiles
  { ticker: "TATAMOTORS.NS", name: "Tata Motors", sector: "Automotive", price: 472.95, cagr: 28.5, dividendYield: 0.2, risk: "Very High", beta: 1.45, peRatio: 15.5, description: "Leading auto manufacturer with strong EV presence and JLR." },
  { ticker: "M&M.NS", name: "Mahindra & Mahindra", sector: "Automotive", price: 3420.00, cagr: 22.5, dividendYield: 1.1, risk: "High", beta: 1.2, peRatio: 22.1, description: "Leader in tractors and utility vehicles." },
  { ticker: "MARUTI.NS", name: "Maruti Suzuki", sector: "Automotive", price: 13900.00, cagr: 15.5, dividendYield: 1.2, risk: "Moderate", beta: 1.0, peRatio: 28.5, description: "India's largest passenger car manufacturer." },
  { ticker: "BAJAJ-AUTO.NS", name: "Bajaj Auto", sector: "Automotive", price: 11704.00, cagr: 18.2, dividendYield: 2.1, risk: "Moderate", beta: 0.95, peRatio: 25.1, description: "Major two-wheeler and three-wheeler manufacturer." },
  { ticker: "EICHERMOT.NS", name: "Eicher Motors", sector: "Automotive", price: 8129.00, cagr: 20.5, dividendYield: 0.8, risk: "High", beta: 1.1, peRatio: 35.2, description: "Maker of Royal Enfield motorcycles." },

  // Healthcare
  { ticker: "SUNPHARMA.NS", name: "Sun Pharmaceutical", sector: "Healthcare", price: 1920.20, cagr: 16.5, dividendYield: 0.8, risk: "Moderate", beta: 0.75, peRatio: 35.1, description: "Largest Indian pharma company." },
  { ticker: "DRREDDY.NS", name: "Dr. Reddy's Laboratories", sector: "Healthcare", price: 1200.70, cagr: 14.5, dividendYield: 0.6, risk: "Moderate", beta: 0.7, peRatio: 22.5, description: "Global pharmaceutical company." },
  { ticker: "CIPLA.NS", name: "Cipla Limited", sector: "Healthcare", price: 1452.50, cagr: 15.2, dividendYield: 0.8, risk: "Moderate", beta: 0.75, peRatio: 28.1, description: "Multinational pharmaceutical company." },
  { ticker: "APOLLOHOSP.NS", name: "Apollo Hospitals", sector: "Healthcare", price: 8897.00, cagr: 25.5, dividendYield: 0.2, risk: "High", beta: 1.05, peRatio: 75.2, description: "Major hospital chain and pharmacy network." },

  // Infrastructure, Telecom & Others
  { ticker: "LT.NS", name: "Larsen & Toubro", sector: "Industrials", price: 4059.40, cagr: 20.5, dividendYield: 1.1, risk: "Moderate", beta: 1.15, peRatio: 35.4, description: "Engineering and construction conglomerate." },
  { ticker: "BHARTIARTL.NS", name: "Bharti Airtel", sector: "Communication", price: 1996.00, cagr: 18.5, dividendYield: 0.4, risk: "Moderate", beta: 0.95, peRatio: 55.1, description: "Leading telecommunications company." },
  { ticker: "ULTRACEMCO.NS", name: "UltraTech Cement", sector: "Materials", price: 11655.00, cagr: 16.5, dividendYield: 0.5, risk: "Moderate", beta: 1.0, peRatio: 45.2, description: "Largest manufacturer of grey cement in India." },
  { ticker: "ADANIENT.NS", name: "Adani Enterprises", sector: "Industrials", price: 3036.30, cagr: 45.5, dividendYield: 0.1, risk: "Very High", beta: 1.85, peRatio: 95.5, description: "Flagship company of the Adani Group." },
  { ticker: "ADANIPORTS.NS", name: "Adani Ports & SEZ", sector: "Industrials", price: 1693.40, cagr: 25.5, dividendYield: 0.5, risk: "High", beta: 1.45, peRatio: 35.1, description: "Largest commercial ports operator in India." }
];

const LOCAL_STORAGE_US_KEY = "investwithsrijan_us_stocks_db_v2";
const LOCAL_STORAGE_IN_KEY = "investwithsrijan_in_stocks_db_v2";

export const getStoredStocks = (currency = '$') => {
  const isUS = currency === '$';
  const key = isUS ? LOCAL_STORAGE_US_KEY : LOCAL_STORAGE_IN_KEY;
  const defaults = isUS ? INITIAL_US_STOCKS : INITIAL_INDIA_STOCKS;
  
  try {
    const data = localStorage.getItem(key);
    if (data) {
      return JSON.parse(data);
    }
  } catch (err) {
    console.error("Error reading stock DB from local storage:", err);
  }
  return defaults;
};

export const saveStocksToStore = (stocks, currency = '$') => {
  const isUS = currency === '$';
  const key = isUS ? LOCAL_STORAGE_US_KEY : LOCAL_STORAGE_IN_KEY;
  try {
    localStorage.setItem(key, JSON.stringify(stocks));
  } catch (err) {
    console.error("Error saving stock DB:", err);
  }
};

export const resetStockDatabase = (currency = '$') => {
  const isUS = currency === '$';
  const defaults = isUS ? INITIAL_US_STOCKS : INITIAL_INDIA_STOCKS;
  saveStocksToStore(defaults, currency);
  return defaults;
};
