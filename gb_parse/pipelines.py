# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import pymongo
from scrapy import Request
from scrapy.pipelines.images import ImagesPipeline


class GbParsePipeline:
    def process_item(self, item, spider):
        return item


class GbParseMongoPipeline:
    def __init__(self):
        client = pymongo.MongoClient("mongodb://localhost:27017")
        self.db = client["gb_data_mining_16_02_2021"]

    def process_item(self, item, spider):
        self.db[spider.name].insert_one(item)
        return item


class GbParseHHMongoPipline:
    def __init__(self):
        client = pymongo.MongoClient("mongodb://localhost:27017")
        self.db = client["headhunter"]

    def process_item(self, item, spider):
        if item.get("employer_name"):
            self.db["employer_info"].insert_one(item)
        else:
            self.db["vacancy"].insert_one(item)
        return item


class GbParseInstMongoPipline:
    def __init__(self):
        client = pymongo.MongoClient("mongodb://localhost:27017")
        self.db = client["Instagram"]
        self.collection = self.db["tags"]

    def process_item(self, item, spider):
        if item.get("data").get("name"):
            if len(list(self.collection.find({"_id": item["_id"]}))) == 0:
                self.db["tags"].insert_one(item)
            return item
        self.db["posts"].insert_one(item)
        return item


class GbImageDownloadPipeline(ImagesPipeline):
    def get_media_requests(self, item, info):
        img_url = item.get("data").get("photo")
        if img_url:
            yield Request(img_url)

    def item_completed(self, results, item, info):
        if results:
            item["data"]["photos"] = results[0][1]
        return item
