import json
import logging
import re
import time
from urllib.parse import urljoin, urlparse
from kubespider_source_provider_sdk import SDK, SchedulerProvider, Resource, LinkType, FileType
from kubespider_source_provider_sdk.utils import get_request_controller


class MTeam:
    def __init__(self, host: str, cookie: str, proxy="", use_proxy=False):
        self.host = host
        self.request_handler = get_request_controller(cookie=cookie, use_proxy=use_proxy)

    def get_torrent_dl_token(self, torrent_id):
        """获取种子token"""
        time.sleep(1)
        resp = self.request_handler.post(urljoin(self.host, "/api/torrent/genDlToken"), data={'id': torrent_id})
        status_code, content = resp.status_code, resp.json()
        data = content.get("data", "")
        token = re.findall(r'credential=(.*)', data)
        return token[0] if token else None

    def get_torrent_link(self, token):
        """获取种子地址"""
        time.sleep(1)
        resp = self.request_handler.get(urljoin(self.host, f"/api/rss/dl?useHttps=true&type=&credential={token}"),
                                        allow_redirects=False)
        resp_headers = resp.headers
        location = resp_headers.get("location")
        return location

    def parse(self, source):
        match = re.findall(r'/detail/(\d*)', source)
        torrent_id = match[0] if match else None
        resp = self.request_handler.post(urljoin(self.host, "https://kp.m-team.cc/api/torrent/detail"),
                                         data={'id': torrent_id})
        status_code, content = resp.status_code, resp.json()
        data = content.get("data", {})
        if status_code != 200 or not data:
            logging.warning("链接:%s 解析失败: %s %s", source, status_code, content)
        else:
            torrent_id = data.get("id")
            dl_token = self.get_torrent_dl_token(torrent_id)
            torrent_url = self.get_torrent_link(dl_token)
            if torrent_url:
                return [Resource(url=torrent_url, link_type=LinkType.torrent, file_type=FileType.general, **data).data]
        return []

    def search(self, keyword, page=1, **kwargs):
        mode = kwargs.get("mode")
        if not mode or mode not in ["normal", "movie", "tvshow", "adult"]:
            mode = "normal"
        post_data = {
            "keyword": keyword,
            "mode": mode,  # normal movie tvshow adult
            "categories": [],
            "visible": 1,
            "pageNumber": page,
            "pageSize": 100
        }
        resp = self.request_handler.post(urljoin(self.host, "/api/torrent/search"), json=post_data)
        status_code, content = resp.status_code, resp.json()
        data = content.get("data", {}).get("data", [])
        total_page = content.get("data", {}).get("totalPages", 1)
        next_page = True if int(total_page) > page else False
        if status_code != 200 or not data:
            logging.warning("keyword:%s 搜索失败: %s %s", keyword, status_code, content)
            return
        return {
            "page": page,
            "page_size": 100,
            "next_page": next_page,
            "data": [Resource(**item).data for item in data]
        }

    def scheduler(self):
        pass


@SDK()
class MTeamProvider(SchedulerProvider):
    @staticmethod
    # pylint: disable=unused-argument
    def should_handle(source: str, **kwargs):
        host_list = [
            "https://kp.m-team.cc",
            "https://ap.m-team.cc",
            "https://xp.m-team.cc",
            "https://xp1.m-team.cc",
            "https://xp2.m-team.cc",
            "https://pt.m-team.cc",  # (大陸用戶不建議使用)
            "https://tp.m-team.cc",  # (大陸用戶不建議使用)
            "https://xp.m-team.io",
            "https://yp.m-team.io",
            "https://zp.m-team.io",
        ]
        parsed_url = urlparse(source)
        host = f"{parsed_url.scheme}://{parsed_url.netloc}"
        if host in host_list:
            return True
        return False

    @staticmethod
    # pylint: disable=unused-argument
    def get_links(source: str, **kwargs):
        host = kwargs.get("host")
        cookie = kwargs.get("cookie")
        proxy = kwargs.get("proxy")
        use_proxy = kwargs.get("use_proxy")
        if not all([host, cookie]):
            raise ValueError("host and cookie cannot be empty")
        mt = MTeam(host, cookie, proxy, use_proxy)
        return mt.parse(source)

    @staticmethod
    def search(keyword: str, page=1, **kwargs):
        host = kwargs.get("host")
        cookie = kwargs.get("cookie")
        proxy = kwargs.get("proxy")
        use_proxy = kwargs.get("use_proxy")
        if not all([host, cookie]):
            raise ValueError("host and cookie cannot be empty")
        mt = MTeam(host, cookie, proxy, use_proxy)
        return mt.search(keyword, page)

    @staticmethod
    def scheduler(**kwargs):
        host = kwargs.get("host")
        cookie = kwargs.get("cookie")
        proxy = kwargs.get("proxy")
        use_proxy = kwargs.get("use_proxy")
        if not all([host, cookie]):
            raise ValueError("host and cookie cannot be empty")
        mt = MTeam(host, cookie, proxy, use_proxy)
        return mt.scheduler()
