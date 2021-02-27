import requests
from urllib.parse import urljoin
import bs4
import time
import typing
import datetime as dt
from lesson_3.database.db import Database


class GbBlogParse:
    def __init__(self, start_url, comments_url, database):
        self.db = database
        self.start_url = start_url
        self.done_urls = set()
        self.tasks = []
        self.comments_url = comments_url

    def _get_response(self, url, params=None):
        while True:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response
            time.sleep(0.5)

    def _get_soup(self, url):
        response = self._get_response(url)
        soup = bs4.BeautifulSoup(response.text, "lxml")
        return soup

    def __create_task(self, url, callback, tag_list):
        for link in set(
            urljoin(url, href.attrs.get("href")) for href in tag_list if href.attrs.get("href")
        ):
            if link not in self.done_urls:
                task = self._get_task(link, callback)
                self.done_urls.add(link)
                self.tasks.append(task)

    def _parse_feed(self, url, soup):
        ul = soup.find("ul", attrs={"class": "gb__pagination"})
        self.__create_task(url, self._parse_feed, ul.find_all("a"))
        self.__create_task(
            url, self._parse_post, soup.find_all("a", attrs={"class": "post-item__title"})
        )

    def _get_comment(self, arr) -> list:
        dic_data = dict(name=None, url=None, text=None)
        result = []
        children = []
        for i in arr:
            dic_data = dict(
                name=i["comment"]["user"]["full_name"],
                url=i["comment"]["user"]["url"],
                text=i["comment"]["body"],
            )
            result.append(dic_data)
            if i["comment"]["children"]:
                children.extend(i["comment"]["children"])
        if children:
            result.extend(self._get_comment(children))
        return result

    def _parse_post(self, url, soup):
        author_name_tag = soup.find("div", attrs={"itemprop": "author"})
        date = "".join(soup.find("time").attrs.get("datetime").split(":"))
        comments_block = soup.find("comments")
        params = {
            "commentable_type": "Post",
            "commentable_id": comments_block.attrs.get("commentable-id"),
            "order": "desc",
        }
        resp = self._get_response(self.comments_url, params=params)

        data = {
            "post_data": {
                "url": url,
                "title": soup.find("h1", attrs={"class": "blogpost-title"}).text,
                "image_url": soup.find("img").attrs.get("src"),
                "date": dt.datetime.strptime(date, "%Y-%m-%dT%H%M%S%z"),
            },
            "writer": {
                "name": author_name_tag.text,
                "url": urljoin(url, author_name_tag.parent.attrs.get("href")),
            },
            "comments": self._get_comment(resp.json()),
            "tags": [
                {"name": a_tag.text, "url": urljoin(url, a_tag.attrs.get("href"))}
                for a_tag in soup.find_all("a", attrs={"class": "small"})
            ],
        }
        return data

    def _get_task(self, url, callback: typing.Callable) -> typing.Callable:
        def task():
            soup = self._get_soup(url)
            return callback(url, soup)

        return task

    def run(self):
        self.tasks.append(self._get_task(self.start_url, self._parse_feed))
        self.done_urls.add(self.start_url)
        for task in self.tasks:
            result = task()
            if isinstance(result, dict):
                self.db.create_post(result)


if __name__ == "__main__":
    db = Database("sqlite:///gb_blog.db")
    url = "https://geekbrains.ru/posts"
    url_comments = urljoin("https://geekbrains.ru", "/api/v2/comments")
    parser = GbBlogParse(url, url_comments, db)
    parser.run()
