from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings
from gb_parse.spiders.autoyoula import AutoyoulaSpider

if __name__ == "__main__":
    crawler_settings = Settings()
    crawler_settings.setmodule("gb_parse.settings")
    crawl_proc = CrawlerProcess(settings=crawler_settings)
    crawl_proc.crawl(AutoyoulaSpider)
    crawl_proc.start()
