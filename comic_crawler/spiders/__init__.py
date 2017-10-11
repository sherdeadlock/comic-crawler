# This package will contain the spiders of your Scrapy project
#
# Please refer to the documentation for information on how to create and manage
# your spiders.

import re, os
from urllib.parse import urlparse

import scrapy
from scrapy import Request, Selector
from scrapy.http import Response


class CartoonmadSpider(scrapy.Spider):
    name = "cartoonmad"
    allowed_domains = ["cartoonmad.com"]

    def __init__(self, **kwargs):
        super().__init__(CartoonmadSpider.name, **kwargs)
        if hasattr(self, "start_index"):
            self.start_index = int(self.start_index)
        else:
            self.start_index = 0

        if not hasattr(self, "repository"):
            self.repository = "/tmp"

    def start_requests(self):
        yield Request(self.start_url, callback=self.parse)

    def is_table(self, table: Selector):
        for td in table.xpath(".//td"):
            text = td.extract()
            if text and re.search("第\s*\d+\s*[卷|話]", text):
                return True
        return False

    def parse(self, response: Response):
        # scrapy.shell.inspect_response(response, self)
        directory = urlparse(response.url).path.split("/")[-1].split(".")[0]
        requests = []
        for table in response.xpath("//table[not(.//table)]"):
            if not self.is_table(table):
                continue

            links = table.xpath(".//td/a/@href").extract()
            for link in links:
                url = response.urljoin(link)
                requests.append(Request(url, self.parse_chapter, meta={"directory": directory}))

        self._requests = iter(requests)

        for i in range(self.start_index):
            next(self._requests)

        yield next(self._requests, None)

    def parse_chapter(self, response: Response):
        # scrapy.shell.inspect_response(response, self)
        filename = urlparse(response.url).path.split("/")[-1].split(".")[0]
        el: Selector = next(iter(response.xpath("//a[img[@oncontextmenu='return false']]")), None)
        if el is None:
            yield next(self._requests, None)
            return

        imgurl = el.xpath("img/@src").extract_first()
        imgname = urlparse(imgurl).path.split("/")[-1]
        filename = filename + " " + imgname

        meta = response.meta.copy()
        meta["filename"] = filename

        yield Request(imgurl, callback=self.download_image, meta=meta)

        nexturl = response.urljoin(el.xpath("@href").extract_first())
        yield Request(nexturl, callback=self.parse_chapter, meta=meta, dont_filter=True)
        print("{} {} {}".format(filename, imgurl, nexturl))

    def download_image(self, response: Response):
        filename = self.repository + "/" + response.meta["directory"] + "/" + response.meta["filename"]
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        file = open(filename, "wb")
        file.write(response.body)
        file.close()
