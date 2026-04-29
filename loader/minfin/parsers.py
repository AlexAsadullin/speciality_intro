import asyncio
import io
import json
import os
import re
import sys
from urllib.parse import urljoin

import httpx
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import (
    MINFIN_DIRS,
    MINFIN_OPENDATA_URL,
    MINFIN_DATASET_BUDGET,
    MINFIN_DATASET_FNB,
    MINFIN_BUDGET_HTML_URL,
    MINFIN_FNB_HTML_URL,
    MINFIN_DATA_LINK_REGEX,
    MINFIN_HTTP_TIMEOUT,
    MINFIN_USER_AGENT,
    MINFIN_OFZ_SECTIONS,
    MINFIN_BUDGET_SECTIONS,
    MINFIN_SCRAPE_DELAY_S,
    MINFIN_SCRAPE_TIMEOUT_S,
    MINFIN_SCRAPE_MAX_PAGES,
)
from loader.helpers import RunReport, ensure_dir

_DATA_LINK_RE = re.compile(MINFIN_DATA_LINK_REGEX)


async def _http_get(url: str) -> httpx.Response:
    print(f"  HTTP GET {url} (timeout={MINFIN_HTTP_TIMEOUT}s)")
    async with httpx.AsyncClient(
        headers={"User-Agent": MINFIN_USER_AGENT},
        timeout=MINFIN_HTTP_TIMEOUT,
        follow_redirects=True,
    ) as client:
        resp = await client.get(url)
    print(f"  HTTP {resp.status_code}, {len(resp.content)} bytes, "
          f"content-type={resp.headers.get('content-type', '?')}")
    resp.raise_for_status()
    return resp


async def _latest_csv_url(dataset_id: str, name: str) -> str | None:
    passport = f"{MINFIN_OPENDATA_URL}/{dataset_id}/"
    print(f"  scanning passport page {passport}")
    resp = await _http_get(passport)
    matches = _DATA_LINK_RE.findall(resp.text)
    print(f"  regex found {len(matches)} candidate CSV link(s)")
    if not matches:
        print(f"[minfin/{name}] no data-*.csv links on {passport}")
        return None
    url, stamp = max(matches, key=lambda m: m[1])
    print(f"  picked latest snapshot stamp={stamp} -> {url}")
    return url


async def _fetch_opendata_csv(dataset_id: str, name: str) -> pd.DataFrame:
    url = await _latest_csv_url(dataset_id, name)
    if not url:
        return pd.DataFrame()
    resp = await _http_get(url)
    text = resp.content.decode("utf-8-sig")
    print(f"  parsing CSV ({len(text)} chars)")
    df = pd.read_csv(io.StringIO(text))
    if df.empty:
        print(f"[minfin/{name}] CSV is empty: {url}")
        return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    print(f"  CSV parsed: {df.shape[0]} rows x {df.shape[1]} cols, columns={list(df.columns)[:8]}")
    return df


async def _fallback_html(url: str, name: str) -> pd.DataFrame:
    print(f"[minfin/{name}] -- HTML fallback")
    resp = await _http_get(url)
    print(f"  parsing HTML tables (response {len(resp.text)} chars)")
    tables = pd.read_html(io.StringIO(resp.text), thousands=" ", decimal=",")
    print(f"  found {len(tables)} HTML tables: sizes={[len(t) for t in tables]}")
    if not tables:
        return pd.DataFrame()
    df = max(tables, key=len).copy()
    df.columns = [str(c).strip() for c in df.columns]
    print(f"  picked largest table: {df.shape[0]} rows x {df.shape[1]} cols, columns={list(df.columns)[:8]}")
    return df


def _save(df: pd.DataFrame, out_dir: str, name: str) -> str:
    ensure_dir(out_dir)
    out_path = os.path.join(out_dir, f"{name}.csv")
    df.to_csv(out_path, index=False)
    print(f"  -> saved {len(df)} rows to {out_path}")
    return out_path


async def _fetch_dataset(dataset_id: str | None, html_url: str | None, name: str, out_dir: str) -> int:
    print(f"\n[minfin/{name}] === START ===")
    print(f"[minfin/{name}] dataset_id: {dataset_id or '(none, HTML only)'}")
    print(f"[minfin/{name}] target dir: {out_dir}")
    df = pd.DataFrame()
    if dataset_id:
        try:
            print(f"[minfin/{name}] step 1/2: OpenData CSV")
            df = await _fetch_opendata_csv(dataset_id, name)
            if not df.empty:
                print(f"[minfin/{name}] OpenData ok: {len(df)} rows")
            else:
                print(f"[minfin/{name}] OpenData returned empty dataframe")
        except Exception as e:
            print(f"[minfin/{name}] OpenData error: {type(e).__name__}: {e}")
    if df.empty and html_url:
        try:
            step = "step 2/2" if dataset_id else "step 1/1"
            print(f"[minfin/{name}] {step}: HTML fallback ({html_url})")
            df = await _fallback_html(html_url, name)
        except Exception as e:
            print(f"[minfin/{name}] HTML fallback error: {type(e).__name__}: {e}")
    if df.empty:
        print(f"[minfin/{name}] === FAIL: no data ===")
        return 0
    _save(df, out_dir, name)
    print(f"[minfin/{name}] === DONE: {len(df)} rows ===\n")
    return len(df)


async def budget() -> int:
    return await _fetch_dataset(MINFIN_DATASET_BUDGET, MINFIN_BUDGET_HTML_URL, "budget", MINFIN_DIRS["budget"])


async def fnb() -> int:
    return await _fetch_dataset(MINFIN_DATASET_FNB, MINFIN_FNB_HTML_URL, "fnb", MINFIN_DIRS["fnb"])


# ============================================================================
# doc-cards scraper для разделов minfin.gov.ru без OpenData
# (cloudscraper + BeautifulSoup; на основе parser_example.py)
# ============================================================================

_BASE = "https://minfin.gov.ru"


def _scrape_get(url: str):
    """cloudscraper-запрос с сохранением raw [] в URL (минфин режет %5B%5D)."""
    import cloudscraper
    import requests
    from bs4 import BeautifulSoup
    print(f"  HTTP GET {url} (cloudscraper, timeout={MINFIN_SCRAPE_TIMEOUT_S}s)")
    s = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )
    s.headers.update({"Accept-Language": "ru-RU,ru;q=0.9", "Referer": _BASE + "/"})
    req = requests.Request("GET", url)
    prep = s.prepare_request(req)
    prep.url = url  # отменяем автоматическое URL-кодирование скобок
    r = s.send(prep, timeout=MINFIN_SCRAPE_TIMEOUT_S)
    print(f"  HTTP {r.status_code} {r.reason}, {len(r.content)} bytes")
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def _parse_doc_cards(soup, source_url: str) -> list[dict]:
    """Извлекает карточки документов: a[href*='id_4='] + ближайшая дата + файлы + теги."""
    records, seen = [], set()
    for a in soup.select("a[href*='id_4=']"):
        href = a.get("href", "")
        title = a.get_text(strip=True)
        if not title or len(title) < 5 or href in seen:
            continue
        seen.add(href)
        page_url = urljoin(_BASE, href)
        container = a.parent
        for _ in range(6):
            if container is None:
                break
            txt = container.get_text(" ", strip=True)
            if re.search(r"\d{2}\.\d{2}\.\d{4}", txt) or container.select("a[href*='/common/upload/']"):
                break
            container = container.parent
        date_str, files, tags = "", [], []
        if container:
            m = re.search(r"\d{2}\.\d{2}\.\d{4}", container.get_text(" ", strip=True))
            date_str = m.group(0) if m else ""
            for fa in container.select("a[href*='/common/upload/']"):
                fh = fa.get("href", "")
                files.append({
                    "label": fa.get_text(strip=True),
                    "url": urljoin(_BASE, fh),
                    "ext": fh.rsplit(".", 1)[-1].lower() if "." in fh else "",
                })
            tags = [t.get_text(strip=True) for t in container.select("a[href*='TAG_ID']")]
        records.append({
            "title": title,
            "date": date_str,
            "tags": json.dumps(tags, ensure_ascii=False),
            "page_url": page_url,
            "files": json.dumps(files, ensure_ascii=False),
            "source_url": source_url,
        })
    return records


async def _scrape_pages(base_url: str, max_pages: int) -> list[dict]:
    records = []
    sep = "&" if "?" in base_url else "?"
    for page in range(1, max_pages + 1):
        url = base_url if page == 1 else f"{base_url}{sep}PAGEN_1={page}"
        try:
            soup = await asyncio.to_thread(_scrape_get, url)
        except Exception as e:
            print(f"  page {page} error: {type(e).__name__}: {e}")
            break
        await asyncio.sleep(MINFIN_SCRAPE_DELAY_S)
        page_records = _parse_doc_cards(soup, url)
        print(f"  page {page}: {len(page_records)} doc cards")
        if not page_records:
            break
        records.extend(page_records)
        has_next = soup.select_one("a.nav-btn-next") or soup.select_one(".pager a[title*='след']")
        if not has_next and page > 1:
            break
    return records


async def _scrape_section(url: str, section_name: str, max_pages: int) -> list[dict]:
    """Парсим карточки документов; если их нет -- забираем text-snippet секции."""
    records = await _scrape_pages(url, max_pages)
    if not records:
        try:
            soup = await asyncio.to_thread(_scrape_get, url)
            await asyncio.sleep(MINFIN_SCRAPE_DELAY_S)
        except Exception as e:
            print(f"  section snippet error: {type(e).__name__}: {e}")
            soup = None
        if soup:
            main = soup.select_one(".content-text, .mf-content, article, #content, main")
            snippet = re.sub(r"\s+", " ", main.get_text(" ", strip=True))[:800] if main else ""
            if snippet:
                records.append({
                    "title": section_name,
                    "date": "",
                    "tags": "[]",
                    "page_url": url,
                    "files": "[]",
                    "source_url": url,
                    "section": section_name,
                    "text_snippet": snippet,
                    "category": "section_text",
                })
                print(f"  no doc cards -> grabbed section snippet ({len(snippet)} chars)")
    for r in records:
        r.setdefault("section", section_name)
        r.setdefault("text_snippet", "")
    return records


def _dedup(records: list[dict]) -> list[dict]:
    seen, out = set(), []
    for r in records:
        k = r.get("page_url", "")
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


async def ofz_auctions() -> int:
    name = "ofz_auctions"
    print(f"\n[minfin/{name}] === START === (cloudscraper doc-cards)")
    print(f"[minfin/{name}] target dir: {MINFIN_DIRS[name]}")
    records = []
    for url, cat in MINFIN_OFZ_SECTIONS:
        print(f"\n[minfin/{name}] section [{cat}] <- {url}")
        for r in await _scrape_pages(url, MINFIN_SCRAPE_MAX_PAGES):
            r["category"] = cat
            r.setdefault("section", cat)
            r.setdefault("text_snippet", "")
            records.append(r)
    records = _dedup(records)
    if not records:
        print(f"[minfin/{name}] === FAIL: no data ===")
        return 0
    df = pd.DataFrame(records)
    _save(df, MINFIN_DIRS[name], name)
    print(f"[minfin/{name}] === DONE: {len(df)} rows ===\n")
    return len(df)


async def state_support() -> int:
    name = "state_support"
    print(f"\n[minfin/{name}] === START === (cloudscraper doc-cards)")
    print(f"[minfin/{name}] target dir: {MINFIN_DIRS[name]}")
    records = []
    for section_name, url in MINFIN_BUDGET_SECTIONS:
        print(f"\n[minfin/{name}] section [{section_name}] <- {url}")
        for r in await _scrape_section(url, section_name, MINFIN_SCRAPE_MAX_PAGES):
            r.setdefault("category", "document")
            records.append(r)
    records = _dedup(records)
    if not records:
        print(f"[minfin/{name}] === FAIL: no data ===")
        return 0
    df = pd.DataFrame(records)
    _save(df, MINFIN_DIRS[name], name)
    print(f"[minfin/{name}] === DONE: {len(df)} rows ===\n")
    return len(df)


async def main() -> None:
    print("\n========== Minfin (opendata + minfin.gov.ru) loader ==========\n")
    report = RunReport("minfin")
    await report.run("budget", budget)
    await report.run("fnb", fnb)
    await report.run("ofz_auctions", ofz_auctions)
    await report.run("state_support", state_support)
    report.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
