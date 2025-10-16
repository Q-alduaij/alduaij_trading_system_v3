# Lolo Trading Agent - Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### Step 1: Extract and Navigate

```bash
unzip lolo-trading-agent.zip
cd lolo-trading-agent
```

### Step 2: Set Up Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure API Keys

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your credentials:
# - MT5_ACCOUNT, MT5_PASSWORD, MT5_SERVER
# - OPENROUTER_API_KEY (your AI API key)
# - Market data API keys (Polygon, Finnhub, etc.)
```

**Your API Keys (from your master prompt):**
- OpenRouter API: `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`
- Market Data APIs: `48aEyv6hTIkubx8NsS9TdlfHdblpA5m5` and `WrXA_o05NNZJb7QSpnbm`

### Step 4: Configure Trading Parameters

Edit `config/instruments.yaml`:
```yaml
forex:
  enabled: true
  instruments:
    - symbol: EURUSD
      enabled: true
    - symbol: GBPUSD
      enabled: true

metals:
  enabled: true  # For gold and silver trading
  instruments:
    - symbol: XAUUSD
      enabled: true
```

Edit `config/strategies.yaml`:
```yaml
risk_management:
  max_daily_loss_percent: 0.05  # 5% max loss per day
  risk_per_trade_percent: 0.01  # 1% risk per trade
```

### Step 5: Start in Paper Trading Mode

**IMPORTANT: Always start with paper trading!**

In `.env`, set:
```
PAPER_TRADING=True
```

Then run:
```bash
python3 main.py
```

### Step 6: Access Web Dashboard (Optional)

In a new terminal:
```bash
source venv/bin/activate
python3 web/app.py
```

Open browser: `http://127.0.0.1:5000`

## 📋 What Happens When You Run It

1. **System Initialization**: Connects to MT5, initializes database, loads configurations
2. **Analysis Cycle** (every 30 minutes by default):
   - Research Agent identifies opportunities
   - Technical Agent analyzes charts
   - Fundamental Agent checks economic data
   - Sentiment Agent reads news
   - Portfolio Manager makes decision
   - Risk Agent validates safety
   - Execution Agent places trade (if approved)
3. **Daily Reflexion** (end of day): Analyzes performance and generates insights
4. **Continuous Monitoring**: Tracks open positions and market conditions

## 🛡️ Safety Features

- **Paper Trading Mode**: Test without real money
- **Daily Loss Limit**: Stops trading if 5% daily loss reached
- **Maximum Drawdown**: Pauses if 20% drawdown from peak
- **Position Limits**: Max 10 open positions, 2 per instrument
- **Emergency Stop**: Web dashboard button to close all positions

## 📊 Monitoring Your Agent

### Via Console
- Watch the terminal for real-time logs
- See each agent's analysis and reasoning
- Monitor trade execution

### Via Web Dashboard
- Real-time account balance and equity
- Performance metrics (win rate, profit)
- Open positions table
- Trade history
- AI-generated insights

## ⚙️ Key Configuration Files

| File | Purpose |
|------|---------|
| `.env` | API keys and credentials |
| `config/instruments.yaml` | Trading instruments |
| `config/strategies.yaml` | Risk and trading parameters |
| `config/settings.py` | System settings |

## 🔧 Customization

### Change Analysis Frequency
In `config/settings.py`:
```python
ANALYSIS_INTERVAL_MINUTES = 30  # Change to 15, 60, etc.
```

### Change Trading Hours
```python
TRADING_START_HOUR = 0   # 24-hour format
TRADING_END_HOUR = 23
```

### Adjust Risk Parameters
In `config/strategies.yaml`:
```yaml
risk_management:
  max_daily_loss_percent: 0.03  # More conservative: 3%
  risk_per_trade_percent: 0.005  # Smaller positions: 0.5%
```

## 🐛 Troubleshooting

### MT5 Connection Failed
- Ensure MetaTrader 5 is installed and running
- Check MT5 credentials in `.env`
- Verify MT5 allows automated trading (Tools > Options > Expert Advisors)

### API Errors
- Verify API keys in `.env`
- Check API rate limits
- Ensure internet connection is stable

### No Trades Being Placed
- Check if within trading hours
- Verify `PAPER_TRADING=True` is set
- Review logs for agent reasoning
- Ensure instruments are enabled in `config/instruments.yaml`

## 📈 Going Live (After Testing)

**ONLY after at least 1 month of successful paper trading:**

1. Review all paper trading results
2. Verify win rate and profitability
3. Check risk management effectiveness
4. Set `PAPER_TRADING=False` in `.env`
5. Start with minimum position sizes
6. Monitor closely for first week
7. Gradually increase position sizes

## 📚 Further Reading

- [Full Documentation](docs/01_introduction.md)
- [Architecture Details](docs/04_architecture.md)
- [Development Guide](docs/06_development.md)

## ⚠️ Final Warning

**Trading involves significant risk. This system is for educational purposes. You are solely responsible for all trading decisions and outcomes. Never trade with money you cannot afford to lose.**

---

**Need Help?** Check the documentation or open an issue on GitHub.

