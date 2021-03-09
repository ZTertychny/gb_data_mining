from scrapy import Selector
from scrapy.loader import ItemLoader
from itemloaders.processors import TakeFirst, MapCompose
import re
from urllib.parse import urljoin, unquote
from base64 import b64decode


def get_characteristics(item: list) -> dict:
    selector = Selector(text=item)
    return {
        selector.xpath('//div[contains(@class, "AdvertSpecs_label")]/text()')
        .extract_first(): selector.xpath('//div[contains(@class, "AdvertSpecs_data")]//text()')
        .extract_first(),
    }


def get_image(item) -> list:
    selector = Selector(text=item)
    re_pattern_img = re.compile(r"%2Fstatic.am%2Fautomobile_m3%2Fdocument%2F([a-zA-z|\d|\%]+).jpg")
    img_url = "https://static.am/automobile_m3/document/"
    img_list = re.findall(re_pattern_img, selector.xpath("//text()").get())
    return [urljoin(img_url, url.replace("%2F", "/") + ".jpg") for url in img_list]


def get_author(item):
    selector = Selector(text=item)
    re_pattern_dealer_check = re.compile(r"sellerLink%22%2Cnull%2C%22type")
    re_pattern_user = re.compile(r"youlaId%22%2C%22([a-zA-Z|\d]+)%22%2C%22avatar")
    re_pattern_dealer = re.compile(r"sellerLink%22%2C%22([\W|a-zA-Z|\d]+)%22%2C%22type")
    url_youla = "https://auto.youla.ru/"
    if re.findall(re_pattern_dealer_check, selector.xpath("//text()").get()):
        author_id = re.findall(re_pattern_user, selector.xpath("//text()").get())
        return urljoin(f"{url_youla}/user/", author_id[0])
    else:
        author_id = re.findall(re_pattern_dealer, selector.xpath("//text()").get())
        return urljoin(url_youla, author_id[0].replace("%2F", "/"))


def get_phone(item):
    selector = Selector(text=item)
    re_pattern_phone = re.compile(r"phone%22%2C%22([a-zA-Z|\d|%]+)%22%2C%22time")
    phone = unquote(re.findall(re_pattern_phone, selector.xpath("//text()").get())[0])
    return b64decode(b64decode(phone)).decode()


class AutoyoulaLoader(ItemLoader):
    default_item_class = dict
    title_out = TakeFirst()
    price_in = MapCompose(lambda price: float(price.replace("\u2009", "")))
    price_out = TakeFirst()
    description_out = TakeFirst()
    characteristics_in = MapCompose(get_characteristics)
    author_url_in = MapCompose(get_author)
    author_url_out = TakeFirst()
    image_urls_in = MapCompose(get_image)
    phone_in = MapCompose(get_phone)
    phone_out = TakeFirst()


def create_author_url(item):
    selector = Selector(text=item)
    url = selector.xpath("//@href").get()
    return urljoin("https://hh.ru/", url)


def create_text(item):
    return "".join(item)


class HeadHunterLoader(ItemLoader):
    default_item_class = dict
    title_out = TakeFirst()
    hh_employer_url_in = MapCompose(create_author_url)
    hh_employer_url_out = TakeFirst()
    salary_out = create_text
    description_out = create_text

    employer_name_out = TakeFirst()
    employer_website_out = TakeFirst()
    description_employer_out = create_text
    employer_link_hh_out = TakeFirst()


class InstTagLoader(ItemLoader):
    default_item_class = dict
    date_parse_out = TakeFirst()
    data_out = TakeFirst()
    _id_out = TakeFirst()


class InstPostLoader(ItemLoader):
    default_item_class = dict
    date_parse_out = TakeFirst()
    data_out = TakeFirst()
