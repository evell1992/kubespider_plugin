import math
import os
from urllib.parse import urljoin, quote

from kubespider_source_provider_sdk import SDK, ProviderType, Resource, LinkType, FileType
from kubespider_source_provider_sdk.utils import get_request_controller, get_unique_hash


@SDK(ProviderType.parser)
class AlistProvider:
    @staticmethod
    def should_handle(source: str, **kwargs):
        return True

    @staticmethod
    def parser(source: str, **kwargs):
        cookie = kwargs.get("cookie", "")
        files = []
        return files

    @staticmethod
    def search(keyword, **kwargs):
        tags = kwargs.get("tags", [])
        return []

    @staticmethod
    def seeding(**kwargs):
        max_count = kwargs.get("max_count", 20)
        auto_replace = kwargs.get("auto_replace", True)
        return []
