import React, { useState } from 'react';
import { PlusCircle, Trash2, TrendingUp, PieChart as PieIcon, AlertCircle } from 'lucide-react';
import { PieChart as RechartsPie, Cell, ResponsiveContainer, LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip } from 'recharts';

const API_BASE = 'http://localhost:5001';

const DEFAULT_HOLDINGS = [
  { symbol: 'AAPL', allocation: '25' },
  { symbol: 'MSFT', allocation: '25' },
  { symbol: 'GOOG', allocation: '25' },
  { symbol: 'TSLA', allocation: '25' },
];

const getDiversificationLabel = (score) => {
  if (score >= 0.6) return { text: 'High', color: 'text-emerald-300' };
  if (score >= 0.3) return { text: 'Medium', color: 'text-amber-300' };
  return { text: 'Low', color: 'text-rose-300' };
};


const PortfolioAnalyzer = () => {
  const [holdings, setHoldings] = useState(DEFAULT_HOLDINGS);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const addHolding = () => {
    setHoldings([...holdings, { symbol: '', allocation: '' }]);
  };

  const removeHolding = (index) => {
    if (holdings.length > 1) {
      setHoldings(holdings.filter((_, i) => i !== index));
    }
  };

  const updateHolding = (index, field, value) => {
    const updated = holdings.map((holding, i) =>
      i === index ? { ...holding, [field]: value } : holding
    );
    setHoldings(updated);
  };

  const validatePortfolio = () => {
    const validHoldings = holdings.filter((h) => h.symbol && h.allocation);
    if (validHoldings.length === 0) {
      setError('Please add at least one stock with allocation.');
      return false;
    }

    const totalAllocation = validHoldings.reduce(
      (sum, h) => sum + parseFloat(h.allocation || 0),
      0
    );
    if (Math.abs(totalAllocation - 100) > 0.01) {
      setError(`Total allocation must equal 100%. Current total: ${totalAllocation.toFixed(2)}%`);
      return false;
    }

    setError('');
    return true;
  };

  const analyzePortfolio = async () => {
    if (!validatePortfolio()) return;

    setLoading(true);
    setError('');

    try {
      const validHoldings = holdings.filter((h) => h.symbol && h.allocation);
      const portfolio = validHoldings.map((h) => ({
        symbol: h.symbol.toUpperCase(),
        allocation: parseFloat(h.allocation),
      }));

      const response = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ portfolio }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to analyze portfolio');
      }

      setAnalysis(data);
    } catch (err) {
      console.error('Analysis error:', err);
      setError(err.message || 'Failed to analyze portfolio. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#00c9a7', '#ff6f61'];
  const totalAllocation = holdings.reduce(
    (sum, h) => sum + parseFloat(h.allocation || 0),
    0
  );

  const allocationData = holdings
    .filter((h) => h.symbol && h.allocation)
    .map((h) => ({
      symbol: h.symbol.toUpperCase(),
      allocation: parseFloat(h.allocation),
    }));

  return (
    <section className="relative py-16 px-4 sm:px-6 lg:px-8 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      <div className="absolute inset-0 pointer-events-none opacity-40">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.18),_transparent_55%),_radial-gradient(circle_at_bottom,_rgba(129,140,248,0.16),_transparent_55%)]" />
      </div>

      <div className="relative max-w-5xl mx-auto space-y-10">
        <header className="text-center space-y-3">
          <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/40 bg-slate-900/60 px-4 py-1 text-xs font-medium text-cyan-100 shadow-[0_0_30px_rgba(34,211,238,0.25)]">
            <span className="h-1.5 w-1.5 rounded-full bg-cyan-300 animate-pulse" />
            QuantWise · AI-powered portfolio snapshot
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-slate-50 flex items-center justify-center gap-3">
            <TrendingUp className="h-7 w-7 text-cyan-300" />
            Portfolio Analyzer
          </h2>
          <p className="max-w-2xl mx-auto text-sm sm:text-base text-slate-300">
            Start with a ready‑made sample portfolio, tweak the allocations, and instantly see
            estimated risk & return based on recent price movements.
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-10">
          {/* Left: Inputs */}
          <div className="rounded-2xl border border-slate-700/70 bg-slate-900/80 shadow-[0_18px_60px_rgba(15,23,42,0.8)] backdrop-blur-md p-5 sm:p-6 space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                  <PieIcon className="h-4 w-4 text-cyan-300" />
                  Holdings
                </h3>
                <p className="text-xs text-slate-400">
                  Use 3–6 large cap stocks for the cleanest demo.
                </p>
              </div>
              <div className="text-right text-xs text-slate-300">
                <span className="text-slate-400">Total allocation</span>
                <p
                  className={`font-semibold ${
                    Math.abs(totalAllocation - 100) < 0.01 ? 'text-emerald-300' : 'text-amber-300'
                  }`}
                >
                  {totalAllocation.toFixed(1)}%
                </p>
              </div>
            </div>

            <div className="space-y-3 max-h-72 overflow-y-auto pr-1 custom-scrollbar">
              {holdings.map((holding, index) => (
                <div
                  key={index}
                  className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center rounded-xl border border-slate-700/70 bg-slate-900/80 px-3 py-3"
                >
                  <input
                    type="text"
                    placeholder="Symbol (e.g., AAPL)"
                    value={holding.symbol}
                    onChange={(e) =>
                      updateHolding(index, 'symbol', e.target.value.toUpperCase())
                    }
                    className="w-full sm:flex-1 rounded-lg bg-slate-900/80 px-3 py-2.5 text-sm text-slate-50 border border-slate-700 focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 outline-none placeholder:text-slate-500 transition"
                  />
                  <div className="relative w-full sm:w-32">
                    <input
                      type="number"
                      placeholder="Alloc %"
                      value={holding.allocation}
                      onChange={(e) => updateHolding(index, 'allocation', e.target.value)}
                      className="w-full rounded-lg bg-slate-900/80 px-3 py-2.5 text-sm text-slate-50 border border-slate-700 focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 outline-none placeholder:text-slate-500 transition"
                      min="0"
                      max="100"
                      step="0.1"
                    />
                    <span className="pointer-events-none absolute right-3 top-2.5 text-xs text-slate-500">
                      %
                    </span>
                  </div>
                  <button
                    onClick={() => removeHolding(index)}
                    disabled={holdings.length === 1}
                    className="inline-flex items-center justify-center rounded-lg border border-slate-700 bg-slate-900/80 px-2.5 py-2 text-xs font-medium text-slate-300 hover:border-rose-500 hover:text-rose-300 hover:bg-slate-900 disabled:opacity-40 disabled:hover:border-slate-700 disabled:hover:text-slate-300 transition"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>

            <div className="flex flex-col sm:flex-row gap-3 sm:items-center justify-between pt-2">
              <button
                onClick={addHolding}
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-cyan-500/60 bg-slate-900/80 px-3.5 py-2.5 text-xs sm:text-sm font-medium text-cyan-100 hover:bg-slate-900 hover:border-cyan-400 hover:text-cyan-50 transition shadow-[0_0_25px_rgba(34,211,238,0.25)]"
              >
                <PlusCircle className="h-4 w-4" />
                Add stock
              </button>

              <button
                onClick={analyzePortfolio}
                disabled={loading}
                className="inline-flex items-center justify-center rounded-lg bg-gradient-to-r from-cyan-500 via-sky-500 to-indigo-500 px-6 py-2.5 text-xs sm:text-sm font-semibold text-white shadow-lg shadow-cyan-500/35 hover:shadow-cyan-400/45 hover:from-cyan-400 hover:via-sky-400 hover:to-indigo-400 disabled:opacity-60 disabled:cursor-not-allowed transition-transform hover:-translate-y-0.5"
              >
                {loading ? 'Crunching numbers…' : 'Run analysis'}
              </button>
            </div>

            {error && (
              <div className="mt-3 flex items-start gap-2 rounded-lg border border-rose-500/50 bg-rose-950/60 px-3 py-2.5 text-xs text-rose-100">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-300" />
                <span>{error}</span>
              </div>
            )}
          </div>

          {/* Right: Output */}
          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-700/70 bg-slate-900/80 shadow-[0_18px_60px_rgba(15,23,42,0.8)] backdrop-blur-md p-5 sm:p-6">
              <h3 className="text-sm font-semibold text-slate-100 mb-4 flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-emerald-300" />
                Portfolio snapshot
              </h3>

              {analysis ? (
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs sm:text-sm">
                  <div className="rounded-xl bg-slate-900/80 border border-emerald-500/40 px-3 py-3 flex flex-col gap-1">
                    <span className="text-slate-400">Expected annual return</span>
                    <span className="text-emerald-300 text-lg font-semibold">
                      {(analysis.portfolio_metrics.expected_return * 100).toFixed(2)}%
                    </span>
                  </div>
                  <div className="rounded-xl bg-slate-900/80 border border-amber-500/40 px-3 py-3 flex flex-col gap-1">
                    <span className="text-slate-400">Volatility (risk)</span>
                    <span className="text-amber-300 text-lg font-semibold">
                      {(analysis.portfolio_metrics.volatility * 100).toFixed(2)}%
                    </span>
                  </div>
                  <div className="rounded-xl bg-slate-900/80 border border-sky-500/40 px-3 py-3 flex flex-col gap-1">
                    <span className="text-slate-400">Sharpe ratio</span>
                    <span className="text-sky-300 text-lg font-semibold">
                      {analysis.portfolio_metrics.sharpe_ratio.toFixed(2)}
                    </span>
                  </div>
                  {analysis.diversification && (() => {
                  const { diversification_score } = analysis.diversification;
                  const label = getDiversificationLabel(diversification_score);

                  return (
                  <div className="rounded-xl bg-slate-900/80 border border-indigo-500/40 px-3 py-3 flex flex-col gap-1">
                  <span className="text-slate-400">Diversification score</span>
                  <span className={`${label.color} text-lg font-semibold`}>
                    {diversification_score.toFixed(2)} ({label.text})
                    </span>
                  </div>
                );
          })()}
                </div>
              ) : (
                <p className="text-xs sm:text-sm text-slate-400">
                  Add or adjust your holdings on the left, then click{' '}
                  <span className="font-semibold text-slate-200">Run analysis</span> to see a quick
                  risk–return view of the portfolio.
                </p>
              )}
            </div>

            <div className="rounded-2xl border border-slate-700/70 bg-slate-900/80 shadow-[0_18px_60px_rgba(15,23,42,0.8)] backdrop-blur-md p-5 sm:p-6 space-y-5">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                  <PieIcon className="h-4 w-4 text-cyan-300" />
                  Allocation & equity curve
                </h3>
              </div>

              <div className="grid grid-cols-1 gap-6">
                {allocationData.length > 0 && (
                  <div className="h-48 sm:h-56">
                    <ResponsiveContainer width="100%" height="100%">
                      <RechartsPie
                        data={allocationData}
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        dataKey="allocation"
                        label={({ symbol, allocation }) => `${symbol}: ${allocation}%`}
                      >
                        {allocationData.map((entry, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={COLORS[index % COLORS.length]}
                          />
                        ))}
                      </RechartsPie>
                    </ResponsiveContainer>
                  </div>
                )}

                {analysis?.history && analysis.history.length > 0 && (
                  <div className="h-48 sm:h-56">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={analysis.history}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                        <XAxis dataKey="date" hide />
                        <YAxis tick={{ fill: '#9ca3af', fontSize: 10 }} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#020617',
                            borderRadius: 8,
                            border: '1px solid rgba(148, 163, 184, 0.6)',
                            fontSize: 11,
                          }}
                          labelStyle={{ color: '#e5e7eb' }}
                        />
                        <Line
                          type="monotone"
                          dataKey="value"
                          stroke="#38bdf8"
                          strokeWidth={2}
                          dot={false}
                          activeDot={{ r: 3, fill: '#e0f2fe', strokeWidth: 0 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default PortfolioAnalyzer;