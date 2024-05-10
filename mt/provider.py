import logging
import math
import re
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from kubespider_plugin import SDK, SchedulerProvider, Resource, LinkType, FileType
from kubespider_plugin.utils import get_request_controller
from kubespider_plugin.values import KubespiderContext


def convert_bigger_size(size: int, unit: str) -> tuple[float, str]:
    units = ["B", "KB", "MB", "GB", "TB", "PB", "EB"]
    if unit not in units:
        raise ValueError(f"Unit must be one of {units}")
    index = units.index(unit)
    exponent = int(math.log(size, 1024))
    allow_exponent = exponent if (index + exponent) < len(units) - 1 else len(units) - index - 1
    if exponent > 0:
        return round(size / (1024 ** allow_exponent), 2), units[index + allow_exponent]
    return size, unit


class MTeam:
    def __init__(self, host: str, token: str, proxy="", use_proxy=False):
        self.host = host
        self.headers = {
            "Authorization": token,
        }
        self.request_handler = requests.session()
        self.request_handler.headers = self.headers

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
        resp = self.request_handler.post(urljoin(self.host, "/api/torrent/detail"),
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
                result = [Resource(
                    url=torrent_url,
                    link_type=LinkType.torrent,
                    file_type=FileType.general,
                    **data
                ).data]
                return result
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
            "data": [Resource(
                url=urljoin(self.host, f"/detail/{item.get('id')}"),
                link_type=LinkType.general,
                **item
            ).data for item in data]
        }

    def scheduler(self, **kwargs):
        if kwargs.get("push_info"):
            message = self.get_news() + self.get_new_mails()
            message.append(self.get_profile())
        if kwargs.get("allow_seeding"):
            resp = self.request_handler.post(urljoin(self.host, "/api/tracker/myPeerStatus")).json()
            seeding_count = int(resp.get("data", {}).get("leecher", 0)) + int(resp.get("data", {}).get("seeder", 0))
            # 替换
            if kwargs.get("max_seeding") >= seeding_count:
                # 允许替换
                if kwargs.get("allow_delete_seed"):
                    pass
            # 新增
            else:
                pass

    def get_new_mails(self):
        resp = self.request_handler.post(urljoin(self.host, "/api/msg/notify/statistic")).json()
        unread_count = int(resp.get("data", {}).get("unMake", 0))
        unread_message = []
        if unread_count:
            post_datas = [
                {"keyword": "", "box": 1, "pageNumber": 1, "pageSize": 100},  # 收件箱
                {"keyword": "", "box": -2, "pageNumber": 1, "pageSize": 100},  # 系统信息
            ]
            for data in post_datas:
                resp = self.request_handler.post(urljoin(self.host, "/api/msg/search"), data=data).json()
                for message in resp.get("data", {}).get("data", []):
                    unread = message.get("unread")
                    if unread:
                        msg_id = message.get("id")
                        title = message.get("title")
                        context = message.get("context")
                        modify_date = message.get("lastModifiedDate")  # 2024-04-17 23:19:45
                        # read message
                        self.request_handler.post(urljoin(self.host, "/api/msg/markRead"),
                                                  data={"msgIds": msg_id}).json()
                        unread_message.append({"title": title, "date": modify_date, "context": context})
        return unread_message

    def get_news(self):
        resp = self.request_handler.post(urljoin(self.host, "/api/news/list")).json()
        news_list = []
        for news in resp.get("data", []):
            title = news.get("subject")
            context = news.get("context")
            modify_date = news.get("lastModifiedDate")
            modify_date_time = datetime.strptime(modify_date, '%Y-%m-%d %H:%M:%S')
            if modify_date_time.date() == datetime.now().date():
                news_list.append({"title": title, "date": modify_date, "context": context})
        return news_list

    def get_profile(self):
        resp = self.request_handler.post(urljoin(self.host, "/api/member/profile")).json()
        share_rate = resp.get("data", {}).get("memberCount", {}).get("shareRate")
        bonus = resp.get("data", {}).get("memberCount", {}).get("bonus")
        upload = convert_bigger_size(int(resp.get("data", {}).get("memberCount", {}).get("uploaded", 0)), "B")
        download = convert_bigger_size(int(resp.get("data", {}).get("memberCount", {}).get("downloaded", 0)), "B")
        resp = self.request_handler.post(urljoin(self.host, "/api/tracker/myPeerStatus")).json()
        leach = resp.get("data", {}).get("leecher")
        seed = resp.get("data", {}).get("seeder")
        return {
            "leach": leach,
            "seed": seed,
            "share_rate": share_rate,
            "bonus": bonus,
            "upload": f"{upload[0]} {upload[1]}",
            "download": f"{download[0]} {download[1]}",
        }

    def get_seeding_info(self):
        post_data = {
            "pageNumber": 1,
            "pageSize": 100,
            "type": "INCOMPLETE",  # LEECHING INCOMPLETE SEEDING COMPLETED
            "userid": "",
        }
        resp = self.request_handler.post(urljoin(self.host, "/api/member/getUserTorrentList")).json()


@SDK()
class MTeamProvider(SchedulerProvider):
    @staticmethod
    # pylint: disable=unused-argument
    def should_handle(source: str, context: KubespiderContext, **kwargs):
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
    def get_links(source: str, context: KubespiderContext, **kwargs):
        host = kwargs.get("host")
        token = kwargs.get("token")
        proxy = kwargs.get("proxy")
        use_proxy = kwargs.get("use_proxy")
        if not all([host, token]):
            raise ValueError("host and token cannot be empty")
        mt = MTeam(host, token, proxy, use_proxy)
        return mt.parse(source)

    @staticmethod
    def search(keyword: str, page: int, context: KubespiderContext, **kwargs):
        host = kwargs.get("host")
        token = kwargs.get("token")
        use_proxy = kwargs.get("use_proxy")
        if not all([host, token]):
            raise ValueError("host and cookie cannot be empty")
        mt = MTeam(host, token, context.proxy, use_proxy)
        return mt.search(keyword, page)

    @staticmethod
    def scheduler(context: KubespiderContext, **kwargs):
        host = kwargs.get("host")
        token = kwargs.get("token")
        proxy = kwargs.get("proxy")
        use_proxy = kwargs.get("use_proxy")
        if not all([host, token]):
            raise ValueError("host and cookie cannot be empty")
        mt = MTeam(host, token, proxy, use_proxy)
        return mt.scheduler(**kwargs)
