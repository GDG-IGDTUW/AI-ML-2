import React, { useState, useEffect } from 'react';
import { PlusCircle, Trash2, TrendingUp, Shield, PieChart, BarChart3, AlertCircle, RefreshCw, Activity, Zap } from 'lucide-react';
import { PieChart as RechartsPie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts';

const PortfolioAnalyzer = () => {
  const [holdings, setHoldings] = useState([
    { symbol: '', allocation: '' }
  ]);
  const [analysis, setAnalysis] = useState(null);
  const [realTimeData, setRealTimeData] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isRealTimeActive, setIsRealTimeActive] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [priceHistory, setPriceHistory] = useState({});
  const [alerts, setAlerts] = useState([]);

  // Real-time data polling
  useEffect(() => {
    let interval;
    if (isRealTimeActive && analysis) {
      interval = setInterval(() => {
        fetchRealTimeData();
      }, 5000); // Update every 5 seconds
    }
    return () => clearInterval(interval);
  }, [isRealTimeActive, analysis]);

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
    const validHoldings = holdings.filter(h => h.symbol && h.allocation);
    if (validHoldings.length === 0) {
      setError('Please add at least one stock with allocation');
      return false;
    }

    const totalAllocation = validHoldings.reduce((sum, h) => sum + parseFloat(h.allocation || 0), 0);
    if (Math.abs(totalAllocation - 100) > 0.01) {
      setError(`Total allocation must equal 100%. Current total: ${totalAllocation.toFixed(2)}%`);
      return false;
    }

    setError('');
    return true;
  };

  const fetchRealTimeData = async () => {
    if (!analysis) return;

    try {
      const validHoldings = holdings.filter(h => h.symbol && h.allocation);
      const symbols = validHoldings.map(h => h.symbol.toUpperCase());
      
      const response = await fetch('http://localhost:5000/api/realtime', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbols })
      });
      
      if (!response.ok) throw new Error('Failed to fetch real-time data');
      
      const data = await response.json();
      setRealTimeData(data.prices);
      setLastUpdate(new Date());
      
      // Update price history for charts
      setPriceHistory(prev => {
        const updated = { ...prev };
        Object.keys(data.prices).forEach(symbol => {
          if (!updated[symbol]) updated[symbol] = [];
          updated[symbol].push({
            time: new Date().toLocaleTimeString(),
            price: data.prices[symbol].price,
            change: data.prices[symbol].change_percent
          });
          // Keep only last 20 data points
          if (updated[symbol].length > 20) {
            updated[symbol] = updated[symbol].slice(-20);
          }
        });
        return updated;
      });
      
      // Check for alerts
      checkForAlerts(data.prices);
      
      // Recalculate portfolio metrics with new prices
      await updatePortfolioMetrics(data.prices);
      
    } catch (err) {
      console.error('Real-time data fetch error:', err);
    }
  };

  const checkForAlerts = (prices) => {
    const newAlerts = [];
    const alertThreshold = 2; // 2% change threshold
    
    Object.entries(prices).forEach(([symbol, data]) => {
      const changePercent = Math.abs(data.change_percent);
      if (changePercent > alertThreshold) {
        newAlerts.push({
          id: Date.now() + Math.random(),
          symbol,
          type: data.change_percent > 0 ? 'gain' : 'loss',
          change: data.change_percent,
          timestamp: new Date()
        });
      }
    });
    
    if (newAlerts.length > 0) {
      setAlerts(prev => [...newAlerts, ...prev].slice(0, 10)); // Keep last 10 alerts
    }
  };

  const updatePortfolioMetrics = async (prices) => {
    try {
      const validHoldings = holdings.filter(h => h.symbol && h.allocation);
      const portfolio = validHoldings.map(h => ({
        symbol: h.symbol.toUpperCase(),
        allocation: parseFloat(h.allocation)
      }));

      const response = await fetch('http://localhost:5000/api/analyze-realtime', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ portfolio, current_prices: prices })
      });
      
      if (!response.ok) throw new Error('Failed to update portfolio metrics');
      
      const data = await response.json();
      setAnalysis(prev => ({
        ...prev,
        ...data,
        real_time_value: data.portfolio_value,
        real_time_change: data.portfolio_change
      }));
      
    } catch (err) {
      console.error('Portfolio metrics update error:', err);
    }
  };

  const analyzePortfolio = async () => {
    if (!validatePortfolio()) return;

    setLoading(true);
    setError('');

    try {
      const validHoldings = holdings.filter(h => h.symbol && h.allocation);
      const portfolio = validHoldings.map(h => ({
        symbol: h.symbol.toUpperCase(),
        allocation: parseFloat(h.allocation)
      }));

      const response = await fetch('http://localhost:5000/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.JSON.stringify({ portfolio })
      });
      
      if (!response.ok) throw new Error('Failed to analyze portfolio');
      
      const data = await response.json();
      setAnalysis(data);
      
      // Initialize price history
      const initialHistory = {};
      portfolio.forEach(stock => {
        initialHistory[stock.symbol] = [];
      });
      setPriceHistory(initialHistory);
      
    } catch (err) {
      setError('Failed to analyze portfolio. Please try again.');
      console.error('Analysis error:', err);
    } finally {
      setLoading(false);
    }
  };

  const toggleRealTime = () => {
    setIsRealTimeActive(!isRealTimeActive);
    if (!isRealTimeActive) {
      fetchRealTimeData(); // Fetch immediately when enabled
    }
  };

  const dismissAlert = (alertId) => {
    setAlerts(prev => prev.filter(alert => alert.id !== alertId));
  };

  const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#00ff00', '#ff00ff', '#00ffff', '#ff0000'];
  const totalAllocation = holdings.reduce((sum, h) => sum + parseFloat(h.allocation || 0), 0);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-pink-800 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="bg-white/90 backdrop-blur-lg rounded-3xl shadow-2xl p-8">
          {/* Header with Real-time Status */}
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-gray-800 mb-2">
              Real-Time Portfolio Analyzer
              {isRealTimeActive && (
                <Zap className="inline ml-2 text-yellow-500 animate-pulse" size={32} />
              )}
            </h1>
            <p className="text-gray-600">Live portfolio analysis with real-time data and recommendations</p>
            {lastUpdate && (
              <p className="text-sm text-green-600 mt-2">
                Last updated: {lastUpdate.toLocaleTimeString()}
              </p>
            )}
          </div>

          {/* Real-time Alerts */}
          {alerts.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-3 flex items-center">
                <Activity className="mr-2 text-red-500" />
                Live Alerts
              </h3>
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {alerts.slice(0, 3).map(alert => (
                  <div
                    key={alert.id}
                    className={`p-3 rounded-lg flex justify-between items-center ${
                      alert.type === 'gain' ? 'bg-green-100 border-green-300' : 'bg-red-100 border-red-300'
                    } border`}
                  >
                    <span className={`font-semibold ${alert.type === 'gain' ? 'text-green-700' : 'text-red-700'}`}>
                      {alert.symbol}: {alert.change > 0 ? '+' : ''}{alert.change.toFixed(2)}%
                    </span>
                    <button
                      onClick={() => dismissAlert(alert.id)}
                      className="text-gray-500 hover:text-gray-700"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Portfolio Input Section */}
          <div className="bg-gray-50 rounded-2xl p-6 mb-8">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-semibold text-gray-800 flex items-center">
                <PieChart className="mr-2" />
                Portfolio Holdings
              </h2>
              {analysis && (
                <button
                  onClick={toggleRealTime}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg font-semibold transition-colors ${
                    isRealTimeActive 
                      ? 'bg-green-500 text-white hover:bg-green-600' 
                      : 'bg-blue-500 text-white hover:bg-blue-600'
                  }`}
                >
                  {isRealTimeActive ? (
                    <>
                      <Activity className="animate-pulse" size={20} />
                      Live Data ON
                    </>
                  ) : (
                    <>
                      <RefreshCw size={20} />
                      Enable Real-Time
                    </>
                  )}
                </button>
              )}
            </div>
            
            {holdings.map((holding, index) => (
              <div key={index} className="flex gap-4 mb-4 items-center">
                <input
                  type="text"
                  placeholder="Stock Symbol (e.g., AAPL)"
                  value={holding.symbol}
                  onChange={(e) => updateHolding(index, 'symbol', e.target.value.toUpperCase())}
                  className="flex-1 px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none transition-colors"
                />
                <div className="relative">
                  <input
                    type="number"
                    placeholder="Allocation %"
                    value={holding.allocation}
                    onChange={(e) => updateHolding(index, 'allocation', e.target.value)}
                    className="w-32 px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none transition-colors"
                    min="0"
                    max="100"
                    step="0.1"
                  />
                  <span className="absolute right-3 top-3 text-gray-500">%</span>
                </div>
                {/* Real-time price display */}
                {realTimeData[holding.symbol] && (
                  <div className="text-sm">
                    <div className="font-semibold">${realTimeData[holding.symbol].price?.toFixed(2)}</div>
                    <div className={`${realTimeData[holding.symbol].change_percent >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {realTimeData[holding.symbol].change_percent >= 0 ? '+' : ''}
                      {realTimeData[holding.symbol].change_percent?.toFixed(2)}%
                    </div>
                  </div>
                )}
                <button
                  onClick={() => removeHolding(index)}
                  disabled={holdings.length === 1}
                  className="p-3 text-red-500 hover:bg-red-50 rounded-lg disabled:text-gray-300 disabled:hover:bg-transparent transition-colors"
                >
                  <Trash2 size={20} />
                </button>
              </div>
            ))}

            <div className="flex justify-between items-center mt-6">
              <button
                onClick={addHolding}
                className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
              >
                <PlusCircle size={20} />
                Add Stock
              </button>
              
              <div className="text-right">
                <p className={`text-lg font-semibold ${Math.abs(totalAllocation - 100) < 0.01 ? 'text-green-600' : 'text-red-600'}`}>
                  Total: {totalAllocation.toFixed(1)}%
                </p>
                {analysis?.real_time_value && (
                  <p className="text-sm text-gray-600">
                    Portfolio Value: ${analysis.real_time_value.toLocaleString()}
                  </p>
                )}
                {analysis?.real_time_change && (
                  <p className={`text-sm font-semibold ${analysis.real_time_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    Today: {analysis.real_time_change >= 0 ? '+' : ''}{analysis.real_time_change.toFixed(2)}%
                  </p>
                )}
              </div>
            </div>

            {error && (
              <div className="mt-4 p-3 bg-red-100 border border-red-300 rounded-lg flex items-center">
                <AlertCircle className="text-red-500 mr-2" size={20} />
                <span className="text-red-700">{error}</span>
              </div>
            )}

            <button
              onClick={analyzePortfolio}
              disabled={loading}
              className="w-full mt-6 py-4 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-semibold rounded-lg hover:from-purple-700 hover:to-blue-700 disabled:opacity-50 transition-all transform hover:scale-105"
            >
              {loading ? 'Analyzing Portfolio...' : 'Analyze Portfolio'}
            </button>
          </div>

          {/* Real-time Price Charts */}
          {Object.keys(priceHistory).length > 0 && Object.values(priceHistory).some(history => history.length > 0) && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
              {Object.entries(priceHistory).map(([symbol, history]) => 
                history.length > 0 && (
                  <div key={symbol} className="bg-white rounded-2xl p-6 shadow-lg">
                    <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
                      <TrendingUp className="mr-2 text-blue-600" />
                      {symbol} - Live Price
                    </h3>
                    <ResponsiveContainer width="100%" height={200}>
                      <LineChart data={history}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="time" />
                        <YAxis />
                        <Tooltip />
                        <Line type="monotone" dataKey="price" stroke="#8884d8" strokeWidth={2} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )
              )}
            </div>
          )}

          {/* Analysis Results */}
          {analysis && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Portfolio Metrics */}
              <div className="bg-gradient-to-br from-green-50 to-blue-50 rounded-2xl p-6">
                <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center">
                  <TrendingUp className="mr-2 text-green-600" />
                  Portfolio Metrics
                  {isRealTimeActive && <Activity className="ml-2 text-green-500 animate-pulse" size={16} />}
                </h3>
                <div className="space-y-4">
                  <div className="flex justify-between items-center p-3 bg-white rounded-lg">
                    <span className="text-gray-700">Expected Annual Return</span>
                    <span className="font-semibold text-green-600">
                      {(analysis.portfolio_metrics.expected_return * 100).toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-white rounded-lg">
                    <span className="text-gray-700">Volatility (Risk)</span>
                    <span className="font-semibold text-orange-600">
                      {(analysis.portfolio_metrics.volatility * 100).toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-white rounded-lg">
                    <span className="text-gray-700">Sharpe Ratio</span>
                    <span className="font-semibold text-blue-600">
                      {analysis.portfolio_metrics.sharpe_ratio.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-white rounded-lg">
                    <span className="text-gray-700">Beta</span>
                    <span className="font-semibold text-purple-600">
                      {analysis.portfolio_metrics.beta.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-white rounded-lg">
                    <span className="text-gray-700">Value at Risk (95%)</span>
                    <span className="font-semibold text-red-600">
                      {(analysis.portfolio_metrics.var_95 * 100).toFixed(2)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Real-time Recommendations */}
              <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-2xl p-6">
                <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center">
                  <Shield className="mr-2 text-purple-600" />
                  Live Recommendations
                  {isRealTimeActive && <Zap className="ml-2 text-yellow-500 animate-pulse" size={16} />}
                </h3>
                <div className="space-y-4">
                  <div className="p-3 bg-white rounded-lg">
                    <span className="text-gray-700">Risk Level: </span>
                    <span className="font-semibold text-orange-600">{analysis.risk_analysis.risk_level}</span>
                  </div>
                  <div className="p-3 bg-white rounded-lg">
                    <span className="text-gray-700">Concentration Risk: </span>
                    <span className="font-semibold text-purple-600">{analysis.diversification.concentration_risk}</span>
                  </div>
                  <div className="space-y-2">
                    <h4 className="font-semibold text-gray-700">Live Recommendations:</h4>
                    <ul className="space-y-1">
                      {analysis.risk_analysis.recommendations.map((rec, i) => (
                        <li key={i} className="text-sm text-gray-600 bg-white p-2 rounded flex items-start">
                          <span className="text-blue-500 mr-2">•</span>
                          {rec}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>

              {/* Sector Allocation Chart */}
              <div className="bg-white rounded-2xl p-6 shadow-lg">
                <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center">
                  <PieChart className="mr-2 text-blue-600" />
                  Sector Allocation
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <RechartsPie
                    data={analysis.diversification.sector_allocation}
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="allocation"
                    label={({ sector, allocation }) => `${sector}: ${allocation}%`}
                  >
                    {analysis.diversification.sector_allocation.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </RechartsPie>
                  <Tooltip />
                </ResponsiveContainer>
              </div>

              {/* Holdings Chart */}
              <div className="bg-white rounded-2xl p-6 shadow-lg">
                <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center">
                  <BarChart3 className="mr-2 text-green-600" />
                  Holdings Breakdown
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={analysis.diversification.sector_allocation}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="symbol" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="allocation" fill="#8884d8" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PortfolioAnalyzer;