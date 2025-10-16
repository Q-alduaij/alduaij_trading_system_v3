# 🤖 Lolo Trading Agent

**AI-Powered Multi-Agent Trading System for MetaTrader 5**

## ⚠️ Disclaimer

**Trading involves significant risk of loss and is not suitable for all investors. You are solely responsible for all trading decisions and outcomes. This software is provided for educational and experimental purposes only. Use at your own risk.**

## 📋 Overview

The Lolo Trading Agent is an advanced, AI-powered automated trading system designed for the MetaTrader 5 platform. It leverages a multi-agent architecture where seven specialized AI agents collaborate to analyze markets, manage risk, and execute trades autonomously.

### Key Features

- **Multi-Agent AI System**: Seven specialized agents for research, technical analysis, fundamental analysis, sentiment analysis, risk management, execution, and portfolio management
- **LLM-Powered Decisions**: Uses DeepSeek LLM via OpenRouter for advanced reasoning and decision-making
- **Comprehensive Data Integration**: Multiple market data APIs (Polygon, Finnhub, Alpha Vantage, TwelveData, FMP) with fallback mechanisms
- **News & Sentiment Analysis**: Real-time news collection and sentiment analysis from multiple sources
- **Economic Calendar Integration**: Monitors high-impact economic events from Forex Factory
- **Robust Risk Management**: Strict position sizing, daily loss limits, drawdown protection, and correlation checks
- **Real-Time Web Dashboard**: Flask-based interface with WebSocket updates for live monitoring
- **Continuous Learning**: Reflexion module for daily performance analysis and improvement
- **Advanced Memory System**: SQLite database + ChromaDB vector store for RAG (Retrieval-Augmented Generation)
- **Technical Indicators**: RSI, MACD, Bollinger Bands, Stochastic, ATR, Moving Averages, and more

## 🏗️ Architecture

The system uses a multi-agent architecture orchestrated by the Portfolio Manager:

1. **Research Agent**: Scans the market for potential trading opportunities
2. **Technical Agent**: Performs technical analysis on selected instruments
3. **Fundamental Agent**: Analyzes macroeconomic data and central bank policies
4. **Sentiment Agent**: Gathers and analyzes news sentiment and economic events
5. **Portfolio Manager**: Aggregates analysis from all agents and makes the final trading decision using an LLM
6. **Risk Agent**: Assesses the risk of the proposed trade and calculates position size
7. **Execution Agent**: Executes the trade on the MT5 platform

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- MetaTrader 5 terminal installed
- Git

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/lolo-trading-agent.git
   cd lolo-trading-agent
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and MT5 credentials
   ```

5. **Configure instruments and strategies:**
   - Edit `config/instruments.yaml` to enable/disable trading instruments
   - Edit `config/strategies.yaml` to adjust risk parameters

### Running the Agent

**Main Trading Agent:**
```bash
python3 main.py
```

**Web Dashboard:**
```bash
python3 web/app.py
```
Then navigate to `http://127.0.0.1:5000` in your browser.

## 📖 Documentation

Comprehensive documentation is available in the `docs/` directory:

- [01 - Introduction](docs/01_introduction.md)
- [02 - Installation](docs/02_installation.md)
- [03 - Configuration](docs/03_configuration.md)
- [04 - Architecture](docs/04_architecture.md)
- [05 - Usage](docs/05_usage.md)
- [06 - Development](docs/06_development.md)

## 🔧 Configuration

### Risk Management Parameters

```yaml
risk_management:
  max_daily_loss_percent: 0.05      # 5% max daily loss
  max_drawdown_percent: 0.20        # 20% max drawdown
  risk_per_trade_percent: 0.01      # 1% risk per trade
  max_open_positions: 10
  max_positions_per_instrument: 2
```

### Trading Schedule

```python
TRADING_START_HOUR = 0    # Start at midnight
TRADING_END_HOUR = 23     # End at 11 PM
ANALYSIS_INTERVAL_MINUTES = 30  # Analyze every 30 minutes
```

## 🧪 Paper Trading Mode

The system includes a paper trading mode for testing without real money:

```python
PAPER_TRADING = True  # Set in .env or config/settings.py
```

## 📊 Web Dashboard Features

- **Real-time Account Monitoring**: Balance, equity, profit, margin level
- **Performance Metrics**: Total trades, win rate, total profit
- **Open Positions**: Live view of all open positions
- **Trade History**: Recent closed trades
- **Learning Insights**: AI-generated insights from daily reflexion
- **Control Panel**: Start, stop, and emergency stop buttons

## 🔐 Security

- All API keys and credentials are stored in `.env` (never committed to Git)
- `.gitignore` configured to exclude sensitive files
- Database and logs are excluded from version control

## 📝 License

This project is licensed under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Support

For questions or issues, please open an issue on GitHub.

## 🙏 Acknowledgments

- MetaTrader 5 Python API
- OpenRouter for LLM access
- Market data providers: Polygon, Finnhub, Alpha Vantage, TwelveData, FMP
- News APIs: NewsAPI, Forex Factory

---

**Built with ❤️ for automated trading enthusiasts**

