from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
import requests

class Singleton(type):
    def __init__(cls, name, bases, dict):
        super(Singleton, cls).__init__(name, bases, dict)
        cls.instance = None 

    def __call__(cls,*args,**kw):
        if cls.instance is None:
            cls.instance = super(Singleton, cls).__call__(*args, **kw)
        return cls.instance


class TeamsParser(object):
    __metaclass__ = Singleton
    def __init__(self):
        self.refresh_interval = 600 # Max Seconds before refreshing the news feed.
        self._teams_messages = []
        self._new_teams_messages = []
        self.update_pending = False
        self._last_refresh = None
        self._current_item_index = 0
    
    async def refresh_teams_feed(self):
        """Checks for new Teams messages since the last refresh."""
        
        # Check if we need to refresh based on the interval
        if self._last_refresh and (datetime.now() - self._last_refresh) < timedelta(seconds=self.refresh_interval):
            # print("Refresh interval not yet passed, skipping.")
            return
        self._last_refresh = datetime.now()

    def get_teams_feed(self):
        """Returns the last cached list of teams messages."""
        return self._teams_messages
    
    def get_current_teams_str(self) -> str:
        """
        Gets the teams item currently selected by the index.
        Format: 'SENDER: Message'
        """
        if not self._teams_messages or len(self._teams_messages) == 0:
            # Fallback text if the list is empty
            return "No new messages!"
        
        # Get the current item using the index
        item = self._teams_messages[self._current_item_index]
            
        return f"[bg:#FFFF00][fg:#000000]{item['publisher'].upper()}:[fg:#ffffff][bg:#000000] {item['title']}"

    def next_message(self):
        """
        Advances the internal index to select the next news item in the list.
        Cycles back to the start if the end is reached.
        """

        if self.update_pending:
            self._current_item_index = 0
            self._teams_messages = self._upcoming_teams_messages
            self.update_pending = False
            self._upcoming_teams_messages = 0

        if not self._teams_messages:
            return # Cannot advance if there are no items
            
        # Increment the index
        self._current_item_index += 1
        
        # If we reach the end of the list, loop back to the start (0)
        if self._current_item_index >= len(self._teams_messages):
            self._current_item_index = 0