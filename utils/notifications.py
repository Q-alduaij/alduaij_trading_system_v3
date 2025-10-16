"""
Notification Manager
Handles system notifications and alerts
"""

from typing import List, Dict, Any
from datetime import datetime
from enum import Enum
from utils.logger import get_logger

logger = get_logger("main")


class NotificationType(Enum):
    """Notification types"""
    TRADE_EXECUTED = "trade_executed"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    SYSTEM_ERROR = "system_error"
    HIGH_CONFIDENCE_OPPORTUNITY = "high_confidence_opportunity"
    UNUSUAL_MARKET_CONDITIONS = "unusual_market_conditions"
    WEEKLY_LOSS_LIMIT = "weekly_loss_limit"
    DRAWDOWN_WARNING = "drawdown_warning"
    CONNECTION_LOST = "connection_lost"
    CONNECTION_RESTORED = "connection_restored"


class Notification:
    """Notification object"""
    
    def __init__(
        self,
        notification_type: NotificationType,
        title: str,
        message: str,
        severity: str = "info",
        data: Dict[str, Any] = None
    ):
        self.id = datetime.now().timestamp()
        self.type = notification_type
        self.title = title
        self.message = message
        self.severity = severity  # info, warning, error, critical
        self.data = data or {}
        self.timestamp = datetime.now()
        self.read = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary"""
        return {
            'id': self.id,
            'type': self.type.value,
            'title': self.title,
            'message': self.message,
            'severity': self.severity,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
            'read': self.read
        }


class NotificationManager:
    """Manages system notifications"""
    
    def __init__(self, max_notifications: int = 100):
        self.notifications: List[Notification] = []
        self.max_notifications = max_notifications
        self.listeners = []
    
    def add_notification(
        self,
        notification_type: NotificationType,
        title: str,
        message: str,
        severity: str = "info",
        data: Dict[str, Any] = None
    ):
        """
        Add a new notification
        
        Args:
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            severity: Severity level (info, warning, error, critical)
            data: Additional data
        """
        notification = Notification(notification_type, title, message, severity, data)
        self.notifications.insert(0, notification)
        
        # Limit number of stored notifications
        if len(self.notifications) > self.max_notifications:
            self.notifications = self.notifications[:self.max_notifications]
        
        # Log notification
        log_level = {
            'info': logger.info,
            'warning': logger.warning,
            'error': logger.error,
            'critical': logger.critical
        }.get(severity, logger.info)
        
        log_level(f"[{notification_type.value}] {title}: {message}")
        
        # Notify listeners (for WebSocket updates)
        self._notify_listeners(notification)
    
    def get_notifications(self, limit: int = 20, unread_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get recent notifications
        
        Args:
            limit: Maximum number of notifications to return
            unread_only: Only return unread notifications
            
        Returns:
            List of notification dictionaries
        """
        notifications = self.notifications
        
        if unread_only:
            notifications = [n for n in notifications if not n.read]
        
        return [n.to_dict() for n in notifications[:limit]]
    
    def mark_as_read(self, notification_id: float):
        """Mark notification as read"""
        for notification in self.notifications:
            if notification.id == notification_id:
                notification.read = True
                break
    
    def mark_all_as_read(self):
        """Mark all notifications as read"""
        for notification in self.notifications:
            notification.read = False
    
    def clear_notifications(self):
        """Clear all notifications"""
        self.notifications = []
    
    def add_listener(self, callback):
        """Add a listener for new notifications (for WebSocket)"""
        self.listeners.append(callback)
    
    def _notify_listeners(self, notification: Notification):
        """Notify all listeners of new notification"""
        for listener in self.listeners:
            try:
                listener(notification.to_dict())
            except Exception as e:
                logger.error(f"Error notifying listener: {e}")
    
    # Convenience methods for common notifications
    
    def notify_trade_executed(self, trade_data: Dict[str, Any]):
        """Notify that a trade was executed"""
        self.add_notification(
            NotificationType.TRADE_EXECUTED,
            "Trade Executed",
            f"{trade_data.get('action', 'Trade')} {trade_data.get('instrument', 'Unknown')} at {trade_data.get('price', 'N/A')}",
            severity="info",
            data=trade_data
        )
    
    def notify_daily_loss_limit(self, loss_amount: float, limit: float):
        """Notify that daily loss limit was reached"""
        self.add_notification(
            NotificationType.DAILY_LOSS_LIMIT,
            "Daily Loss Limit Reached",
            f"Daily loss of ${abs(loss_amount):.2f} has reached the limit of ${limit:.2f}. Trading paused.",
            severity="critical",
            data={'loss': loss_amount, 'limit': limit}
        )
    
    def notify_system_error(self, error_message: str, error_data: Dict[str, Any] = None):
        """Notify of system error"""
        self.add_notification(
            NotificationType.SYSTEM_ERROR,
            "System Error",
            error_message,
            severity="error",
            data=error_data or {}
        )
    
    def notify_high_confidence_opportunity(self, opportunity_data: Dict[str, Any]):
        """Notify of high-confidence trading opportunity"""
        self.add_notification(
            NotificationType.HIGH_CONFIDENCE_OPPORTUNITY,
            "High Confidence Opportunity",
            f"High confidence {opportunity_data.get('action', 'trade')} opportunity for {opportunity_data.get('instrument', 'Unknown')}",
            severity="info",
            data=opportunity_data
        )
    
    def notify_unusual_market_conditions(self, condition_description: str, data: Dict[str, Any] = None):
        """Notify of unusual market conditions"""
        self.add_notification(
            NotificationType.UNUSUAL_MARKET_CONDITIONS,
            "Unusual Market Conditions",
            condition_description,
            severity="warning",
            data=data or {}
        )
    
    def notify_connection_lost(self, connection_type: str):
        """Notify that connection was lost"""
        self.add_notification(
            NotificationType.CONNECTION_LOST,
            "Connection Lost",
            f"Lost connection to {connection_type}. Attempting to reconnect...",
            severity="error",
            data={'connection_type': connection_type}
        )
    
    def notify_connection_restored(self, connection_type: str):
        """Notify that connection was restored"""
        self.add_notification(
            NotificationType.CONNECTION_RESTORED,
            "Connection Restored",
            f"Connection to {connection_type} has been restored.",
            severity="info",
            data={'connection_type': connection_type}
        )


# Global notification manager instance
notification_manager = NotificationManager()

