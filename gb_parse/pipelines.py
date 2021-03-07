# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import pymongo


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
