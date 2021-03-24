# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import pymongo
import pymongo.errors
import bson
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


class GbImageDownloadPipeline(ImagesPipeline):
    def get_media_requests(self, item, info):
        img_url = item.get("data").get("photo")
        if img_url:
            yield Request(img_url)

    def item_completed(self, results, item, info):
        if results:
            item["data"]["photos"] = results[0][1]
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


class GbParseInstaSocialImageDownloadPipeline(ImagesPipeline):
    def get_media_requests(self, item, info):
        img_url = item.get("profile_pic_url")
        if img_url:
            yield Request(img_url)

    def item_completed(self, results, item, info):
        if results:
            item["photos"] = [itm[1] for itm in results]
        return item


class GbParseInstaSocialMongoPipline:
    def __init__(self):
        client = pymongo.MongoClient("mongodb://localhost:27017")
        self.db = client["InstaSocial"]

    def process_item(self, item, spider):
        coll_name = item.pop("profile")
        try:
            self.insert_item(coll_name, item)
        except bson.errors.InvalidDocument:
            item["photos"] = None
            self.insert_item(coll_name, item)

        return item

    def insert_item(self, coll_name, item):
        if item.get("follower"):
            self.db[f"{coll_name}.followers"].insert_one(item)
        else:
            self.db[f"{coll_name}.following"].insert_one(item)


class GbParseInstaFinalProjMongoPipline:
    def __init__(self):
        client = pymongo.MongoClient("mongodb://localhost:27017")
        self.db = client["InstaSocial"]

    def process_item(self, item, spider):
        if not item.get("chain_array"):
            collection_name = item.pop("profile")
            try:
                self.db[f"{collection_name}.full"].insert_one(item)
            except pymongo.errors.DuplicateKeyError:
                self.db[f"{collection_name}.handshake"].insert_one(item)

        return item


class GbParseInstChainMongoPipline:
    def __init__(self):
        client = pymongo.MongoClient("mongodb://localhost:27017")
        self.db = client["InstaSocial"]
        self.collection = self.db["chain"]

    def process_item(self, item, spider):
        if item.get("chain_array"):
            self.collection.insert_one(item)

        return item
