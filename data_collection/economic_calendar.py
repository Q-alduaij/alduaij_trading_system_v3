"""
Economic Calendar
Fetches and monitors economic events from Forex Factory
"""

import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import pytz
from config.settings import Settings
from utils.logger import get_logger

logger = get_logger("api")


class EconomicCalendar:
    """Economic calendar integration with Forex Factory"""
    
    def __init__(self):
        self.calendar_url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        self.events_cache = []
        self.last_update = None
        self.cache_duration = 3600  # 1 hour
    
    def fetch_events(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch economic events from Forex Factory
        
        Args:
            force_refresh: Force refresh even if cache is valid
            
        Returns:
            List of economic events
        """
        # Check cache
        if not force_refresh and self.last_update:
            if (datetime.now() - self.last_update).total_seconds() < self.cache_duration:
                return self.events_cache
        
        try:
            response = requests.get(self.calendar_url, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            events = []
            for event in data:
                try:
                    events.append({
                        'title': event.get('title', ''),
                        'country': event.get('country', ''),
                        'date': event.get('date', ''),
                        'time': event.get('time', ''),
                        'impact': event.get('impact', ''),  # Low, Medium, High
                        'forecast': event.get('forecast', ''),
                        'previous': event.get('previous', ''),
                        'actual': event.get('actual', ''),
                        'currency': event.get('currency', '')
                    })
                except Exception as e:
                    logger.debug(f"Error parsing event: {e}")
                    continue
            
            self.events_cache = events
            self.last_update = datetime.now()
            
            logger.info(f"Fetched {len(events)} economic events from Forex Factory")
            return events
            
        except Exception as e:
            logger.error(f"Error fetching economic calendar: {e}")
            return self.events_cache  # Return cached data on error
    
    def get_high_impact_events(
        self,
        hours_ahead: int = 24,
        force_refresh: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get high-impact events in the next N hours
        
        Args:
            hours_ahead: Hours to look ahead
            force_refresh: Force refresh calendar
            
        Returns:
            List of high-impact events
        """
        events = self.fetch_events(force_refresh)
        
        high_impact = []
        now = datetime.now(pytz.timezone(Settings.TIMEZONE))
        cutoff_time = now + timedelta(hours=hours_ahead)
        
        for event in events:
            # Filter by impact level
            if event.get('impact', '').lower() != 'high':
                continue
            
            # Parse event datetime
            try:
                event_date = event.get('date', '')
                event_time = event.get('time', '')
                
                if not event_date or not event_time:
                    continue
                
                # Combine date and time
                event_datetime_str = f"{event_date} {event_time}"
                event_datetime = datetime.strptime(event_datetime_str, "%Y-%m-%d %H:%M")
                event_datetime = pytz.timezone('UTC').localize(event_datetime)
                event_datetime = event_datetime.astimezone(pytz.timezone(Settings.TIMEZONE))
                
                # Check if event is within time window
                if now <= event_datetime <= cutoff_time:
                    event['event_datetime'] = event_datetime
                    high_impact.append(event)
                    
            except Exception as e:
                logger.debug(f"Error parsing event datetime: {e}")
                continue
        
        logger.info(f"Found {len(high_impact)} high-impact events in next {hours_ahead} hours")
        return high_impact
    
    def should_pause_trading(
        self,
        pause_before_minutes: int = 15,
        pause_after_minutes: int = 15
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if trading should be paused due to upcoming high-impact event
        
        Args:
            pause_before_minutes: Minutes before event to pause
            pause_after_minutes: Minutes after event to pause
            
        Returns:
            Tuple of (should_pause, event_info)
        """
        events = self.get_high_impact_events(hours_ahead=1)
        
        now = datetime.now(pytz.timezone(Settings.TIMEZONE))
        
        for event in events:
            event_datetime = event.get('event_datetime')
            if not event_datetime:
                continue
            
            # Calculate time difference
            time_diff = (event_datetime - now).total_seconds() / 60  # minutes
            
            # Check if we're in the pause window
            if -pause_after_minutes <= time_diff <= pause_before_minutes:
                logger.warning(f"Trading paused due to high-impact event: {event['title']} at {event_datetime}")
                return True, event
        
        return False, None
    
    def get_upcoming_events(
        self,
        hours: int = 24,
        min_impact: str = "Medium"
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming events filtered by impact level
        
        Args:
            hours: Hours to look ahead
            min_impact: Minimum impact level (Low, Medium, High)
            
        Returns:
            List of upcoming events
        """
        events = self.fetch_events()
        
        impact_levels = {'Low': 1, 'Medium': 2, 'High': 3}
        min_impact_value = impact_levels.get(min_impact, 2)
        
        upcoming = []
        now = datetime.now(pytz.timezone(Settings.TIMEZONE))
        cutoff_time = now + timedelta(hours=hours)
        
        for event in events:
            # Filter by impact
            event_impact = event.get('impact', '')
            event_impact_value = impact_levels.get(event_impact, 0)
            
            if event_impact_value < min_impact_value:
                continue
            
            # Parse datetime
            try:
                event_date = event.get('date', '')
                event_time = event.get('time', '')
                
                if not event_date or not event_time:
                    continue
                
                event_datetime_str = f"{event_date} {event_time}"
                event_datetime = datetime.strptime(event_datetime_str, "%Y-%m-%d %H:%M")
                event_datetime = pytz.timezone('UTC').localize(event_datetime)
                event_datetime = event_datetime.astimezone(pytz.timezone(Settings.TIMEZONE))
                
                if now <= event_datetime <= cutoff_time:
                    event['event_datetime'] = event_datetime
                    event['time_until'] = str(event_datetime - now)
                    upcoming.append(event)
                    
            except Exception as e:
                logger.debug(f"Error parsing event: {e}")
                continue
        
        # Sort by datetime
        upcoming.sort(key=lambda x: x.get('event_datetime', now))
        
        return upcoming
    
    def get_events_summary(self) -> Dict[str, Any]:
        """
        Get summary of economic events
        
        Returns:
            Summary dictionary
        """
        events = self.fetch_events()
        upcoming_24h = self.get_upcoming_events(hours=24)
        high_impact = self.get_high_impact_events(hours_ahead=24)
        
        return {
            'total_events_this_week': len(events),
            'upcoming_24h': len(upcoming_24h),
            'high_impact_24h': len(high_impact),
            'should_pause': self.should_pause_trading()[0],
            'next_high_impact': high_impact[0] if high_impact else None
        }

