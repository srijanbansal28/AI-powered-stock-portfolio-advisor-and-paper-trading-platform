/**
 * Financial Calculation & Portfolio Optimization Engine (Indian Markets)
 */

export const calculateCompoundGrowth = (
  initialCapital,
  monthlyContribution,
  annualReturnPercent,
  dividendYieldPercent = 0,
  targetYears = 5
) => {
  const r = annualReturnPercent / 100;
  const divR = dividendYieldPercent / 100;
  let currentBalance = Number(initialCapital);
  let totalContributions = Number(initialCapital);
  const yearlySchedule = [];

  for (let year = 1; year <= targetYears; year++) {
    const startBalance = currentBalance;
    const annualContribution = Number(monthlyContribution) * 12;
    
    // Monthly compounding calculation
    const monthlyRate = r / 12;
    let yearInterest = 0;
    
    for (let m = 0; m < 12; m++) {
      currentBalance += Number(monthlyContribution);
      const mInterest = currentBalance * monthlyRate;
      yearInterest += mInterest;
      currentBalance += mInterest;
    }

    totalContributions += annualContribution;
    const annualDividend = currentBalance * divR;
    const cumulativeGrowth = currentBalance - totalContributions;

    yearlySchedule.push({
      year,
      startBalance: Math.round(startBalance),
      annualContribution: Math.round(annualContribution),
      totalContributions: Math.round(totalContributions),
      interestEarned: Math.round(yearInterest),
      annualDividendIncome: Math.round(annualDividend),
      endBalance: Math.round(currentBalance),
      totalGrowth: Math.round(cumulativeGrowth)
    });
  }

  return yearlySchedule;
};

export const generatePortfolioRecommendation = (
  initialAmount = 50000,
  monthlySIP = 500,
  horizonYears = 5,
  riskProfile = "Moderate",
  goal = "Wealth Growth",
  stocksList = []
) => {
  const budget = Number(initialAmount);
  const sip = Number(monthlySIP);
  const years = Number(horizonYears);

  // Filter Indian stocks by risk / goal criteria
  let selectedTickers = [];
  
  if (riskProfile === "Conservative") {
    // Nifty Bluechips, Gold, FMCG, PSU
    selectedTickers = [
      { ticker: "NIFTYBEES", weight: 35 },
      { ticker: "GOLDBEES", weight: 20 },
      { ticker: "HDFCBANK", weight: 15 },
      { ticker: "ITC", weight: 15 },
      { ticker: "RELIANCE", weight: 15 }
    ];
  } else if (riskProfile === "Aggressive") {
    // High CAGR IT, Tata Motors, Bajaj Finance, Next 50
    selectedTickers = [
      { ticker: "JUNIORBEES", weight: 25 },
      { ticker: "TATAMOTORS", weight: 20 },
      { ticker: "BAJFINANCE", weight: 20 },
      { ticker: "TCS", weight: 18 },
      { ticker: "MON100", weight: 17 }
    ];
  } else if (riskProfile === "Very Aggressive") {
    // High Growth Multibagger Bets
    selectedTickers = [
      { ticker: "TATAMOTORS", weight: 25 },
      { ticker: "BAJFINANCE", weight: 25 },
      { ticker: "TITAN", weight: 20 },
      { ticker: "MON100", weight: 15 },
      { ticker: "LT", weight: 15 }
    ];
  } else if (goal.toLowerCase().includes("dividend") || riskProfile === "Income") {
    // High Dividend Yield Cashflow Indian Portfolio
    selectedTickers = [
      { ticker: "COALINDIA", weight: 30 },
      { ticker: "ITC", weight: 25 },
      { ticker: "NTPC", weight: 20 },
      { ticker: "INFY", weight: 15 },
      { ticker: "HDFCBANK", weight: 10 }
    ];
  } else {
    // Moderate (Balanced Indian Wealth Growth Default)
    selectedTickers = [
      { ticker: "NIFTYBEES", weight: 35 },
      { ticker: "RELIANCE", weight: 20 },
      { ticker: "TCS", weight: 15 },
      { ticker: "ICICIBANK", weight: 15 },
      { ticker: "BANKBEES", weight: 15 }
    ];
  }

  // Map tickers to database objects & calculate allocation breakdown
  const stockMap = new Map(stocksList.map(s => [s.ticker, s]));
  
  let weightedCAGR = 0;
  let weightedDivYield = 0;

  const allocations = selectedTickers.map(item => {
    const stock = stockMap.get(item.ticker) || {
      ticker: item.ticker,
      name: item.ticker,
      cagr: 12,
      dividendYield: 1.2,
      sector: "Indian Equity",
      price: 500
    };
    
    const spendAmount = Math.round((budget * item.weight) / 100);
    const sharesToBuy = Math.max(1, Math.round(spendAmount / stock.price));
    
    weightedCAGR += stock.cagr * (item.weight / 100);
    weightedDivYield += stock.dividendYield * (item.weight / 100);

    return {
      ticker: stock.ticker,
      name: stock.name,
      sector: stock.sector,
      weightPercentage: item.weight,
      spendAmount,
      sharesToBuy,
      price: stock.price,
      cagr: stock.cagr,
      dividendYield: stock.dividendYield,
      risk: stock.risk || "Moderate",
      description: stock.description
    };
  });

  // Calculate compound schedules for Base, Conservative (-3%), and Optimistic (+3%) scenarios
  const baseSchedule = calculateCompoundGrowth(budget, sip, weightedCAGR, weightedDivYield, years);
  const consSchedule = calculateCompoundGrowth(budget, sip, Math.max(2, weightedCAGR - 3.5), weightedDivYield, years);
  const optSchedule = calculateCompoundGrowth(budget, sip, weightedCAGR + 3.5, weightedDivYield, years);

  const finalBaseVal = baseSchedule[baseSchedule.length - 1].endBalance;
  const finalConsVal = consSchedule[consSchedule.length - 1].endBalance;
  const finalOptVal = optSchedule[optSchedule.length - 1].endBalance;
  const totalInvested = budget + sip * 12 * years;
  const netProfit = finalBaseVal - totalInvested;

  // Sector breakdown aggregation
  const sectorBreakdown = {};
  allocations.forEach(alloc => {
    sectorBreakdown[alloc.sector] = (sectorBreakdown[alloc.sector] || 0) + alloc.spendAmount;
  });

  return {
    initialAmount: budget,
    monthlySIP: sip,
    horizonYears: years,
    riskProfile,
    goal,
    weightedCAGR: Number(weightedCAGR.toFixed(2)),
    weightedDivYield: Number(weightedDivYield.toFixed(2)),
    totalInvested,
    projectedFinalValue: finalBaseVal,
    conservativeFinalValue: finalConsVal,
    optimisticFinalValue: finalOptVal,
    netProfit,
    annualDividendIncomeProjected: Math.round(finalBaseVal * (weightedDivYield / 100)),
    allocations,
    sectorBreakdown,
    baseSchedule,
    consSchedule,
    optSchedule
  };
};

export const formatCurrency = (val, currencySymbol = "₹") => {
  if (val === undefined || val === null || isNaN(val)) return `${currencySymbol}0`;
  
  const num = Number(val);
  
  // Format numbers neatly with Indian comma separator if using ₹
  if (currencySymbol === "₹") {
    return `${currencySymbol}${num.toLocaleString("en-IN", {
      maximumFractionDigits: 0
    })}`;
  }

  return `${currencySymbol}${num.toLocaleString("en-US", {
    maximumFractionDigits: 0
  })}`;
};
