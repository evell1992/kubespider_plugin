import re
from urllib.parse import urljoin, urlparse
from lxml import etree

from kubespider_plugin import SchedulerProvider, SDK
from kubespider_plugin.values import KubespiderContext, Resource, LinkType, FileType
from kubespider_plugin.utils import get_request_controller


class NexusPHP:
    def __init__(self, context: KubespiderContext, proxy="", use_proxy=False, ):
        self.context = context
        self.proxy = proxy
        self.use_proxy = use_proxy

    @staticmethod
    def match_website(url: str, websites: dict) -> dict:
        parsed_url = urlparse(url)
        host = f"{parsed_url.scheme}://{parsed_url.netloc}"
        for item in websites:
            website_url = item.get("host", "")
            cookie = item.get("cookie", "")
            if host in website_url:
                return {"host": website_url, "cookie": cookie}
        return {}

    def attendance(self, websites: dict) -> None:
        for website in websites:
            url = urljoin(website["host"], "attendance.php")
            get_request_controller(self.proxy, website["cookie"], use_proxy=self.use_proxy).get(url)

    def parse(self, host: str, cookie: str, source: str):
        match = re.findall(r"\?id=(\d*)", source)
        torrent_id = match[0] if match else '0'
        response = get_request_controller(self.proxy, cookie, use_proxy=self.use_proxy).get(source).text
        dom = etree.HTML(response)
        title_element = dom.xpath('//h1/text()')
        title = (title_element[0] if title_element else '').strip()
        url = urljoin(host, f"download.php?id={torrent_id}")
        subtitle_element = dom.xpath('//h1/following-sibling::table[1]//tr[2]/td[2]/text()')
        subtitle = subtitle_element[0] if subtitle_element else ''
        info_element = dom.xpath('//h1/following-sibling::table[1]//tr[3]/td[2]//text()')
        desc = " ".join(el.strip() for el in info_element)
        size = info_element[1].strip()
        return Resource(
            url=url,
            title=title,
            subtitle=subtitle,
            desc=desc,
            size=size,
            link_type=LinkType.torrent,
            file_type=FileType.general,
            plugin=self.context.plugin_name
        ).data

    def search(self, keyword, page=1, websites: dict = None):
        result = []
        for item in websites:
            website_url = item.get("host", "")
            cookie = item.get("cookie", "")
            url = urljoin(website_url, f"torrents.php?search={keyword}&notnewword=1")
            response = get_request_controller(self.proxy, cookie, use_proxy=self.use_proxy).get(url).text
            dom = etree.HTML(response)
            next_page = False
            for a in dom.xpath('//p[@align="center"]//a'):
                text = ''.join(a.xpath('.//text()'))
                if "下一页" in text:
                    next_page = True
                    break
            resources = {
                "page": page,
                "page_size": 100,
                "next_page": next_page,
                "data": []
            }
            for tr in dom.xpath('//table[@class="torrents"]/tr')[1:]:
                tags = tr.xpath('./td[2]//td[1]//img/@alt')
                info = [i.strip() for i in tr.xpath('./td[2]/table/tr/td[1]//text()') if i.strip()]
                size = " ".join(tr.xpath('.//td[5]//text()'))
                link = tr.xpath('./td[2]//td[1]//a/@href')[0]
                url = urljoin(website_url, link)
                resources["data"].append(Resource(
                    url=url,
                    title=info[0],
                    subtitle=info[-1],
                    size=size,
                    tags=tags,
                    link_type=LinkType.torrent,
                    file_type=FileType.general,
                    plugin=self.context.plugin_name
                ).data)
            result.append(resources)
        return result

    def scheduler(self, websites: dict):
        self.attendance(websites)


@SDK()
class NexusPHPProvider(SchedulerProvider):
    @staticmethod
    # pylint: disable=unused-argument
    def should_handle(source: str, context: KubespiderContext, **kwargs):
        websites = kwargs.get("websites", {})
        hosts = []
        for item in websites:
            parsed_host = urlparse(item.get("host", ""))
            hosts.append(f"{parsed_host.scheme}://{parsed_host.netloc}")
        parsed_url = urlparse(source)
        host = f"{parsed_url.scheme}://{parsed_url.netloc}"
        if host in hosts:
            return True
        return False

    @staticmethod
    # pylint: disable=unused-argument
    def get_links(source: str, context: KubespiderContext, **kwargs):
        websites = kwargs.get("websites", {})
        website = NexusPHP.match_website(source, websites)
        host = website.get("host")
        cookie = website.get("cookie")
        proxy = kwargs.get("proxy")
        use_proxy = kwargs.get("use_proxy")
        if not all([host, cookie]):
            raise ValueError(f"Website does not contain configuration for the source: {source}")
        nexus = NexusPHP(context, proxy, use_proxy)
        return nexus.parse(source, host, cookie)

    @staticmethod
    def search(keyword: str, page: int, context: KubespiderContext, **kwargs):
        websites = kwargs.get("websites", {})
        proxy = kwargs.get("proxy")
        use_proxy = kwargs.get("use_proxy")
        if not websites:
            raise ValueError(f"Website does not contain configuration for search: {keyword}")
        nexus = NexusPHP(context, proxy, use_proxy)
        return nexus.search(keyword, page, websites)

    @staticmethod
    def scheduler(context: KubespiderContext, **kwargs):
        websites = kwargs.get("websites", {})
        proxy = kwargs.get("proxy")
        use_proxy = kwargs.get("use_proxy")
        if not websites:
            raise ValueError(f"Website does not contain configuration for scheduler")
        nexus = NexusPHP(context, proxy, use_proxy)
        return nexus.scheduler(websites)
