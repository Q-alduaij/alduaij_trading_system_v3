## 5. Usage

### 5.1. Running the Agent

To run the trading agent, execute the `main.py` script:

```bash
python3 main.py
```

The agent will start, connect to MT5, and begin its analysis loop according to the configured interval.

### 5.2. Web Dashboard

To use the web dashboard, run the `app.py` script in the `web/` directory:

```bash
python3 web/app.py
```

Navigate to `http://127.0.0.1:5000` in your web browser to view the dashboard.

The dashboard provides:

-   Real-time account status and performance metrics.
-   A view of open positions and recent trades.
-   Controls to start, stop, and emergency-stop the agent.
-   A log of the agent's learning insights.

