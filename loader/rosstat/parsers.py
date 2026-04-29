import asyncio
import io
import os
import sys

import httpx
import pandas as pd
from lxml import etree

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import (
    ROSSTAT_DIRS,
    FEDSTAT_CPI_URL,
    FEDSTAT_IPP_URL,
    FEDSTAT_SDMX_NS,
    ROSSTAT_HTTP_TIMEOUT,
    ROSSTAT_USER_AGENT,
)
from loader.helpers import RunReport, ensure_dir


async def _http_get(url: str) -> httpx.Response:
    print(f"  HTTP GET {url} (timeout={ROSSTAT_HTTP_TIMEOUT}s)")
    async with httpx.AsyncClient(
        headers={"User-Agent": ROSSTAT_USER_AGENT},
        timeout=ROSSTAT_HTTP_TIMEOUT,
        follow_redirects=True,
    ) as client:
        resp = await client.get(url)
    print(f"  HTTP {resp.status_code}, {len(resp.content)} bytes, "
          f"content-type={resp.headers.get('content-type', '?')}")
    resp.raise_for_status()
    return resp


def _parse_sdmx_to_df(xml_bytes: bytes) -> pd.DataFrame:
    print(f"  parsing SDMX XML ({len(xml_bytes)} bytes)")
    root = etree.fromstring(xml_bytes)
    rows: list[dict] = []
    series_count = 0
    for series in root.iter(f"{{{FEDSTAT_SDMX_NS['gen']}}}Series"):
        series_count += 1
        series_key: dict[str, str] = {}
        for kv in series.iter(f"{{{FEDSTAT_SDMX_NS['gen']}}}Value"):
            concept = kv.get("concept", "")
            value = kv.get("value", "")
            if concept:
                series_key[concept] = value
        obs_count_in_series = 0
        for obs in series.iter(f"{{{FEDSTAT_SDMX_NS['gen']}}}Obs"):
            time_el = obs.find(f"{{{FEDSTAT_SDMX_NS['gen']}}}Time")
            value_el = obs.find(f"{{{FEDSTAT_SDMX_NS['gen']}}}ObsValue")
            if time_el is None or value_el is None:
                continue
            time_text = time_el.text
            value_text = value_el.get("value")
            if time_text and value_text:
                row = dict(series_key)
                row["date"] = time_text
                row["value"] = value_text.replace(",", ".")
                rows.append(row)
                obs_count_in_series += 1
        if series_count <= 5:
            print(f"    series #{series_count} key={series_key}: {obs_count_in_series} obs")
    print(f"  SDMX parsed: {series_count} series, {len(rows)} total observations")
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    if "date" in df.columns and not df.empty:
        print(f"  date range: {df['date'].min()} .. {df['date'].max()}, "
              f"NaN values: {df['value'].isna().sum()}")
    return df


async def _fallback_html(url: str, name: str) -> pd.DataFrame:
    indicator_url = url.replace("/data.do?", "?").replace("&format=sdmx", "")
    print(f"[rosstat/{name}] -- HTML fallback")
    resp = await _http_get(indicator_url)
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


async def _fetch_indicator(url: str, name: str, out_dir: str) -> int:
    print(f"\n[rosstat/{name}] === START ===")
    print(f"[rosstat/{name}] source: {url}")
    print(f"[rosstat/{name}] target dir: {out_dir}")
    df = pd.DataFrame()
    try:
        print(f"[rosstat/{name}] step 1/2: SDMX")
        resp = await _http_get(url)
        df = _parse_sdmx_to_df(resp.content)
        if not df.empty:
            print(f"[rosstat/{name}] SDMX ok: {len(df)} rows, {df.shape[1]} cols")
        else:
            print(f"[rosstat/{name}] SDMX returned empty dataframe")
    except Exception as e:
        print(f"[rosstat/{name}] SDMX error: {type(e).__name__}: {e}")
    if df.empty:
        try:
            print(f"[rosstat/{name}] step 2/2: HTML fallback")
            df = await _fallback_html(url, name)
        except Exception as e:
            print(f"[rosstat/{name}] HTML fallback error: {type(e).__name__}: {e}")
    if df.empty:
        print(f"[rosstat/{name}] === FAIL: no data ===")
        return 0
    _save(df, out_dir, name)
    print(f"[rosstat/{name}] === DONE: {len(df)} rows ===\n")
    return len(df)


async def cpi() -> int:
    return await _fetch_indicator(FEDSTAT_CPI_URL, "cpi", ROSSTAT_DIRS["cpi"])


async def ipp() -> int:
    return await _fetch_indicator(FEDSTAT_IPP_URL, "ipp", ROSSTAT_DIRS["ipp"])


async def main() -> None:
    print("\n========== Rosstat (fedstat.ru) loader ==========\n")
    report = RunReport("rosstat")
    await report.run("cpi", cpi)
    await report.run("ipp", ipp)
    report.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
