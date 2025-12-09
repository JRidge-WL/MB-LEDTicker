from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
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
                    return await response.text(), url
                else:
                    print(f"Failed to fetch {url}: Status {response.status}")
        except aiohttp.ClientError as e:
            print(f"Error fetching {url}: {e}")
        return None, url
    
    async def refresh_news_feed(self):
        """Fetches all feeds concurrently if the interval has passed."""
        
        # Check if we need to refresh based on the interval
        if self._last_refresh and (datetime.now() - self._last_refresh) < timedelta(seconds=self.refresh_interval):
            # print("Refresh interval not yet passed, skipping.")
            return

        print("\nRefreshing news feeds asynchronously...")
        self._last_refresh = datetime.now()
        
        # Calculate the threshold time (6 hours ago) in UTC
        six_hours_ago = datetime.now(ZoneInfo("UTC")) - timedelta(hours=6)

        # Use a single aiohttp session for efficiency
        async with aiohttp.ClientSession() as session:
            # Create a list of async tasks to run concurrently
            tasks = [self._fetch_feed_data(session, url) for url in self.feeds]
            # Run them all at the same time and wait for all results
            results_with_urls = await asyncio.gather(*tasks)

        all_entries = []
        for result_tuple in results_with_urls:
            if result_tuple is None:
                continue

            result_text, url = result_tuple

            if result_text:
                feed = feedparser.parse(result_text)
                default_publisher = feed.feed.get('title', url) 

                for entry in feed.entries:
                    # --- START: Filtering Logic ---
                    # Use the 'published_parsed' attribute which is a time tuple (struct_time)
                    pub_date_parsed = entry.get('published_parsed')
                    
                    if pub_date_parsed:
                        # Convert the time tuple to a timezone-aware datetime object in UTC
                        pub_date_datetime = datetime(*pub_date_parsed[:6], tzinfo=ZoneInfo("UTC"))

                        # Only proceed if the article was published after the threshold
                        if pub_date_datetime >= six_hours_ago:
                            # --- END: Filtering Logic ---

                            publisher_name = entry.get('author') or (getattr(entry, 'source', None) and entry.source.get('title')) or default_publisher
                            
                            all_entries.append({
                                'title': entry.get('title', 'No Title'),
                                'link': entry.get('link', 'No Link'),
                                'published': entry.get('published', 'No Date'),
                                'publisher': publisher_name 
                            })
        
        # Sort all news items by date (optional, but good practice for recent news)
        # We can sort using our new 'published_datetime' key if we store it, 
        # but sorting by the 'published' string works fine for reverse chronological order in most cases.
        # all_entries.sort(key=lambda item: item['published'], reverse=True) 

        self._news_items = all_entries
        print(f"News refresh complete. Total items found in last 6 hours: {len(self._news_items)}")


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

        # Format the string
        news_string = f"{item['title']} - {item['publisher']}"
            
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