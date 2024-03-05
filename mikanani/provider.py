# This works for: https://mikanani.me
# Function: download anime you subscribe
# encoding:utf-8
import logging
import xml.etree.ElementTree as ET
import re
from re import Pattern
from bs4 import BeautifulSoup
from kubespider_source_provider_sdk import SDK, ProviderType, LinkType, Resource, FileType
from kubespider_source_provider_sdk.utils import get_request_controller, format_long_string


def get_anime_title(element, pattern: Pattern) -> str:
    # get the episode name of anime source, or None for invalid item
    title = element.find('./title').text
    logging.debug("[Mikanani:Parser] Checking title %s with pattern %s", title, pattern)
    if pattern is None or pattern.match(title):
        return title
    logging.warning("[Mikanani:Parser] Episode %s will not be downloaded, filtered by %s", title, pattern)
    return ""


def get_anime_path(element, request_handler) -> str:
    # get the path of anime source, or None for invalid item
    link = element.find('./link').text
    # example: https://mikanani.me/Home/Episode/5350b283db7d8e4665a08dda24d0d0c66259fc71
    try:
        data = request_handler.get(link, timeout=30).content
    except Exception as err:
        logging.info('[Mikanani:Parser] get anime title error:%s', err)
        return None
    dom = BeautifulSoup(data, 'html.parser')
    titles = dom.find_all('a', ['class', 'w-other-c'])
    if len(titles) == 0:
        logging.error('[Mikanani:Parser] get anime title empty:%s', link)
        return None
    title = titles[0].text.strip()
    logging.info('[Mikanani:Parser] get anime title:%s', title)
    return title


def get_links_from_xml(content, pattern: str, link_type, request_handler, auto_download=False):
    if pattern is not None:
        reg = re.compile(pattern)
    else:
        reg = None
    try:
        xml_parse = ET.fromstring(content)
        items = xml_parse.findall('.//item')
        ret = []
        for i in items:
            anime_name = i.find('./guid').text
            path = None
            try_count = 0
            while path is None and try_count < 6:
                path = get_anime_path(i, request_handler)
                try_count += 1
            item_title = get_anime_title(i, reg)
            logging.info('[Mikanani:Parser] find %s', format_long_string(anime_name))
            url = i.find('./enclosure').attrib['url']
            if path is not None and item_title is not None:
                ret.append(Resource(
                    url=url,
                    path=path,
                    title=item_title,
                    file_type=FileType.tv,
                    link_type=link_type,
                    auto_download=auto_download
                ).data)
            else:
                logging.warning("[Mikanani:Parser] Skip %s, %s", anime_name, item_title)
        return ret
    except Exception as err:
        logging.info('[Mikanani:Parser] parse rss xml error:%s', err)
        return []


@SDK(ProviderType.parser)
class MikanAniProvider:
    @staticmethod
    # pylint: disable=unused-argument
    def should_handle(source: str, **kwargs):
        return False

    @staticmethod
    # pylint: disable=unused-argument
    def get_links(source: str, **kwargs):
        pattern = kwargs.get("pattern", "")
        auto_download = kwargs.get("auto_download", False)
        proxy = kwargs.get("proxy", "")
        cookie = kwargs.get("cookie", "")
        request_handler = get_request_controller(proxy, cookie, False)
        resources = []
        try:
            content = request_handler.get(source, timeout=30).text
            resources += get_links_from_xml(content, pattern, LinkType.torrent, request_handler,
                                            auto_download)
        except Exception as err:
            logging.info('[Mikanani:Parser] get links error: %s', err)
        return resources
