import pymongo


class MongoHandling:
    def __init__(self, client: str, db: str):
        self.client = pymongo.MongoClient(client)
        self.db = self.client[db]

    def get_mutual_handshake(self, first_collection: str, second_collection: str):
        for itm in self.db[first_collection].aggregate(
            [
                {
                    "$lookup": {
                        "from": f"{second_collection}",
                        "localField": "follow_url",
                        "foreignField": "follow_url",
                        "as": "results",
                    }
                },
                {"$project": {"results.username": 1, "_id": 0}},
                {"$match": {"$expr": {"$ne": ["$results", []]}}},
                {"$unwind": "$results"},
            ]
        ):
            return itm

    def get_record(self, collection: str, field: str, target: str):
        return self.db[collection].find_one({f"{field}": target}, {f"{field}": 1, "_id": 0})

    def get_handshake(self, collection: str):
        return [itm["username"] for itm in self.db[collection].find({}, {"username": 1, "_id": 0})]

    def get_collection_size(self, collection: str) -> int:
        return int(self.db[collection].estimated_document_count())

    def get_chain(self, collection: str, users_chain):
        return self.db[collection].find_one({"chain": f"{users_chain}"}, {"chain": 1, "_id": 0})
