import scrapy
import json
from urllib.parse import urlencode
from ..loaders import InstaSocialFollowLoader
from .paths import InstaSocialSpiderPaths


class InstasocialSpider(scrapy.Spider):
    name = "instasocial"
    allowed_domains = ["www.instagram.com"]
    start_urls = ["http://www.instagram.com/"]
    _login_url = "https://www.instagram.com/accounts/login/ajax/"
    _api_url = "https://www.instagram.com/graphql/query/"

    _query_hash = {
        "followers": "5aefa9893005572d237da5068082d8d5",
        "following": "3dec7e2c57367ef3da3d987d89f9dbc8",
    }

    def __init__(self, login, password, profile_names, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login = login
        self.password = password
        self.profiles_names = profile_names
        self._current_profile = ""

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
                for profile in self.profiles_names:
                    self._current_profile = profile
                    yield response.follow(f"/{profile}", callback=self.profile_parse)

    def profile_parse(self, response, *args, **kwargs):
        data = self.js_data_extract(response)
        id_profile = data["entry_data"]["ProfilePage"][0]["graphql"]["user"]["id"]
        profile = data["entry_data"]["ProfilePage"][0]["graphql"]["user"]["username"]
        variables = {"id": id_profile, "first": 100, "profile": profile}
        yield response.follow(
            f"{self._api_url}?{self.create_params_link(self._query_hash['followers'], variables)}",
            callback=self.follow_parse,
            cb_kwargs=variables,
        )

        yield response.follow(
            f"{self._api_url}?{self.create_params_link(self._query_hash['following'], variables)}",
            callback=self.follow_parse,
            cb_kwargs=variables,
        )

    def follow_parse(self, response, *args, **kwargs):
        variables = kwargs
        data = response.json().get("data").get("user")
        edge_follow = data.get("edge_followed_by")
        is_follower = True

        if edge_follow:
            next_page = edge_follow.get("page_info").get("has_next_page")
        else:
            next_page = data.get("edge_follow").get("page_info").get("has_next_page")
            edge_follow = data.get("edge_follow")
            is_follower = False

        yield from self.load_follow(
            edge_follow["edges"], variables["profile"], is_follower=is_follower
        )

        if next_page:
            variables["after"] = edge_follow.get("page_info").get("end_cursor")
            if is_follower:
                yield response.follow(
                    f"{self._api_url}?{self.create_params_link(self._query_hash['followers'], variables)}",
                    callback=self.follow_parse,
                    cb_kwargs=variables,
                )
            else:
                yield response.follow(
                    f"{self._api_url}?{self.create_params_link(self._query_hash['following'], variables)}",
                    callback=self.follow_parse,
                    cb_kwargs=variables,
                )

    def load_follow(self, data, profile, is_follower=None):
        for node in data:
            loader = InstaSocialFollowLoader()
            loader.add_value("profile", profile)
            for field, value in InstaSocialSpiderPaths.follow_info.items():
                loader.add_value(field, value(node["node"]))
            loader.add_value("is_follower", is_follower)
            yield loader.load_item()

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
