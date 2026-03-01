import sys
import os
import yaml
from loguru import logger
from pathlib import Path
import ezkfg as ez
import urllib.parse
import requests
import json
import time
import random
import re
import xml.etree.ElementTree as ET
import datetime
from typing import Optional

DEFAULT_HEADER = {
    "title": "Title",
    "venue": " Venue",
    "year": " Year ",
    "link": "Link",
}

DEFAULT_LENGTH = {
    "title": 60,
    "venue": 53,
    "year": 4,
    "link": 60,
}

def init_log():
    """Initialize loguru log information"""
    event_logger_format = (
        "<g>{time:YYYY-MM-DD HH:mm:ss}</g> | "
        "<lvl>{level}</lvl> - "
        # "<c><u>{name}</u></c> | "
        "{message}"
    )
    logger.remove()
    logger.add(
        sink=sys.stdout,
        colorize=True,
        level="DEBUG",
        format=event_logger_format,
        diagnose=False,
    )

    return logger


def init_path(cfg):
    cfg["cache_path"] = Path("./../cached")
    cfg["cache_path"].mkdir(parents=True, exist_ok=True)

    return cfg


def init(cfg_path: str):
    cfg = ez.Config().load(cfg_path)
    cfg = init_path(cfg)
    init_log()
    return cfg


def get_item_info(item, key):
    try:
        return item[key]
    except KeyError:
        return ""


def get_dblp_items(dblp_data):
    try:
        items = dblp_data["result"]["hits"]["hit"]
    except KeyError:
        items = []

    # item{'author', 'title', 'venue', 'year', 'type', 'access', 'key', 'doi', 'ee', 'url'}
    res_items = []

    for item in items:
        res_item = {}
        # format author
        authors = get_item_info(item["info"], "authors")
        try:
            authors = [author["text"] for author in authors["author"]]
        except TypeError:
            if "author" not in authors:
                continue
            if "text" not in authors["author"]:
                continue

            authors = [authors["author"]["text"]]

        # logger.info(f"authors: {authors}")

        res_item["author"] = ", ".join(authors)
        needed_keys = [
            "title",
            "venue",
            "year",
            "type",
            "access",
            "key",
            "doi",
            "ee",
            "url",
        ]
        for key in needed_keys:
            key_temp = get_item_info(item["info"], key)
            res_item[key] = key_temp if key_temp else ""

        res_items.append(res_item)

    return res_items


def get_msg(items, topic, cfilename, aggregated=False):
    # change "topic" from url to string
    string_topic = urllib.parse.unquote(topic)
    # get name of topic
    name_topic = string_topic.split(":")[-2]

    # print information of topic
    research_topic = " ".join([c[0].upper()+c[1:] for c in cfilename.split("-")])
    msg = f"# {research_topic} - New papers about {research_topic}\n\n"
    msg += f"## [{name_topic}](https://dblp.org/search?q={topic})\n\n"
    msg += f"""Explore {len(items)} new papers about {name_topic}.\n\n"""

    if aggregated == False:
        for item in items:
            msg += f"{item['title']}\n"
            # msg += f"[{item['title']}]({item['url']})\n"
            # msg += f"- Authors: {item['author']}\n"
            # msg += f"- Venue: {item['venue']}\n"
            msg += f"- Year: {item['year']}\n\n"

    msg = msg.replace("'", "")
    return msg

def request_data(url, retry=3, sleep_time=5):
    try:
        time.sleep(sleep_time + random.random() * 5)  # sleep to avoid being blocked
        response = requests.get(url)
        response.raise_for_status()  # 如果响应状态不是200，将引发HTTPError异常
        data = response.json()
    # deal with errors
    except Exception as e:
        logger.error(f"Exception: {e}")
        if retry > 0:
            logger.info(f"retrying {url}")
            return request_data(url, retry - 1)
        else:
            logger.error(f"Failed to request {url}")
        return None
    else:
        return data

def normalize_title(title: str) -> str:
    if not title:
        return ""
    return re.sub(r"[^a-z0-9]+", "", title.lower())

def extract_arxiv_id(link: str) -> str:
    if not link:
        return ""
    match = re.search(r"arxiv\.org/(?:abs|pdf)/([^?#/]+)", link)
    if not match:
        return ""
    arxiv_id = match.group(1)
    if "v" in arxiv_id:
        arxiv_id = arxiv_id.split("v")[0]
    return arxiv_id

def build_public_index(data_dir: Path):
    title_year = set()
    arxiv_ids = set()

    for yaml_path in data_dir.glob("*.yaml"):
        try:
            data = yaml.safe_load(open(yaml_path)) or {}
        except Exception:
            continue

        for venue, venue_data in data.items():
            if venue == "section" or not isinstance(venue_data, dict):
                continue
            for year, year_block in venue_data.items():
                body = year_block.get("body", [])
                if not isinstance(body, list):
                    continue
                for item in body:
                    title = item.get("title", "")
                    year_val = str(item.get("year", ""))
                    if title:
                        title_year.add((normalize_title(title), year_val))
                    link = item.get("link") or item.get("url") or ""
                    arxiv_id = extract_arxiv_id(link)
                    if arxiv_id:
                        arxiv_ids.add(arxiv_id)

    return {"title_year": title_year, "arxiv_ids": arxiv_ids}

def extract_arxiv_query_terms(dblp_topics):
    terms = set()
    for raw in dblp_topics or []:
        decoded = urllib.parse.unquote(raw)
        if "%" in decoded:
            decoded = decoded.replace("%", " ")

        markers = [
            " venue:",
            " streamid:",
            " type:",
            " title:",
            " author:",
            " year:",
        ]
        cut = len(decoded)
        for marker in markers:
            idx = decoded.find(marker)
            if idx != -1 and idx < cut:
                cut = idx

        phrase = decoded[:cut].strip()
        phrase = re.sub(r"\s+", " ", phrase)
        if phrase:
            terms.add(phrase)

    return sorted(terms)

def build_arxiv_query(term: str) -> str:
    term = term.strip()
    if " " in term:
        return f'all:"{term}"'
    return f"all:{term}"

def request_arxiv_data(query: str, max_results: int = 50, start: int = 0, retry: int = 3, sleep_time: int = 5):
    base_url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": query,
        "start": str(start),
        "max_results": str(max_results),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": "awesome-topics-bot/1.0"}

    try:
        time.sleep(sleep_time + random.random() * 3)
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"Exception: {e}")
        if retry > 0:
            logger.info(f"retrying {url}")
            return request_arxiv_data(query, max_results=max_results, start=start, retry=retry - 1)
        logger.error(f"Failed to request {url}")
        return None

def parse_arxiv_feed(xml_text: str):
    if not xml_text:
        return []

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    items = []
    for entry in root.findall("atom:entry", ns):
        title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
        published = entry.findtext("atom:published", default="", namespaces=ns)
        entry_id = entry.findtext("atom:id", default="", namespaces=ns)
        authors = [a.findtext("atom:name", default="", namespaces=ns) for a in entry.findall("atom:author", ns)]
        authors = [a for a in authors if a]

        journal_ref = entry.findtext("arxiv:journal_ref", default="", namespaces=ns)
        doi = entry.findtext("arxiv:doi", default="", namespaces=ns)

        year = ""
        if published:
            year = published.split("-")[0]

        arxiv_id = extract_arxiv_id(entry_id)
        items.append({
            "title": title,
            "author": ", ".join(authors),
            "venue": "arXiv",
            "year": year,
            "url": entry_id,
            "published": published,
            "arxiv_id": arxiv_id,
            "journal_ref": journal_ref or "",
            "doi": doi or "",
        })

    return items

def _parse_published_date(published: str):
    if not published:
        return None
    try:
        return datetime.date.fromisoformat(published[:10])
    except ValueError:
        return None

def get_arxiv_items(query: str, max_results: int = 50, since_date: Optional[datetime.date] = None):
    all_items = []
    start = 0
    page_size = max_results

    while True:
        xml_text = request_arxiv_data(query, max_results=page_size, start=start)
        items = parse_arxiv_feed(xml_text)
        if not items:
            break

        stop_after_page = False
        for item in items:
            if since_date:
                published_date = _parse_published_date(item.get("published", ""))
                if published_date and published_date < since_date:
                    stop_after_page = True
                    continue
            all_items.append(item)

        if since_date and stop_after_page:
            break

        start += page_size

    return all_items
    
def update_yaml_from_dblp(items, topic, yaml_path):
    if not yaml_path.exists():
        data = {"section": []}
    else:
        data = yaml.safe_load(open(yaml_path)) or {"section": []}

    section_title = urllib.parse.unquote(topic).split(":")[-2]

    # ensure section exists
    if section_title not in data:
        data["section"].append({"title": section_title})
        data[section_title] = []

    existing = data[section_title]

    # deduplicate by title + year
    existing_keys = {(p["title"], p["year"]) for p in existing}

    for item in items:
        key = (item["title"], item["year"])
        if key in existing_keys:
            continue

        existing.append({
            "title": item["title"],
            "authors": item["author"],
            "venue": item["venue"],
            "year": item["year"],
            "url": item["url"] or item["ee"],
        })

    yaml.safe_dump(data, open(yaml_path, "w"), sort_keys=False)


# ... (rest of your imports and init functions remain the same)

def normalize_data_schema(data):
    if not isinstance(data, dict):
        data = {}
    data.setdefault("section", [])
    return data

def write_venue_yaml(items, yaml_path):
    """
    Write DBLP items into specific data yaml in _data/
    """
    if yaml_path.exists():
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}

    # ---- schema normalization ----
    data = normalize_data_schema(data)

    for item in items:
        venue = item.get("venue", "Unknown Venue")
        year = str(item.get("year", "Unknown Year"))
        link = item.get("ee") or item.get("url")

        # Ensure section entry exists for the UI/Table of Contents
        if not any(s['title'] == venue for s in data["section"]):
            data["section"].append({"title": venue})
        
        if venue not in data:
            data[venue] = {}

        if year not in data[venue]:
            data[venue][year] = {
                "header": DEFAULT_HEADER.copy(),
                "length": DEFAULT_LENGTH.copy(),
                "body": [],
            }

        body = data[venue][year]["body"]
        existing_titles = {p["title"] for p in body}
        
        if item["title"] not in existing_titles:
            body.append({
                "title": item["title"],
                "venue": venue,
                "year": int(year) if year.isdigit() else year,
                "link": link,
            })
            body.sort(key=lambda x: x["title"])

    # Sort years descending
    for key in data:
        if key != "section" and isinstance(data[key], dict):
            data[key] = dict(sorted(data[key].items(), key=lambda x: x[0], reverse=True))

    with open(yaml_path, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False, indent=2)
