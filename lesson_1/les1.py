from pathlib import Path
import json
import requests
import time


class Parse5ka:
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 "
        "(Macintosh; Intel Mac OS X 10.16; rv:85.0)"
        "Gecko/20100101 Firefox/85.0",
    }

    def __init__(self, start_url: str, dependent_url: str, file_path):
        self.start_url = start_url
        self.dependent_url = dependent_url
        self.path = file_path

    def _get_response(self, url, params=None):
        """Returns response from a server by doing get-request.
        url - url of given site.
        headers - obtain dict of data(headers) for specifying get-request,
        params - obtain the dict of params for specifying get-request"""
        while True:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                return response
            time.sleep(0.5)

    def _parse(self, url, params=None):
        """Returns products from the get-request,
        if there are no products returns the empty list,
        url - url of the given site,
        params - obtain the dict of params for specifying get-request"""
        while url:
            response = self._get_response(url, params)
            data = response.json()
            url = data["next"]
            if data["results"]:
                for product in data["results"]:
                    yield product
            else:
                return []

    def run(self):
        """Main method of the class.
        Outputs the final data in the form of dict and save it on a machine"""
        categories = self._get_response(self.start_url)
        categories = categories.json()
        for group_code in categories:
            params = {"categories": group_code["parent_group_code"]}
            products_discounted = []
            for product in self._parse(self.dependent_url, params=params):
                products_discounted.append(product)
            result_data = dict(
                name=group_code["parent_group_name"],
                code=group_code["parent_group_code"],
                products=products_discounted,
            )
            product_path = self.path.joinpath(f"{result_data['code']}.json")
            self._save(result_data, product_path)

    @staticmethod
    def _save(data: dict, file_path):
        """Method for saving data in json format
        data - receive some data for saving,
        file_path - receive path where data should be saved"""
        jdata = json.dumps(data, ensure_ascii=False)
        file_path.write_text(jdata, encoding="UTF-8")


if __name__ == "__main__":
    url = "https://5ka.ru/api/v2/categories/"
    url_2 = "https://5ka.ru/api/v2/special_offers/"
    save_path = Path(__file__).parent.joinpath("products")
    if not save_path.exists():
        save_path.mkdir()

    parser = Parse5ka(url, url_2, save_path)
    parser.run()
