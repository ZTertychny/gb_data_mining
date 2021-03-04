import scrapy
import re
from urllib.parse import urljoin, unquote
import pymongo
from base64 import b64decode


class AutoyoulaSpider(scrapy.Spider):
    name = "autoyoula"
    allowed_domains = ["auto.youla.ru"]
    start_urls = ["https://auto.youla.ru/"]
    _css_selectors = {
        "brands": "div.TransportMainFilters_brandsList__2tIkv "
        ".ColumnItemList_item__32nYI a.blackLink",
        "pagination": "div.Paginator_block__2XAPy a.Paginator_button__u1e7D",
        "car": "article.SerpSnippet_snippet__3O1t2 .SerpSnippet_titleWrapper__38bZM a.blackLink",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_clinet = pymongo.MongoClient("mongodb://localhost:27017")
        self.db = self.db_clinet["gb_data_mining_youla"]
        self.collection = self.db["youla_adverts"]

    def _get_follow(self, response, select_str, callback, **kwargs):
        for a in response.css(select_str):
            link = a.attrib.get("href")
            yield response.follow(link, callback=callback, cb_kwargs=kwargs)

    def parse(self, response, *args, **kwargs):
        yield from self._get_follow(response, self._css_selectors["brands"], self.brand_parse)

    def brand_parse(self, response, *args, **kwargs):
        yield from self._get_follow(response, self._css_selectors["pagination"], self.brand_parse)

        yield from self._get_follow(response, self._css_selectors["car"], self.car_parse)

    def car_parse(self, response):
        character = response.css(
            "div.AdvertCard_specs__2FEHc .AdvertSpecs_row__ljPcX *::text"
        ).getall()
        advert_dict = {
            "title": response.css(".AdvertCard_advertTitle__1S1Ak::text").get(),
            "price": int(
                response.css("div.AdvertCard_price__3dDCr::text").get().replace("\u2009", "")
            ),
            "characteristics": {
                character[i]: character[i + 1] for i in range(0, len(character), 2)
            },
            "description": response.css(
                "div.AdvertCard_descriptionWrap__17EU3 .AdvertCard_descriptionInner__KnuRi::text"
            ).get(),
        }
        advert_dict.update(self._get_script_search(response))
        self._save(advert_dict)

    def _get_script_search(self, response):
        marker = "window.transitState = decodeURIComponent"
        for script in response.css("script"):
            try:
                if marker in script.css("::text").extract_first():
                    advert_dict_update = {
                        "author_url": self._get_author_url(response, script),
                        "image_urls": self._get_image(script),
                        "phone": self._get_phone(script),
                    }
                    return advert_dict_update
            except TypeError:
                pass

    def _get_author_url(self, response, script):
        re_pattern_dealer_check = re.compile(r"sellerLink%22%2Cnull%2C%22type")
        re_pattern_user = re.compile(r"youlaId%22%2C%22([a-zA-Z|\d]+)%22%2C%22avatar")
        re_pattern_dealer = re.compile(r"sellerLink%22%2C%22([\W|a-zA-Z|\d]+)%22%2C%22type")
        url_youla = "https://auto.youla.ru/"
        if re.findall(re_pattern_dealer_check, script.css("::text").extract_first()):
            author_id = re.findall(re_pattern_user, script.css("::text").extract_first())
            return response.urljoin(f"/user/{author_id[0]}")
        else:
            author_id = re.findall(re_pattern_dealer, script.css("::text").extract_first())
            return urljoin(url_youla, author_id[0].replace("%2F", "/"))

    def _get_image(self, script) -> list:
        re_pattern_img = re.compile(
            r"%2Fstatic.am%2Fautomobile_m3%2Fdocument%2F([a-zA-z|\d|\%]+).jpg"
        )
        img_url = "https://static.am/automobile_m3/document/"
        img_list = re.findall(re_pattern_img, script.css("::text").extract_first())
        return [urljoin(img_url, url.replace("%2F", "/") + ".jpg") for url in img_list]

    def _get_phone(self, script):
        re_pattern_phone = re.compile(r"phone%22%2C%22([a-zA-Z|\d|%]+)%22%2C%22time")
        phone = unquote(re.findall(re_pattern_phone, script.css("::text").extract_first())[0])
        return b64decode(b64decode(phone)).decode()

    def _save(self, data: dict):
        self.collection.insert_one(data)
