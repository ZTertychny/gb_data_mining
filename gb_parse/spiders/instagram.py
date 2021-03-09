import scrapy
import json
from ..loaders import InstTagLoader, InstPostLoader
from .paths import InstagramSpiderPaths
from datetime import datetime


class InstagramSpider(scrapy.Spider):
    name = "instagram"
    allowed_domains = ["www.instagram.com"]
    start_urls = ["http://www.instagram.com/"]
    _login_url = "https://www.instagram.com/accounts/login/ajax/"
    _tags_url = "/explore/tags/"

    _query_hash = "9b498c08113f1e09617a1703c22b2f32"
    _posts_url = "https://www.instagram.com/graphql/query/"
    _owner_post_url = "https://www.instagram.com/p/"
    _current_tag = ""

    def __init__(self, login, password, tags, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login = login
        self.password = password
        self.tags = tags

    def parse(self, response, *args, **kwargs):
        try:
            js_data = self.js_data_extract(response)
            yield scrapy.FormRequest(
                self._login_url,
                method="POST",
                callback=self.parse,
                formdata={"username": self.login, "enc_password": self.password},
                headers={"X-CSRFToken": js_data["config"]["csrf_token"]},
            )
        except AttributeError as e:
            print(e)
            if response.json()["authenticated"]:
                for tag in self.tags:
                    self._current_tag = tag
                    yield response.follow(f"{self._tags_url}{tag}/", callback=self.tag_page_parse)

    def tag_page_parse(self, response):
        try:
            data = self._get_hashtag_struct(response)
        except AttributeError:
            data = response.json().get("data").get("hashtag")

        next = data.get("edge_hashtag_to_media").get("page_info").get("has_next_page")
        yield self.tag_parse(data)
        yield from self.post_tag_parse(data)

        if next:
            variables = {
                "tag_name": self._current_tag,
                "first": 66,
                "after": data["edge_hashtag_to_media"]["page_info"]["end_cursor"],
            }
            yield response.follow(
                f"{self._posts_url}?query_hash={self._query_hash}&variables={json.dumps(variables)}",
                callback=self.tag_page_parse,
            )

    def tag_parse(self, data):
        loader = InstTagLoader()
        loader.add_value("date_parse", datetime.now())
        loader.add_value("_id", InstagramSpiderPaths.tag_paths["_id"](data))
        loader.add_value("data", {"name": InstagramSpiderPaths.tag_paths["name"](data)})
        return loader.load_item()

    def post_tag_parse(self, data):
        posts = data["edge_hashtag_to_media"]["edges"]
        for edge in posts:
            loader = InstPostLoader()
            loader.add_value("date_parse", datetime.now())
            val = {k: v(edge["node"]) for k, v in InstagramSpiderPaths.post_paths.items()}
            loader.add_value("data", val)
            yield loader.load_item()

    def _get_hashtag_struct(self, response) -> dict:
        data = self.js_data_extract(response)
        data = data["entry_data"]["TagPage"][0]["graphql"]["hashtag"]
        return data

    def js_data_extract(self, response):
        script = response.xpath(
            "//script[contains(text(), 'window._sharedData = ')]/text()"
        ).extract_first()
        return json.loads(script.replace("window._sharedData = ", "")[:-1])
