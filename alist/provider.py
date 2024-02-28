import math
import os
from urllib.parse import urljoin, quote

from kubespider_source_provider_sdk import SDK, ProviderType, Resource, LinkType, FileType
from kubespider_source_provider_sdk.utils import get_request_controller, get_unique_hash


@SDK(ProviderType.parser)
class AlistProvider:
    @staticmethod
    # pylint: disable=unused-argument
    def should_handle(source: str, **kwargs):
        return False

    @staticmethod
    # pylint: disable=unused-argument
    def get_links(source: str, **kwargs):
        host = kwargs.get("host", "")
        watch_dirs = kwargs.get("watch_dirs", [])
        proxy = kwargs.get("proxy", "")
        cookie = kwargs.get("cookie", "")
        request_handler = get_request_controller(proxy, cookie, False)
        if not all([host, watch_dirs]):
            raise ValueError("Please provide both host and watch_dirs")

        def fs_list(page, per_page, path) -> tuple:
            data = {
                "path": path,
                "password": "",
                "page": page,
                "per_page": per_page,
                "refresh": False
            }
            url = urljoin(host, "/api/fs/list")
            resp = request_handler.post(url, json=data).json()
            code = resp.get("code")
            content = resp.get("data").get("content")
            alist_provider = resp.get("data").get("provider")
            total = resp.get("data").get("total")
            if code == 200:
                return content, alist_provider, total
            raise ValueError(f"response error: {resp}")

        def list_dir(path="/", per_page=30):
            total_page = 1
            page = 1
            while page <= total_page:
                res = fs_list(page, per_page, path)
                if res:
                    content, alist_provider, total = res
                    total_page = math.ceil(total / per_page)
                    for item in content:
                        item['provider'] = alist_provider
                        item['path'] = os.path.join(path, item.get("name")) if item.get("is_dir") else path
                        yield item
                page += 1

        def get_all_files(path) -> list[Resource]:
            files = []
            for item in list_dir(path):
                if item.get("is_dir") is True:
                    new_path = os.path.join(path, item.get("name"))
                    files += get_all_files(new_path)
                else:
                    uri = os.path.join("/d", os.path.join(item.get("path", "").strip('/'), item.get("name", "")))
                    md5 = (item.get("hash_info") or {}).get("md5", get_unique_hash(uri))
                    sign = item.get("sign", "")
                    modified = item.get("modified", "")
                    item["link"] = urljoin(host, quote(uri) + f'?modified={modified}&sign={sign}')
                    resource = Resource(
                        url=item.pop("link"),
                        title=item.pop("name", ""),
                        path=item.pop("path"),
                        link_type=LinkType.general,
                        file_type=FileType.common,
                        uuid=md5,
                        **item
                    )
                    files.append(resource.data)
            return files

        files = []
        for path in watch_dirs:
            files += get_all_files(path)
        return files
