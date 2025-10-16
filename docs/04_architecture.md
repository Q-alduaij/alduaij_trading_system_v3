'''## 4. Architecture

The Lolo Trading Agent is built on a modular, multi-agent architecture.

### 4.1. Core Components

- **Main Application (`main.py`)**: The main entry point that runs the trading loop.
- **Configuration (`config/`)**: Manages all settings and parameters.
- **Utilities (`utils/`)**: Helper functions, logging, and notifications.
- **Data Collection (`data_collection/`)**: Modules for connecting to MT5 and external data APIs.
- **Analysis (`analysis/`)**: Tools for technical, fundamental, sentiment, and correlation analysis.
- **Memory (`memory/`)**: Manages the agent's memory, including a relational database (SQLite) and a vector store (ChromaDB) for RAG.
- **Learning (`learning/`)**: The reflexion module for continuous improvement.
- **Web Interface (`web/`)**: The Flask and SocketIO-based dashboard.

### 4.2. Multi-Agent System (`agents/`)

The core of the system is the multi-agent team, orchestrated by the Portfolio Manager:

1.  **Research Agent**: Scans the market for potential trading opportunities.
2.  **Technical Agent**: Performs technical analysis on selected instruments.
3.  **Fundamental Agent**: Analyzes macroeconomic data and central bank policies.
4.  **Sentiment Agent**: Gathers and analyzes news sentiment and economic events.
5.  **Portfolio Manager**: Aggregates analysis from all agents and makes the final trading decision using an LLM.
6.  **Risk Agent**: Assesses the risk of the proposed trade and calculates position size.
7.  **Execution Agent**: Executes the trade on the MT5 platform.
'''
