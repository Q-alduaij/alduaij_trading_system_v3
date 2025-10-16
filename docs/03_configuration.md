'''## 3. Configuration

The agent's behavior is configured through environment variables (`.env`) and YAML files in the `config/` directory.

### 3.1. Environment Variables (`.env`)

- **MT5_ACCOUNT**: Your MetaTrader 5 account number.
- **MT5_PASSWORD**: Your MetaTrader 5 account password.
- **MT5_SERVER**: Your broker's server name.
- **OPENROUTER_API_KEY**: Your API key for OpenRouter (for LLM access).
- **... (and other API keys)**: Keys for Polygon, Finnhub, NewsAPI, etc.

### 3.2. Instruments (`config/instruments.yaml`)

This file defines the trading instruments the agent will consider. You can enable or disable categories (forex, metals, etc.) and individual instruments.

```yaml
forex:
  enabled: true
  instruments:
    - symbol: EURUSD
      enabled: true
    - symbol: GBPUSD
      enabled: true
```

### 3.3. Strategies (`config/strategies.yaml`)

This file configures risk management and trading parameters.

```yaml
risk_management:
  max_daily_loss_percent: 0.05  # 5%
  max_drawdown_percent: 0.20    # 20%
  risk_per_trade_percent: 0.01  # 1%

trading:
  max_open_positions: 10
  max_positions_per_instrument: 2
```
'''
