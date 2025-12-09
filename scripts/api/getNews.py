from zoneinfo import ZoneInfo
from datetime import datetime
import aiohttp, feedparser, asyncio

class Singleton(type):
    def __init__(cls, name, bases, dict):
        super(Singleton, cls).__init__(name, bases, dict)
        cls.instance = None 

    def __call__(cls,*args,**kw):
        if cls.instance is None:
            cls.instance = super(Singleton, cls).__call__(*args, **kw)
        return cls.instance


class NewsParser(object):
    __metaclass__ = Singleton
    def __init__(self):
        self.feeds = [
            "https://smartermsp.com/feed/",
            "https://www.kaseya.com/blog/feed/",
            "https://www.theregister.com/headlines.atom",
            "https://stackoverflow.blog/feed/atom/",
            "https://www.bleepingcomputer.com/feed/",
            "https://us-cert.cisa.gov/ncas/alerts.xml",
            "https://api.msrc.microsoft.com/update-guide/rss",
            "http://feeds.arstechnica.com/arstechnica/index?format=xml"
        ]
        self.refresh_interval = 600 # Max Seconds before refreshing the news feed.
        self._news_items = []
        self._last_refresh = None
        self._current_item_index = 0

    async def _fetch_feed_data(self, session, url):
        """Asynchronously fetches a single feed URL."""
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    print(f"Failed to fetch {url}: Status {response.status}")
        except aiohttp.ClientError as e:
            print(f"Error fetching {url}: {e}")
        return None
    
    async def refresh_news_feed(self):
        """Fetches all feeds concurrently if the interval has passed."""
        
        # Check if we need to refresh based on the interval
        if self._last_refresh and (datetime.now() - self._last_refresh) < timedelta(seconds=self.refresh_interval):
            # print("Refresh interval not yet passed, skipping.")
            return

        print("\nRefreshing news feeds asynchronously...")
        self._last_refresh = datetime.now()
        
        # Use a single aiohttp session for efficiency
        async with aiohttp.ClientSession() as session:
            # Create a list of async tasks to run concurrently
            tasks = [self._fetch_feed_data(session, url) for url in self.feeds]
            # Run them all at the same time and wait for all results
            results = await asyncio.gather(*tasks)

        all_entries = []
        for result in results:
            if result:
                # feedparser is synchronous, but runs quickly on the returned text
                feed = feedparser.parse(result) 
                for entry in feed.entries:
                    all_entries.append({
                        'title': entry.get('title', 'No Title'),
                        'link': entry.get('link', 'No Link'),
                        'published': entry.get('published', 'No Date')
                    })
        
        # Sort all news items by date (you may need to refine date parsing here)
        # all_entries.sort(key=lambda item: item['published'], reverse=True) 
        self._news_items = all_entries
        print(f"News refresh complete. Total items: {len(self._news_items)}")

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
            return "Loading news... Please wait for initial sync."
        
        # Get the current item using the index
        item = self._news_items[self._current_item_index]
        
        author_name = item.get('author', 'No Author')

        # Format the string
        news_string = f"{item['title']} - {author_name}"
            
        return news_string

    def next_news(self):
        """
        Advances the internal index to select the next news item in the list.
        Cycles back to the start if the end is reached.
        """
        if not self._news_items:
            return # Cannot advance if there are no items
            
        # Increment the index
        self._current_item_index += 1
        
        # If we reach the end of the list, loop back to the start (0)
        if self._current_item_index >= len(self._news_items):
            self._current_item_index = 0
        
        # Optional: Print the new item selection for debugging
        # print(f"\nAdvanced news item index to {self._current_item_index}")