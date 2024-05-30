import base64
import re
from urllib.parse import urljoin, urlparse

import requests
from kubespider_plugin import SDK, SearchProvider, Resource, LinkType
from kubespider_plugin.values import KubespiderContext
from lxml import etree


class MagnetDog:
    def __init__(self):
        self.request_handler = requests.Session()
        self.request_handler.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        })
        self.host = self.get_query_host()[0]

    def get_query_host(self):
        resp = self.request_handler.get("http://fb.ciligoufabuye.xyz:1234/")
        match = re.findall(r'var urls = \[([\s\S.]*)\];\s*var strURL', resp.text)
        replaces = re.findall(r"strURL = strURL.replace\(/(.*)/g,'(.*)'\);", resp.text)
        urls = []
        for line in match[0].split(','):
            url = line.replace("'", "").strip()
            for rep in replaces:
                url = url.replace(rep[0], rep[1])
            if url:
                urls.append("https://" + url)
        return urls

    @staticmethod
    def b64_encode(keyword):
        b64_keyword = base64.b64encode(bytes(keyword, 'utf-8')).decode("utf-8")
        content = "VjdwwW29" + b64_keyword + "NjdwwW24"
        return content

    def parse(self, source):
        resp = self.request_handler.get(source)
        dom = etree.HTML(resp.text)
        magnet = dom.xpath("//a[@class='Information_magnet']/@href")
        magent_url = magnet[0] if magnet else None
        info = dom.xpath("//div[@class='Information_l_content']//b/text()")
        if magent_url:
            params = {
                "cllj": magent_url
            }
            url = urljoin(self.host, "/clhq.php")
            resp = base64.b64decode(self.request_handler.get(url, params=params).content).decode('utf-8')
            file_list = [{
                'name': li.xpath(".//div[@class='File_list_info']/text()")[0],
                'size': li.xpath(".//div[@class='File_btn']/text()")[0]
            } for li in etree.HTML(resp).xpath("//li")]
        else:
            file_list = []
        return Resource(url=magent_url, file_list=file_list, link_type=LinkType.magnet, size=info[1],
                        publish_time=info[2]).data

    def search(self, keyword, page=1):
        params = {
            "name": self.b64_encode(keyword),
            "sort": "time",
            "page": page
        }
        url = urljoin(self.host, "/cllj.php")
        resp = self.request_handler.get(url, params=params)
        dom = etree.HTML(resp.text)
        resources = []
        uls = dom.xpath('//ul')
        # torrents
        for li in uls[0].xpath('./li'):
            uid = li.xpath('.//a/@id')[0]
            link = urljoin(self.host, li.xpath('.//a/@href')[0])
            name = ''.join(li.xpath('.//a//text()')).strip()
            other = li.xpath('./div[2]/em/text()')
            size = ""
            create_time = ""
            hot = ""
            for string in other:
                size_match = re.findall(r"文件大小：([\s\S]*)", string)
                if size_match:
                    size = size_match[0].strip()
                create_time_match = re.findall(r"创建时间：([\s\S]*)", string)
                if create_time_match:
                    create_time = create_time_match[0].strip()
                hot_match = re.findall(r"热度：([\s\S]*)", string)
                if hot_match:
                    hot = hot_match[0].strip()
            resources.append(Resource(uid=uid, url=link, name=name, size=size, create_time=create_time, hot=hot))
        # pagination
        pages = [p for p in uls[1].xpath('./li//text()') if p.strip()]
        if page < len(pages) - 2:
            next_page = True
        else:
            next_page = False
        return {
            "page": page,
            "page_size": 50,
            "next_page": next_page,
            "data": [r.data for r in resources]
        }


@SDK()
class MagnetDogProvider(SearchProvider):
    @staticmethod
    # pylint: disable=unused-argument
    def should_handle(source: str, context: KubespiderContext, **kwargs):
        host_list = MagnetDog().get_query_host()
        parsed_url = urlparse(source)
        host = f"{parsed_url.scheme}://{parsed_url.netloc}"
        if host in host_list:
            return True
        return False

    @staticmethod
    # pylint: disable=unused-argument
    def get_links(source: str, context: KubespiderContext, **kwargs):
        return MagnetDog().parse(source)

    @staticmethod
    def search(keyword: str, page: int, context: KubespiderContext, **kwargs):
        return MagnetDog().search(keyword, page)
