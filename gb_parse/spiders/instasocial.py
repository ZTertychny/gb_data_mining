import scrapy
import json
from urllib.parse import urlencode
from ..loaders import InstaSocialFollowLoader, InstFinalProjLoader, InstChainLoader
from .paths import InstaSocialSpiderPaths
from ..db.DB_handling import MongoHandling


class InstasocialSpider(scrapy.Spider):
    name = "instasocial"
    allowed_domains = ["www.instagram.com"]
    start_urls = ["http://www.instagram.com/"]
    _login_url = "https://www.instagram.com/accounts/login/ajax/"
    _api_url = "https://www.instagram.com/graphql/query/"
    _target_url = "https://www.instagram.com"

    _query_hash = {
        "follower": "5aefa9893005572d237da5068082d8d5",
        "following": "3dec7e2c57367ef3da3d987d89f9dbc8",
    }

    def __init__(self, login, password, profile_names, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login = login
        self.password = password
        self.profiles_names = profile_names

    def parse(self, response, *args, **kwargs):
        try:
            js_data = self.js_data_extract(response)
            yield scrapy.FormRequest(
                self._login_url,
                method="POST",
                formdata={"username": self.login, "enc_password": self.password},
                headers={"X-CSRFToken": js_data["config"]["csrf_token"]},
            )
        except AttributeError:
            if response.json()["authenticated"]:
                yield from self._get_response_target(self.profiles_names, self.profile_parse)

    def profile_parse(self, response, *args, **kwargs):
        data = self.js_data_extract(response)
        id_profile = data["entry_data"]["ProfilePage"][0]["graphql"]["user"]["id"]
        profile = data["entry_data"]["ProfilePage"][0]["graphql"]["user"]["username"]
        variables = {
            "id": id_profile,
            "include_reel": True,
            "fetch_mutual": True,
            "first": 24,
            "profile": profile,
        }

        yield from self._get_follow(response, "follower", variables, self.follow_parse)

        yield from self._get_follow(response, "following", variables, self.follow_parse)

    def follow_parse(self, response, *args, **kwargs):
        variables = kwargs
        data = response.json().get("data").get("user")
        edge_follow = data.get("edge_followed_by")
        follow = "follower"

        if edge_follow:
            next_page = edge_follow.get("page_info").get("has_next_page")
        else:
            next_page = data.get("edge_follow").get("page_info").get("has_next_page")
            edge_follow = data.get("edge_follow")
            follow = "following"

        yield from self.load_follow(edge_follow["edges"], variables["profile"], follow)

        if next_page:
            variables["after"] = edge_follow.get("page_info").get("end_cursor")
            yield from self._get_follow(response, follow, variables, self.follow_parse)

    def load_follow(self, data, profile, follow_type):
        for node in data:
            loader = InstaSocialFollowLoader()
            loader.add_value("profile", profile)
            for field, value in InstaSocialSpiderPaths.follow_info.items():
                loader.add_value(field, value(node["node"]))
            loader.add_value(follow_type, True)
            yield loader.load_item()

    def _get_response_target(self, target_data, callback, *args, **kwargs):
        for target in target_data:
            yield scrapy.Request(url=f"{self._target_url}/{target}", callback=callback, **kwargs)

    def _get_follow(self, response, follow: str, variables: dict, callback):
        yield response.follow(
            f"{self._api_url}?{self.create_params_link(self._query_hash[follow], variables)}",
            callback=callback,
            cb_kwargs=variables,
        )

    def create_params_link(self, query_hash, variables):
        params = {
            "query_hash": query_hash,
            "variables": json.dumps({k: v for k, v in variables.items() if k != "profile"}),
        }
        return urlencode(params)

    def js_data_extract(self, response):
        script = response.xpath(
            "//script[contains(text(), 'window._sharedData = ')]/text()"
        ).extract_first()
        return json.loads(script.replace("window._sharedData = ", "")[:-1])


class InstFinalProjSpider(InstasocialSpider):
    def __init__(self, login, password, profile_names, *args, **kwargs):
        super().__init__(login, password, profile_names, *args, **kwargs)
        self.counter = 0
        self.breakpoint = 0
        self.tasks = []

    def parse(self, response, *args, **kwargs):
        try:
            js_data = self.js_data_extract(response)
            yield scrapy.FormRequest(
                self._login_url,
                method="POST",
                formdata={"username": self.login, "enc_password": self.password},
                headers={"X-CSRFToken": js_data["config"]["csrf_token"]},
            )
        except AttributeError:
            if response.json()["authenticated"]:
                self.breakpoint = len(self.profiles_names) * 2
                self.tasks = self.profiles_names.copy()
                yield from self.load_chain(self.profiles_names)
                yield from self._get_response_target(self.profiles_names, self.profile_parse)

    def follow_parse(self, response, *args, **kwargs):
        variables = kwargs
        data = response.json().get("data").get("user")
        edge_follow = data.get("edge_followed_by")
        follow = "follower"

        if edge_follow:
            next_page = edge_follow.get("page_info").get("has_next_page")
        else:
            next_page = data.get("edge_follow").get("page_info").get("has_next_page")
            edge_follow = data.get("edge_follow")
            follow = "following"

        yield from self.load_follow(edge_follow["edges"], variables["profile"], follow)

        if next_page:
            variables["after"] = edge_follow.get("page_info").get("end_cursor")
            yield from self._get_follow(response, follow, variables, self.follow_parse)
        else:
            self.check_target_handshake(
                "mongodb://localhost:27017", "Experiment", variables["profile"]
            )
            self.counter += 1
            if self.counter == self.breakpoint:
                yield from self._follow_users_handshake(
                    "mongodb://localhost:27017", "Experiment", self.tasks
                )

    def load_chain(self, children, parents=None):
        for child in children:
            loader = InstChainLoader()
            if parents:
                loader.add_value("chain_array", parents + [child])
            else:
                loader.add_value("chain_array", [child])
            yield loader.load_item()

    def check_target_handshake(self, client: str, db: str, profile_name: str):
        if profile_name == self.profiles_names[0]:
            profile_name = self.profiles_names[1]
        mongo_db = MongoHandling(client, db)
        target_handshake = mongo_db.get_record(
            f"{self.profiles_names[0]}.handshake", "username", profile_name
        )
        if target_handshake:
            result_chain = mongo_db.get_record("chain", "chain_array", profile_name).get(
                "chain_array"
            )
            print(f"Chain - {result_chain}\nLength - {len(result_chain)}")
            return self.crawler.engine.close_spider(self, reason="Goal has been achieved!")

        target_handshake = mongo_db.get_mutual_handshake(
            f"{profile_name}.handshake", f"{self.profiles_names[0]}.handshake"
        )
        if target_handshake:
            parents = mongo_db.get_record("chain", "chain_array", profile_name).get("chain_array")
            result_chain = (
                parents + [target_handshake["results"]["username"]] + [self.profiles_names[0]]
            )
            print(f"Chain - {result_chain}\nLength - {len(result_chain)}")
            return self.crawler.engine.close_spider(self, reason="Goal has been achieved!")

    def _follow_users_handshake(self, client: str, db: str, tasks: list):
        self.tasks = []
        self.counter = 0
        mongo_db = MongoHandling(client, db)
        for user in tasks:
            if user != self.profiles_names[0]:
                handshakes = mongo_db.get_handshake(f"{user}.handshake")
                self.tasks.extend(handshakes)
                parents_chain = mongo_db.get_record("chain", "chain_array", user).get(
                    "chain_array"
                )
                yield from self.load_chain(handshakes, parents=parents_chain)
        self.breakpoint = len(self.tasks) * 2
        yield from self._get_response_target(self.tasks, self.profile_parse)

    def load_follow(self, data, profile, *args, **kwargs):
        for node in data:
            loader = InstFinalProjLoader()
            loader.add_value("profile", profile)
            loader.add_value("_id", InstaSocialSpiderPaths.follow_info["_id"](node["node"]))
            loader.add_value(
                "username", InstaSocialSpiderPaths.follow_info["username"](node["node"])
            )
            loader.add_value(
                "follow_url", InstaSocialSpiderPaths.follow_info["follow_url"](node["node"])
            )
            yield loader.load_item()
