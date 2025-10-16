// Dashboard JavaScript for Lolo Trading Agent

const socket = io();

// Update status indicator
function updateStatus(status) {
    const indicator = document.getElementById('status-indicator');
    const dot = indicator.querySelector('.status-dot');
    const text = indicator.querySelector('.status-text');
    
    dot.className = 'status-dot ' + status;
    text.textContent = status.charAt(0).toUpperCase() + status.slice(1);
}

// Format currency
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(value);
}

// Format percentage
function formatPercent(value) {
    return (value * 100).toFixed(2) + '%';
}

// Update account info
function updateAccountInfo(data) {
    if (!data) return;
    
    document.getElementById('balance').textContent = formatCurrency(data.balance || 0);
    document.getElementById('equity').textContent = formatCurrency(data.equity || 0);
    
    const profit = data.profit || 0;
    const profitEl = document.getElementById('profit');
    profitEl.textContent = formatCurrency(profit);
    profitEl.className = 'value ' + (profit >= 0 ? 'profit' : 'loss');
    
    const marginLevel = data.margin_level || 0;
    document.getElementById('margin-level').textContent = marginLevel.toFixed(2) + '%';
}

// Update positions table
function updatePositions(positions) {
    const tbody = document.getElementById('positions-tbody');
    const count = document.getElementById('positions-count');
    
    count.textContent = positions.length;
    
    if (positions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="no-data">No open positions</td></tr>';
        return;
    }
    
    tbody.innerHTML = positions.map(pos => `
        <tr>
            <td>${pos.ticket}</td>
            <td><strong>${pos.symbol}</strong></td>
            <td>${pos.type.toUpperCase()}</td>
            <td>${pos.volume}</td>
            <td>${pos.open_price.toFixed(5)}</td>
            <td>${pos.current_price.toFixed(5)}</td>
            <td class="${pos.profit >= 0 ? 'profit' : 'loss'}">${formatCurrency(pos.profit)}</td>
        </tr>
    `).join('');
}

// Update trades table
function updateTrades(trades) {
    const tbody = document.getElementById('trades-tbody');
    
    if (trades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="no-data">No recent trades</td></tr>';
        return;
    }
    
    tbody.innerHTML = trades.slice(0, 20).map(trade => {
        const time = new Date(trade.timestamp || trade.created_at).toLocaleString();
        return `
            <tr>
                <td>${time}</td>
                <td><strong>${trade.instrument}</strong></td>
                <td>${trade.action.toUpperCase()}</td>
                <td>${trade.volume}</td>
                <td>${(trade.entry_price || 0).toFixed(5)}</td>
                <td>${(trade.exit_price || 0).toFixed(5)}</td>
                <td class="${(trade.profit || 0) >= 0 ? 'profit' : 'loss'}">${formatCurrency(trade.profit || 0)}</td>
            </tr>
        `;
    }).join('');
}

// Update performance metrics
function updatePerformance(data) {
    document.getElementById('total-trades').textContent = data.total_trades || 0;
    document.getElementById('win-rate').textContent = formatPercent(data.win_rate || 0);
    
    const totalProfit = data.total_profit || 0;
    const profitEl = document.getElementById('total-profit');
    profitEl.textContent = formatCurrency(totalProfit);
    profitEl.className = 'metric-value ' + (totalProfit >= 0 ? 'profit' : 'loss');
}

// Update insights
function updateInsights(insights) {
    const container = document.getElementById('insights-container');
    
    if (insights.length === 0) {
        container.innerHTML = '<p class="no-data">No insights available</p>';
        return;
    }
    
    container.innerHTML = insights.map(insight => `
        <div class="insight-item">
            <div class="insight-content">${insight.content}</div>
            <div class="insight-meta">
                <span>Category: ${insight.insight_type}</span>
                <span>Confidence: ${formatPercent(insight.confidence || 0.5)}</span>
                <span>${new Date(insight.created_at).toLocaleDateString()}</span>
            </div>
        </div>
    `).join('');
}

// Fetch and update all data
async function fetchData() {
    try {
        // Status
        const statusRes = await fetch('/api/status');
        const statusData = await statusRes.json();
        updateStatus(statusData.status);
        updateAccountInfo(statusData.account_info);
        
        // Positions
        const posRes = await fetch('/api/positions');
        const posData = await posRes.json();
        updatePositions(posData.positions || []);
        
        // Trades
        const tradesRes = await fetch('/api/trades');
        const tradesData = await tradesRes.json();
        updateTrades(tradesData.trades || []);
        
        // Performance
        const perfRes = await fetch('/api/performance');
        const perfData = await perfRes.json();
        updatePerformance(perfData);
        
        // Insights
        const insightsRes = await fetch('/api/insights');
        const insightsData = await insightsRes.json();
        updateInsights(insightsData.insights || []);
        
    } catch (error) {
        console.error('Error fetching data:', error);
        updateStatus('offline');
    }
}

// Control buttons
document.getElementById('btn-start').addEventListener('click', async () => {
    try {
        const res = await fetch('/api/control/start', { method: 'POST' });
        const data = await res.json();
        alert(data.message);
    } catch (error) {
        alert('Error starting trading: ' + error.message);
    }
});

document.getElementById('btn-stop').addEventListener('click', async () => {
    try {
        const res = await fetch('/api/control/stop', { method: 'POST' });
        const data = await res.json();
        alert(data.message);
    } catch (error) {
        alert('Error stopping trading: ' + error.message);
    }
});

document.getElementById('btn-emergency').addEventListener('click', async () => {
    if (!confirm('Are you sure you want to execute emergency stop? This will close all positions!')) {
        return;
    }
    
    try {
        const res = await fetch('/api/control/emergency_stop', { method: 'POST' });
        const data = await res.json();
        alert(data.message);
        fetchData(); // Refresh data
    } catch (error) {
        alert('Error executing emergency stop: ' + error.message);
    }
});

// WebSocket event handlers
socket.on('connect', () => {
    console.log('Connected to server');
    updateStatus('online');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    updateStatus('offline');
});

socket.on('account_update', (data) => {
    updateAccountInfo(data);
});

socket.on('positions_update', (data) => {
    updatePositions(data.positions || []);
});

socket.on('system_status', (data) => {
    console.log('System status:', data.status);
});

// Initial data fetch
fetchData();

// Refresh data every 10 seconds
setInterval(fetchData, 10000);

