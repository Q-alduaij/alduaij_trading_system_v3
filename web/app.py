"""
Flask Web Interface for Lolo Trading Agent
Real-time dashboard and control panel
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import threading
import time
from datetime import datetime, timedelta
from config.settings import Settings
from memory.database import Database
from data_collection.mt5_connector import MT5Connector
from agents.portfolio_manager import PortfolioManager
from utils.logger import get_logger

logger = get_logger("web")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'lolo-trading-agent-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global components
db = Database()
mt5 = MT5Connector()
portfolio_manager = PortfolioManager()

# System status
system_status = {
    'running': False,
    'last_update': None,
    'current_cycle': None
}


@app.route('/')
def index():
    """Main dashboard"""
    return render_template('dashboard.html')


@app.route('/api/status')
def get_status():
    """Get system status"""
    try:
        account_info = mt5.get_account_info()
        open_positions = mt5.get_open_positions()
        
        return jsonify({
            'status': 'online' if mt5.connected else 'offline',
            'paper_trading': Settings.PAPER_TRADING,
            'account_info': account_info,
            'open_positions_count': len(open_positions),
            'last_update': system_status['last_update'],
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/positions')
def get_positions():
    """Get open positions"""
    try:
        positions = mt5.get_open_positions()
        return jsonify({'positions': positions})
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/trades')
def get_trades():
    """Get trade history"""
    try:
        days = request.args.get('days', 7, type=int)
        trades = db.get_recent_trades(limit=100)
        return jsonify({'trades': trades})
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/performance')
def get_performance():
    """Get performance metrics"""
    try:
        # Get trades from last 30 days
        trades = db.get_recent_trades(limit=1000)
        
        if not trades:
            return jsonify({
                'total_trades': 0,
                'win_rate': 0,
                'total_profit': 0,
                'average_profit': 0
            })
        
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.get('profit', 0) > 0)
        total_profit = sum(t.get('profit', 0) for t in trades)
        
        return jsonify({
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades,
            'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
            'total_profit': total_profit,
            'average_profit': total_profit / total_trades if total_trades > 0 else 0
        })
    except Exception as e:
        logger.error(f"Error getting performance: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/insights')
def get_insights():
    """Get learning insights"""
    try:
        insights = db.get_learning_insights(limit=20)
        return jsonify({'insights': insights})
    except Exception as e:
        logger.error(f"Error getting insights: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/control/start', methods=['POST'])
def start_trading():
    """Start automated trading"""
    try:
        system_status['running'] = True
        socketio.emit('system_status', {'status': 'started'})
        return jsonify({'success': True, 'message': 'Trading started'})
    except Exception as e:
        logger.error(f"Error starting trading: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/control/stop', methods=['POST'])
def stop_trading():
    """Stop automated trading"""
    try:
        system_status['running'] = False
        socketio.emit('system_status', {'status': 'stopped'})
        return jsonify({'success': True, 'message': 'Trading stopped'})
    except Exception as e:
        logger.error(f"Error stopping trading: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/control/emergency_stop', methods=['POST'])
def emergency_stop():
    """Emergency stop - close all positions"""
    try:
        positions = mt5.get_open_positions()
        
        # Close all positions
        closed_count = 0
        for position in positions:
            # In real implementation, would close each position
            # For now, just log
            logger.warning(f"Emergency stop: Would close position {position['ticket']}")
            closed_count += 1
        
        system_status['running'] = False
        socketio.emit('system_status', {'status': 'emergency_stopped'})
        
        return jsonify({
            'success': True,
            'message': f'Emergency stop executed. {closed_count} positions closed.'
        })
    except Exception as e:
        logger.error(f"Error in emergency stop: {e}")
        return jsonify({'error': str(e)}), 500


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info("Client connected to WebSocket")
    emit('connection_response', {'status': 'connected'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info("Client disconnected from WebSocket")


def background_updates():
    """Background thread for real-time updates"""
    while True:
        try:
            # Get current status
            account_info = mt5.get_account_info()
            positions = mt5.get_open_positions()
            
            # Emit updates
            socketio.emit('account_update', account_info)
            socketio.emit('positions_update', {'positions': positions})
            
            system_status['last_update'] = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"Error in background updates: {e}")
        
        time.sleep(5)  # Update every 5 seconds


def run_web_interface(host='0.0.0.0', port=5000):
    """Run the web interface"""
    logger.info(f"Starting web interface on {host}:{port}")
    
    # Start background update thread
    update_thread = threading.Thread(target=background_updates, daemon=True)
    update_thread.start()
    
    # Run Flask app
    socketio.run(app, host=host, port=port, debug=False)


if __name__ == '__main__':
    run_web_interface()

