import math
import os
from urllib.parse import urljoin, quote

from kubespider_source_provider_sdk import SDK, SchedulerProvider, Resource, LinkType, FileType
from kubespider_source_provider_sdk.utils import get_request_controller, get_unique_hash


class MTeam:
    def __init__(self, host: str, cookie: str):
        pass

    def get_links(self, source):
        return [
            Resource(
                url="http://m-team.getlink.test",
                link_type=LinkType.general,
            ).data
        ]

    def search(self, keyword, page):
        return [
            Resource(
                url="http://m-team.search.test",
                link_type=LinkType.general,
            ).data
        ]

    def scheduler(self, auto_download_resource):
        return [
            Resource(
                url="http://m-team.scheduler.test",
                link_type=LinkType.general,
                auto_download=auto_download_resource
            ).data
        ]


@SDK()
class MTeamProvider(SchedulerProvider):
    @staticmethod
    # pylint: disable=unused-argument
    def should_handle(source: str, **kwargs):
        return False

    @staticmethod
    # pylint: disable=unused-argument
    def get_links(source: str, **kwargs):
        host = kwargs.get("host")
        cookie = kwargs.get("cookie")
        if not all([host, cookie]):
            raise ValueError("host and cookie cannot be empty")
        mt = MTeam(host, cookie)
        return mt.get_links(source)

    @staticmethod
    def search(keyword: str, page=1, **kwargs):
        host = kwargs.get("host")
        cookie = kwargs.get("cookie")
        if not all([host, cookie]):
            raise ValueError("host and cookie cannot be empty")
        mt = MTeam(host, cookie)
        return mt.search(keyword, page)

    @staticmethod
    def scheduler(auto_download_resource: bool, **kwargs):
        host = kwargs.get("host")
        cookie = kwargs.get("cookie")
        if not all([host, cookie]):
            raise ValueError("host and cookie cannot be empty")
        mt = MTeam(host, cookie)
        return mt.scheduler(auto_download_resource)
