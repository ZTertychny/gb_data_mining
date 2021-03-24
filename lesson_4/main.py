import os
import dotenv
from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings
from gb_parse.spiders.autoyoula import AutoyoulaSpider
from gb_parse.spiders.headhunter import HeadhunterSpider
from gb_parse.spiders.instagram import InstagramSpider
from gb_parse.spiders.instasocial import InstasocialSpider

if __name__ == "__main__":
    dotenv.load_dotenv("../.env")
    profile_names = ["pivo_varov", "norimyxxxo"]
    crawler_settings = Settings()
    crawler_settings.setmodule("gb_parse.settings")
    crawl_proc = CrawlerProcess(settings=crawler_settings)
    crawl_proc.crawl(
        InstasocialSpider,
        login=os.getenv("INST_LOGIN"),
        password=os.getenv("INST_PASSWORD"),
        profile_names=profile_names,
    )
    crawl_proc.start()
