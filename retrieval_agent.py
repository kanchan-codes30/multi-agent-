"""Fast retrieval from Wikipedia, arXiv and Crossref."""
import re
import html
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from agents.base_agent import BaseAgent

TIMEOUT = 9
MAX_CONTENT = 6500

HEADERS = {
    "User-Agent": "MultiAgentResearchAssistant/1.0 (educational project)"
}


def clean_text(value):
    """Remove HTML/XML tags and normalize whitespace."""
    value = html.unescape(re.sub(r"<[^>]+>", " ", value or ""))
    return re.sub(r"\s+", " ", value).strip()


class RetrievalAgent(BaseAgent):

    def __init__(self):
        super().__init__("Information Retrieval Agent")

    def _get(self, url, params=None):
        response = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        response.raise_for_status()
        return response

    def _fetch_wikipedia(self, topic):
        results = []

        api = "https://en.wikipedia.org/w/api.php"

        try:
            data = self._get(
                api,
                {
                    "action": "query",
                    "list": "search",
                    "srsearch": topic,
                    "format": "json",
                    "srlimit": 2
                }
            ).json()

            pages = data.get("query", {}).get("search", [])

            for item in pages:
                title = item.get("title", "")

                if not title:
                    continue

                extract_data = self._get(
                    api,
                    {
                        "action": "query",
                        "prop": "extracts",
                        "explaintext": 1,
                        "exsectionformat": "plain",
                        "titles": title,
                        "format": "json",
                        "redirects": 1
                    }
                ).json()

                page_data = extract_data.get("query", {}).get("pages", {})

                for page in page_data.values():
                    content = (page.get("extract") or "").strip()

                    if len(content) >= 250:
                        results.append({
                            "title": page.get("title", title),
                            "url": (
                                "https://en.wikipedia.org/wiki/"
                                + title.replace(" ", "_")
                            ),
                            "content": content[:MAX_CONTENT],
                            "source_type": "wikipedia",
                            "authors": [],
                            "year": None,
                            "doi": ""
                        })

        except requests.RequestException as exc:
            self.log(
                f"Wikipedia unavailable: {exc.__class__.__name__}"
            )

        except (ValueError, KeyError) as exc:
            self.log(f"Wikipedia response could not be parsed: {exc}")

        return results

    def _fetch_arxiv(self, topic):
        results = []

        try:
            response = self._get(
                "https://export.arxiv.org/api/query",
                {
                    "search_query": f'all:"{topic}"',
                    "start": 0,
                    "max_results": 4,
                    "sortBy": "relevance",
                    "sortOrder": "descending"
                }
            )

            root = ET.fromstring(response.text)

            namespace = {
                "a": "http://www.w3.org/2005/Atom"
            }

            entries = root.findall("a:entry", namespace)

            for entry in entries:
                title = clean_text(
                    entry.findtext(
                        "a:title",
                        default="",
                        namespaces=namespace
                    )
                )

                abstract = clean_text(
                    entry.findtext(
                        "a:summary",
                        default="",
                        namespaces=namespace
                    )
                )

                url = entry.findtext(
                    "a:id",
                    default="",
                    namespaces=namespace
                ).strip()

                authors = [
                    author.findtext(
                        "a:name",
                        default="",
                        namespaces=namespace
                    )
                    for author in entry.findall(
                        "a:author",
                        namespace
                    )
                ]

                published = entry.findtext(
                    "a:published",
                    default="",
                    namespaces=namespace
                )

                year = published[:4] if published else None

                if title and len(abstract) >= 180 and url:
                    results.append({
                        "title": title,
                        "url": url,
                        "content": abstract[:MAX_CONTENT],
                        "source_type": "arxiv",
                        "authors": authors,
                        "year": year,
                        "doi": ""
                    })

        except requests.RequestException as exc:
            self.log(
                f"arXiv unavailable: {exc.__class__.__name__}"
            )

        except ET.ParseError as exc:
            self.log(f"arXiv XML parsing failed: {exc}")

        return results

    def _fetch_crossref(self, topic):
        results = []

        try:
            data = self._get(
                "https://api.crossref.org/works",
                {
                    "query.title": topic,
                    "rows": 5,
                    "select": (
                        "title,author,published,created,"
                        "abstract,URL,DOI,type"
                    )
                }
            ).json()

            items = data.get("message", {}).get("items", [])

            for item in items:
                titles = item.get("title") or []

                title = (
                    clean_text(titles[0])
                    if titles else ""
                )

                abstract = clean_text(
                    item.get("abstract", "")
                )

                url = item.get("URL", "")

                # Do not treat metadata-only records as research evidence.
                if not title or len(abstract) < 180 or not url:
                    continue

                authors = []

                for author in item.get("author", []):
                    name = " ".join(
                        part
                        for part in [
                            author.get("given"),
                            author.get("family")
                        ]
                        if part
                    )

                    if name:
                        authors.append(name)

                date_parts = (
                    item.get("published", {}).get("date-parts")
                    or item.get("created", {}).get("date-parts")
                    or [[]]
                )[0]

                year = str(date_parts[0]) if date_parts else None

                results.append({
                    "title": title,
                    "url": url,
                    "content": abstract[:MAX_CONTENT],
                    "source_type": "crossref",
                    "authors": authors,
                    "year": year,
                    "doi": item.get("DOI", "")
                })

        except requests.RequestException as exc:
            self.log(
                f"Crossref unavailable: {exc.__class__.__name__}"
            )

        except (ValueError, KeyError, TypeError) as exc:
            self.log(f"Crossref response could not be parsed: {exc}")

        return results

    def run(self, topic):
        topic = (topic or "").strip()

        if len(topic) < 3:
            raise ValueError(
                "Please enter a research topic containing "
                "at least 3 characters."
            )

        self.log(
            f"Searching Wikipedia, arXiv and Crossref for: {topic}"
        )

        providers = [
            self._fetch_wikipedia,
            self._fetch_arxiv,
            self._fetch_crossref
        ]

        results = []

        # Run all three independent searches concurrently.
        with ThreadPoolExecutor(max_workers=3) as executor:

            futures = [
                executor.submit(provider, topic)
                for provider in providers
            ]

            for future in as_completed(futures):
                try:
                    results.extend(future.result())

                except Exception as exc:
                    self.log(
                        f"A source provider failed: "
                        f"{exc.__class__.__name__}"
                    )

        # Remove duplicate sources.
        unique_results = []
        seen = set()

        for source in results:
            key = (
                source.get("doi")
                or source.get("url")
                or source.get("title", "")
            ).lower().rstrip("/")

            if (
                key
                and key not in seen
                and len(source.get("content", "")) >= 180
            ):
                seen.add(key)
                unique_results.append(source)

        self.log(
            f"Retrieved {len(unique_results)} genuine source(s)"
        )

        if not unique_results:
            raise RuntimeError(
                "No usable sources were returned by Wikipedia, "
                "arXiv or Crossref. Check your internet connection "
                "or try a more specific topic. "
                "No placeholder report was created."
            )

        return unique_results[:8]