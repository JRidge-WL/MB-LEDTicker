from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
import aiohttp, feedparser, asyncio, random

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
        self._teams_items = []
        self._new_teams_items = []
        self.update_pending = False
        self._last_refresh = None
        self._current_item_index = 0
    
    async def refresh_teams_feed(self):
        """Checks for new Teams messages since the last refresh."""
        
        # Check if we need to refresh based on the interval
        if self._last_refresh and (datetime.now() - self._last_refresh) < timedelta(seconds=self.refresh_interval):
            # print("Refresh interval not yet passed, skipping.")
            return

        print("\nRefreshing Teams messages asynchronously...")
        self._last_refresh = datetime.now()

    def get_news_feed(self):
        """Returns the last cached list of news items."""
        return self._news_items
    
    def get_current_news_str(self) -> str:
        """
        Gets the news item currently selected by the index.
        Format: 'HEADLINE - Reporter'
        """
        if not self._news_items:
            # Fallback text if the list is empty
            return "[bg:#FFFF00][fg:#000000]Loading news...[bg:#000000][fg:#FFFFFF] Please wait for initial sync."
        
        # Get the current item using the index
        item = self._news_items[self._current_item_index]
            
        return f"[bg:#FFFF00][fg:#000000]{item['publisher'].upper()}:[fg:#ffffff][bg:#000000] {item['title']}"

    def next_news(self):
        """
        Advances the internal index to select the next news item in the list.
        Cycles back to the start if the end is reached.
        """

        if self.update_pending:
            self._current_item_index = 0
            self._news_items = self._upcoming_news_items
            self.update_pending = False
            self._upcoming_news_items = 0

        if not self._news_items:
            return # Cannot advance if there are no items
            
        # Increment the index
        self._current_item_index += 1
        
        # If we reach the end of the list, loop back to the start (0)
        if self._current_item_index >= len(self._news_items):
            self._current_item_index = 0
        
        # Optional: Print the new item selection for debugging
        # print(f"\nAdvanced news item index to {self._current_item_index}")