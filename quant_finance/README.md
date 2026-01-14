## QuantWise – Real-Time Portfolio Risk & Return Analyzer

QuantWise is a small, focused web app that helps you **understand the risk and return of your real stock/ETF portfolio** using live market data from the Twelve Data API.  
You enter your holdings and allocations; QuantWise pulls historical prices and computes clean portfolio analytics you can actually use.

---

### ✅ Current Capabilities (MVP)

- Input a portfolio of stocks/ETFs with **percentage weights**.
- Fetch recent **daily closing prices** for each symbol from Twelve Data.
- Compute core **portfolio statistics** based on those real returns:
  - Expected annual return
  - Annualised volatility (risk)
  - Sharpe ratio (risk-adjusted return vs a 2% risk-free rate)
- Build a **normalized equity curve** of the portfolio over time.
- Visualise everything in a polished React UI:
  - Portfolio snapshot card (return, volatility, Sharpe)
  - Allocation pie chart
  - Portfolio value history line chart

There is **no mock data** in production paths: if the API key is missing or a symbol is invalid, the backend returns a clear error and the UI surfaces it to the user.

---

### 🧠 Tech Stack

- **Backend**
  - Python, Flask, Flask-CORS
  - NumPy, Pandas
  - Twelve Data HTTP API
  - `python-dotenv` for environment configuration

- **Frontend**
  - React + Vite
  - Tailwind-style utility classes
  - `lucide-react` icons
  - `recharts` for charts

---

### 📁 Key Files

- `api.py` – Flask backend exposing:
  - `GET /api/health` – health check
  - `POST /api/analyze` – portfolio analytics using live Twelve Data prices
- `quantwise-frontend/src/pages/AnalysePortfolio.jsx` – main Portfolio Analyzer UI.
- `quantwise-frontend/src/App.jsx` – wires the analyzer into the landing page.

`predictor.py` currently contains **experimental forecasting models** (Prophet/ARIMA/LSTM) and is not wired into the MVP API yet. It is kept as a playground for future AI/ML features.

---

### 🔐 Configure Your Twelve Data API Key

1. Create a Twelve Data account and get an API key.
2. In the `quant_finance` folder, create a `.env` file:

   ```bash
   TWELVE_DATA_API_KEY=YOUR_REAL_KEY_HERE
   ```

3. The backend loads this automatically via `python-dotenv`.
4. If the key is missing or invalid, `/api/analyze` will return a 400/500 error with a clear message.

---

### 🛠 Run the Backend

From the `quant_finance` directory:

```bash
python -m venv venv            # first time
venv\Scripts\activate          # Windows (or `source venv/bin/activate` on macOS/Linux)
pip install -r requirements.txt
python api.py
```

The backend will start on `http://localhost:5001`.
You can verify it with:

```text
GET http://localhost:5001/api/health
→ {"status": "ok"}
```

---

### 💻 Run the Frontend

From `quant_finance/quantwise-frontend`:

```bash
npm install
npm run dev
```

Then open the Vite dev URL (usually `http://localhost:5173`) in your browser and scroll to the **Portfolio Analyzer** section.

- A sample portfolio (AAPL, MSFT, GOOG, TSLA) is pre-filled.
- Adjust tickers and weights to match your real holdings.
- Click **Run analysis** to fetch live data and update metrics and charts.

---

### 🎯 Planned AI/ML Enhancements

These are the next realistic features we intend to add to make QuantWise more valuable:

- Monte Carlo simulations of future portfolio values using historical return distributions.
- Maximum drawdown and downside deviation metrics for more realistic risk assessment.
- Diversification and correlation analysis between holdings.
- Simple, rule-based risk classification with human-readable explanations.
- Single-symbol price forecasts (Prophet/ARIMA) and basic stress-test scenarios.


