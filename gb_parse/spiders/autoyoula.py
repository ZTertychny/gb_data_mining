import scrapy
from ..loaders import AutoyoulaLoader


class AutoyoulaSpider(scrapy.Spider):
    name = "autoyoula"
    allowed_domains = ["auto.youla.ru"]
    start_urls = ["https://auto.youla.ru/"]

    _xpath_selectors = {
        "brands": "//div[contains(@class, 'TransportMainFilters')]//a[@data-target='brand']",
        "pagination": "//div[contains(@class, 'Paginator_block')]//a[@data-target, 'button-link']",
        "car": "//article[@data-target='serp-snippet']//div[contains(@class, 'SerpSnippet_titleWrapper')]"
        "//a[contains(@class, 'blackLink')]",
        "car_script": "//script[contains(text(), 'window.transitState = decodeURIComponent')]/text()",
    }

    _car_xpaths = {
        "title": '//div[@data-target="advert"]//div[@data-target="advert-title"]/text()',
        "price": '//div[contains(@class, "AdvertCard_priceBlock")]//div[@data-target="advert-price"]/text()',
        "characteristics": '//div[contains(@class, "AdvertCard_specs")]/div/div',
        "description": '//div[contains(@class, "AdvertCard_description")]'
        '//div[@data-target="advert-info-descriptionFull"]/text()',
        "author_url": _xpath_selectors["car_script"],
        "image_urls": _xpath_selectors["car_script"],
        "phone": _xpath_selectors["car_script"],
    }

    def _get_follow_xpath(self, response, select_str, callback, **kwargs):
        try:
            for a in response.xpath(select_str):
                link = a.attrib.get("href")
                yield response.follow(link, callback=callback, cb_kwargs=kwargs)
        except ValueError:
            pass

    def parse(self, response, *args, **kwargs):
        yield from self._get_follow_xpath(
            response, self._xpath_selectors["brands"], self.brand_parse
        )

    def brand_parse(self, response, *args, **kwargs):
        yield from self._get_follow_xpath(
            response, self._xpath_selectors["pagination"], self.brand_parse
        )

        yield from self._get_follow_xpath(response, self._xpath_selectors["car"], self.car_parse)

    def car_parse(self, response):
        loader = AutoyoulaLoader(response=response)
        try:
            for key, selector in self._car_xpaths.items():
                loader.add_xpath(key, selector)
        except AttributeError:
            pass
        else:
            yield loader.load_item()
