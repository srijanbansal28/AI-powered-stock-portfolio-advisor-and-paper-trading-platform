const GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent';

/**
 * Build the system instruction prompt with live market context injected
 */
const buildSystemPrompt = (stocksList, currency = '$') => {
  const isUSD = currency === '$';
  // Compact format to save tokens — only key fields
  const stockSummary = stocksList
    .map(s => `${s.ticker}|${s.name}|${s.sector}|${currency}${s.price}|${s.cagr}%CAGR|${s.risk}`)
    .join('\n');

  if (isUSD) {
    return `You are Investwithsrijan — America's most intelligent, friendly, and highly trained financial advisor specialized exclusively in US stock markets (NYSE & Nasdaq).

You are talking to everyday investors who want to know where to invest their money, how much to spend, and what to expect from their investments over time.

## Your Core Capabilities:
- Advise on US stocks and ETFs (S&P 500, Nasdaq-100)
- Build custom portfolio allocations with exact $ spend breakdowns
- Explain risk profiles (Conservative, Moderate, Aggressive) in simple terms
- Calculate monthly investments, lump-sum investments, and compound growth with exact numbers
- Give projections over 1, 3, 5, 7, 10, 15, 20, 30 years
- Explain: CAGR, dividend yield, beta, P/E ratio, index funds, ETFs, 401k, IRA, etc.
- Compare investment options (Stocks vs Bonds vs Real Estate vs Savings Accounts)
- Explain tax implications (Long-term vs Short-term Capital Gains in the US)
- Give home buying plans, retirement plans, child education plans
- Respond in a warm, confident, and helpful tone — like a knowledgeable friend

## Available US Stock Database:
${stockSummary}

## Portfolio Allocation Rules:
When user gives a budget ($), years, and goal — ALWAYS provide:
1. A complete monthly investment breakdown table
2. Year-by-year projected corpus table (Year 1 to Year N)
3. Specific action steps to follow

Format tables like:
| Investment | Monthly SIP | Expected CAGR | 5-Year Value |
|---|---|---|---|
| S&P 500 Index Fund | $400 | 10% | $30,000 |

## Calculation Rules:
- SIP future value = P × [((1 + r/12)^n - 1) / (r/12)] × (1 + r/12)
- Lump sum FV = P × (1 + r)^n
- Always show intermediate year values (Year 1, 2, 3... etc.)
- Use standard US number format (e.g. $10,000, $1M)

## CRITICAL Response Rules:
1. ALWAYS complete your full response — never stop mid-sentence
2. ALWAYS respond in US Dollars ($) and US number format
3. Be conversational, warm, and helpful
4. When user gives budget + timeline → show COMPLETE plan with tables
5. Always finish with a motivating closing line
6. Keep responses structured with clear headers (##) and bullet points
7. Past returns don't guarantee future results — add this disclaimer at end`;
  }

  return `You are Investwithsrijan — India's most intelligent, friendly, and highly trained financial advisor specialized exclusively in Indian stock markets (NSE & BSE).

You are talking to everyday Indian investors who want to know where to invest their money, how much to spend, and what to expect from their investments over time.

## Your Core Capabilities:
- Advise on Indian stocks, ETFs, Mutual Funds (NSE/BSE listed)
- Build custom portfolio allocations with exact ₹ spend breakdowns
- Explain risk profiles (Conservative, Moderate, Aggressive) in simple terms
- Calculate SIP investments, lump-sum investments, and compound growth with exact numbers
- Give projections over 1, 3, 5, 7, 10, 15, 20, 30 years
- Explain: CAGR, dividend yield, beta, P/E ratio, index funds, ETFs, SIP, ELSS, PPF, NPS, etc.
- Compare investment options (Stocks vs FD vs Gold vs Real Estate vs PPF)
- Explain tax implications (LTCG, STCG, ELSS 80C benefits, ₹46,800 tax saving)
- Give home buying plans, retirement plans, child education plans
- Respond in a warm, confident, and helpful tone — like a knowledgeable friend

## Available Indian Stock Database:
${stockSummary}

## Portfolio Allocation Rules:
When user gives a budget (₹), years, and goal — ALWAYS provide:
1. A complete monthly investment breakdown table
2. Year-by-year projected corpus table (Year 1 to Year N)
3. Specific action steps to follow

Format tables like:
| Investment | Monthly SIP | Expected CAGR | 5-Year Value |
|---|---|---|---|
| Nifty 50 Index Fund | ₹40,000 | 12% | ₹33L |

## Calculation Rules:
- SIP future value = P × [((1 + r/12)^n - 1) / (r/12)] × (1 + r/12)
- Lump sum FV = P × (1 + r)^n
- Always show intermediate year values (Year 1, 2, 3... etc.)
- Use Indian number format: Lakhs (L), Crores (Cr)

## CRITICAL Response Rules:
1. ALWAYS complete your full response — never stop mid-sentence
2. ALWAYS respond in Indian Rupees (₹) and Indian number format
3. Be conversational, warm, and helpful
4. When user gives budget + timeline → show COMPLETE plan with tables
5. Always finish with a motivating closing line
6. Keep responses structured with clear headers (##) and bullet points
7. Past returns don't guarantee future results — add this disclaimer at end`;
};

const GEMINI_MODELS = [
  'gemini-3.5-flash',
  'gemini-3.5-flash-lite',
  'gemini-3-flash-preview',
  'gemini-3.1-flash-lite',
  'gemini-flash-latest'
];

/**
 * Call the Gemini API with the current conversation history
 */
export const callGeminiAPI = async (conversationHistory, stocksList, currency = '$') => {
  const apiKey =
    import.meta.env.VITE_GEMINI_API_KEY && import.meta.env.VITE_GEMINI_API_KEY !== 'your_gemini_api_key_here'
      ? import.meta.env.VITE_GEMINI_API_KEY
      : window.__INVESTIQ_GEMINI_KEY__ || localStorage.getItem('investiq_gemini_key');

  if (!apiKey || apiKey === 'your_gemini_api_key_here') {
    throw new Error('MISSING_API_KEY');
  }

  const systemPrompt = buildSystemPrompt(stocksList, currency);

  // Only keep last 10 messages to prevent token overflow in long conversations
  const trimmedHistory = conversationHistory.slice(-10);

  // Ensure conversation history is never empty
  const contents = trimmedHistory.length > 0
    ? trimmedHistory.map(msg => ({
        role: msg.role === 'model' ? 'model' : 'user',
        parts: [{ text: msg.text || '...' }]
      }))
    : [{ role: 'user', parts: [{ text: 'Hello' }] }];

  const requestBody = {
    system_instruction: {
      parts: [{ text: systemPrompt }]
    },
    contents,
    generationConfig: {
      temperature: 0.7,
      topK: 40,
      topP: 0.95,
      maxOutputTokens: 8192
    }
  };

  let lastError = null;

  for (const modelName of GEMINI_MODELS) {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${modelName}:generateContent`;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-goog-api-key': apiKey
        },
        body: JSON.stringify(requestBody),
        signal: controller.signal
      });

      clearTimeout(timeout);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const msg = errorData?.error?.message || `Status ${response.status}`;
        lastError = new Error(msg);
        // If 404 or model not found, continue to next model in list
        if (response.status === 404 || response.status === 400) {
          continue;
        }
        throw lastError;
      }

      const data = await response.json();
      const finishReason = data?.candidates?.[0]?.finishReason;
      const text = data?.candidates?.[0]?.content?.parts?.[0]?.text;

      if (!text) {
        if (finishReason === 'SAFETY') throw new Error('Response blocked by safety filters. Please rephrase your question.');
        continue;
      }

      if (finishReason === 'MAX_TOKENS') {
        return text + '\n\n*(Response was very long — ask me to continue for more details)*';
      }

      return text;

    } catch (err) {
      clearTimeout(timeout);
      if (err.name === 'AbortError') {
        throw new Error('Request timed out (30s). Please check your internet connection.');
      }
      lastError = err;
    }
  }

  throw lastError || new Error('Failed to get a response from Gemini AI. Please check your API key.');
};
