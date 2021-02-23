import datetime as dt
import requests
from urllib.parse import urljoin
import bs4
import time
import locale
import datetime
import pymongo


class MagnitParse:
    def __init__(self, start_url, db_client=None):
        self.start_url = start_url
        self.db = db_client["gb_data_mining_16_02_2021"]

    def _get_response(self, url):
        while True:
            response = requests.get(url)
            if response.status_code == 200:
                return response
            time.sleep(0.5)

    def _get_soup(self, url):
        response = self._get_response(url)
        soup = bs4.BeautifulSoup(response.text, "lxml")
        return soup

    def _template(self):
        attr_promo = {"class": "card-sale__header"}
        attr_prod = {"class": "card-sale__title"}
        return {
            "url": lambda a: urljoin(self.start_url, a.attrs.get("href")),
            "promo_name": lambda a: a.find("div", attrs=attr_promo).text,
            "product_name": lambda a: a.find("div", attrs=attr_prod).text,
        }

    def run(self):
        soup = self._get_soup(self.start_url)
        catalog = soup.find("div", attrs={"class": "сatalogue__main"})
        for product_a in catalog.find_all("a", recursive=False):
            product_data = self._parse(product_a)
            self.save(product_data)

    def _parse(self, product_a: bs4.Tag) -> dict:
        product_data = {}
        for key, funk in self._template().items():
            try:
                product_data[key] = funk(product_a)
            except AttributeError:
                pass

        return product_data

    def save(self, data: dict):
        collection = self.db["magnit"]
        collection.insert_one(data)


class MagnitParserEnhanced(MagnitParse):
    def _create_date(self, product_a: bs4.Tag, from_d=True) -> datetime:
        """Returns date in form of datetime,
        Receive pruduct_a as bs4.Tag,
        from_d as boolean(True or False). If True then returns from_date,
        else to_date.
        Handle the exception if product has only one date.
        """
        dates = product_a.find("div", attrs={"class": "card-sale__date"})
        if from_d:
            indx_date = 1
        else:
            indx_date = 3
        try:
            date = dt.datetime.strptime(
                f"{dates.contents[indx_date].text.split()[1]} "
                f"{dates.contents[indx_date].text.split()[2][:3]} 2021",
                "%d %b %Y",
            )
        except IndexError:
            return None

        return date

    def _create_price(self, product_a: bs4.Tag, label=None):
        """Returns price in for of the float value
        or None if there is'n any accordance to label or
        if value can't be transformed.

        Receive product_a as bs4.Tag,
        label in form of str 'new' or 'old' for searching price.
        """
        price = product_a.find("div", attrs={"class": f"label__price_{label}"})
        attr_int = {"class": "label__price-integer"}
        attr_decim = {"class": "label__price-decimal"}
        if price:
            try:
                integer = price.find("span", attrs=attr_int).text
                decim = price.find("span", attrs=attr_decim).text
                price = float(f"{integer}.{decim}")
            except AttributeError:
                return None
        return price

    def _template(self):
        """Enhanced template from the class MagnitParse.
        Returns dict of templates."""
        template_dict = MagnitParse._template(self)
        template_dict["image_url"] = lambda a: urljoin(
            self.start_url, a.find("img", attrs={"lazy"}).attrs.get("data-src")
        )
        return template_dict

    def _parse(self, product_a: bs4.Tag) -> dict:
        """Returns dict with the characteristics of some product.
        Receive product_a as bs4.Tag for transforming it into a dictionary.
        """
        product_data = {}
        try:
            for key, funk in self._template().items():
                product_data[key] = funk(product_a)
            product_data.update(
                {
                    "old_price": self._create_price(product_a, label="old"),
                    "new_price": self._create_price(product_a, label="new"),
                    "date_from": self._create_date(product_a),
                }
            )
            if not self._create_date(product_a, from_d=False):
                product_data["date_to"] = product_data["date_from"]
            else:
                res_date = self._create_date(product_a, from_d=False)
                product_data["date_to"] = res_date
        except AttributeError:
            pass

        return product_data


if __name__ == "__main__":
    locale.setlocale(locale.LC_ALL, "")
    url = "https://magnit.ru/promo/"
    db_client = pymongo.MongoClient("mongodb://localhost:27017")
    parser = MagnitParserEnhanced(url, db_client)
    parser.run()
