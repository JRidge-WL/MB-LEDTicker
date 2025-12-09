from zoneinfo import ZoneInfo
from datetime import datetime

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
    def __init__():
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

        def refresh_news_feed():

        def get_news_feed():