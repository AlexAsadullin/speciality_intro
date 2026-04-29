import asyncio
import os
import sys
from datetime import date, datetime, timedelta

import pandas as pd
from dotenv import load_dotenv
from moexalgo import CandlePeriod, Ticker, session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import (
    MOEX_DIRS,
    MOEX_DEFAULT_FIRST_DATE,
    MOEX_DEFAULT_LAST_DATE,
    MOEX_DEFAULT_SHARES,
    MOEX_DEFAULT_INDICES,
    MOEX_DEFAULT_OFZ_INDICES,
    MOEX_DEFAULT_FUTURES,
    MOEX_DEFAULT_SHARES_PERIOD,
    MOEX_CHUNK_TARGET_ROWS,
    MOEX_ROWS_PER_CALENDAR_DAY,
    MOEX_CHUNK_DAYS_METRICS,
)
from loader.helpers import RunReport, adjust_end_date, parse_date, save_csv


def _chunk_days_for(period: "CandlePeriod") -> int:
    """Сколько КАЛЕНДАРНЫХ дней брать в чанк, чтобы получить ~MOEX_CHUNK_TARGET_ROWS строк."""
    rows_per_day = MOEX_ROWS_PER_CALENDAR_DAY[period.name]
    return max(1, int(MOEX_CHUNK_TARGET_ROWS / rows_per_day))


# .env лежит в корне проекта; load_dotenv() без пути берёт cwd, а скрипт запускается
# из loader/moex/, поэтому указываем абсолютный путь явно.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))
session.TOKEN = os.getenv("MOEX_ALGOPACK_TOKEN") or os.getenv("moex_token")
if not session.TOKEN:
    print("[WARN] MOEX_ALGOPACK_TOKEN не задан -- платные endpoint'ы (obstats/tradestats/orderstats) вернут 403")
else:
    print(f"[OK] MOEX_ALGOPACK_TOKEN loaded ({len(session.TOKEN)} chars)")


# ---------- chunked downloaders ----------

async def _fetch_chunked_metric(
    ticker: str,
    method_name: str,
    start_date: date,
    end_date: date,
    chunk_days: int,
) -> pd.DataFrame:
    print(f"[{ticker}/{method_name}] downloading {start_date}..{end_date} "
          f"(target ~{MOEX_CHUNK_TARGET_ROWS} rows/chunk -> {chunk_days} calendar days)")
    stock = Ticker(ticker)
    fetch = getattr(stock, method_name)
    all_data = pd.DataFrame()
    current_start = start_date
    end_date = adjust_end_date(end_date)
    chunk_idx = 0
    retries = 0
    while current_start < end_date:
        current_end = min(current_start + timedelta(days=chunk_days), end_date)
        chunk_idx += 1
        try:
            chunk = await asyncio.to_thread(fetch, start=current_start, end=current_end)
            retries = 0
            if chunk is not None and not chunk.empty:
                chunk["datetime"] = pd.to_datetime(
                    chunk["tradedate"].astype(str) + " " + chunk["tradetime"].astype(str),
                    format="%Y-%m-%d %H:%M:%S",
                )
                chunk = chunk.drop(columns=["tradedate", "tradetime", "systime"], errors="ignore")
                all_data = pd.concat([all_data, chunk], ignore_index=True)
                last_dt = chunk["datetime"].max()
                print(f"  chunk #{chunk_idx} {current_start}..{current_end}: +{len(chunk)} rows (total {len(all_data)})")
                if pd.notna(last_dt):
                    current_start = (last_dt + timedelta(seconds=1)).date()
                else:
                    current_start = current_end + timedelta(days=1)
            else:
                print(f"  chunk #{chunk_idx} {current_start}..{current_end}: empty")
                current_start = current_end + timedelta(days=1)
        except Exception as e:
            retries += 1
            print(f"  chunk #{chunk_idx} ERROR {current_start}..{current_end}: {e} -- retry {retries}/3")
            if "403" in str(e):
                print(f"  ABORT: 403 -- token missing/invalid or no AlgoPack subscription")
                break
            if retries >= 3:
                print(f"  ABORT chunk after 3 retries, skipping")
                current_start = current_end + timedelta(days=1)
                retries = 0
                continue
            await asyncio.sleep(10)
            continue
    if all_data.empty:
        print(f"[{ticker}/{method_name}] no data")
        return all_data
    if "ticker" in all_data.columns:
        all_data = all_data.drop(columns=["ticker"])
    all_data = all_data.drop_duplicates(subset=["datetime"], keep="last")
    all_data = all_data.sort_values("datetime").reset_index(drop=True)
    print(f"[{ticker}/{method_name}] done: {len(all_data)} rows")
    return all_data


async def _fetch_chunked_candles(
    ticker: str,
    start_date: date,
    end_date: date,
    period,
    chunk_days: int,
) -> pd.DataFrame:
    print(f"[{ticker}/candles({period.name})] downloading {start_date}..{end_date} "
          f"(target ~{MOEX_CHUNK_TARGET_ROWS} rows/chunk -> {chunk_days} calendar days)")
    stock = Ticker(ticker)
    all_data = pd.DataFrame()
    current_start = start_date
    end_date = adjust_end_date(end_date)
    chunk_idx = 0
    period_minutes = {
        CandlePeriod.ONE_MINUTE: 1,
        CandlePeriod.TEN_MINUTES: 10,
        CandlePeriod.ONE_HOUR: 60,
        CandlePeriod.ONE_DAY: 60 * 24,
        CandlePeriod.ONE_WEEK: 60 * 24 * 7,
        CandlePeriod.ONE_MONTH: 60 * 24 * 30,
    }.get(period, 1)
    retries = 0
    while current_start < end_date:
        current_end = min(current_start + timedelta(days=chunk_days), end_date)
        chunk_idx += 1
        try:
            chunk = await asyncio.to_thread(stock.candles, start=current_start, end=current_end, period=period)
            retries = 0
            if chunk is not None and not chunk.empty:
                chunk["begin"] = pd.to_datetime(chunk["begin"])
                all_data = pd.concat([all_data, chunk], ignore_index=True)
                last_begin = chunk["begin"].max()
                print(f"  chunk #{chunk_idx} {current_start}..{current_end}: +{len(chunk)} rows (total {len(all_data)})")
                if pd.notna(last_begin):
                    current_start = (last_begin + timedelta(minutes=period_minutes)).date()
                else:
                    current_start = current_end + timedelta(days=1)
            else:
                print(f"  chunk #{chunk_idx} {current_start}..{current_end}: empty")
                current_start = current_end + timedelta(days=1)
        except Exception as e:
            retries += 1
            print(f"  chunk #{chunk_idx} ERROR {current_start}..{current_end}: {e} -- retry {retries}/3")
            if "403" in str(e):
                print(f"  ABORT: 403 -- token missing/invalid or no AlgoPack subscription")
                break
            if retries >= 3:
                print(f"  ABORT chunk after 3 retries, skipping")
                current_start = current_end + timedelta(days=1)
                retries = 0
                continue
            await asyncio.sleep(10)
            continue
    if all_data.empty:
        print(f"[{ticker}/candles] no data")
        return all_data
    all_data["begin"] = pd.to_datetime(all_data["begin"])
    all_data = all_data.drop_duplicates(subset=["begin"], keep="last")
    all_data = all_data.sort_values("begin").reset_index(drop=True)
    print(f"[{ticker}/candles] done: {len(all_data)} rows")
    return all_data


# ---------- public loaders (one per moex/ category) ----------

async def shares(ticker: str, first_date: str, last_date: str, period: "CandlePeriod") -> int:
    df = await _fetch_chunked_candles(
        ticker=ticker,
        start_date=parse_date(first_date),
        end_date=parse_date(last_date),
        period=period,
        chunk_days=_chunk_days_for(period),
    )
    name = f"candles_{period.name.lower()}"
    save_csv(df, MOEX_DIRS["shares"], name, ticker, first_date, last_date)
    return len(df)


async def orderbook(ticker: str, first_date: str, last_date: str) -> int:
    df = await _fetch_chunked_metric(
        ticker=ticker,
        method_name="obstats",
        start_date=parse_date(first_date),
        end_date=parse_date(last_date),
        chunk_days=MOEX_CHUNK_DAYS_METRICS,
    )
    save_csv(df, MOEX_DIRS["orderbook"], "obstats", ticker, first_date, last_date)
    return len(df)


async def tradestats(ticker: str, first_date: str, last_date: str) -> int:
    df = await _fetch_chunked_metric(
        ticker=ticker,
        method_name="tradestats",
        start_date=parse_date(first_date),
        end_date=parse_date(last_date),
        chunk_days=MOEX_CHUNK_DAYS_METRICS,
    )
    save_csv(df, MOEX_DIRS["tradestats"], "tradestats", ticker, first_date, last_date)
    return len(df)


async def orderstats(ticker: str, first_date: str, last_date: str) -> int:
    df = await _fetch_chunked_metric(
        ticker=ticker,
        method_name="orderstats",
        start_date=parse_date(first_date),
        end_date=parse_date(last_date),
        chunk_days=MOEX_CHUNK_DAYS_METRICS,
    )
    save_csv(df, MOEX_DIRS["orderstats"], "orderstats", ticker, first_date, last_date)
    return len(df)


async def indices(ticker: str, first_date: str, last_date: str) -> int:
    df = await _fetch_chunked_candles(
        ticker=ticker,
        start_date=parse_date(first_date),
        end_date=parse_date(last_date),
        period=CandlePeriod.ONE_DAY,
        chunk_days=_chunk_days_for(CandlePeriod.ONE_DAY),
    )
    save_csv(df, MOEX_DIRS["indices"], "index_1d", ticker, first_date, last_date)
    return len(df)


async def ofz_curve(ticker: str, first_date: str, last_date: str) -> int:
    df = await _fetch_chunked_candles(
        ticker=ticker,
        start_date=parse_date(first_date),
        end_date=parse_date(last_date),
        period=CandlePeriod.ONE_DAY,
        chunk_days=_chunk_days_for(CandlePeriod.ONE_DAY),
    )
    save_csv(df, MOEX_DIRS["ofz_curve"], "ofz_1d", ticker, first_date, last_date)
    return len(df)


async def derivatives(ticker: str, first_date: str, last_date: str) -> int:
    df = await _fetch_chunked_candles(
        ticker=ticker,
        start_date=parse_date(first_date),
        end_date=parse_date(last_date),
        period=CandlePeriod.ONE_DAY,
        chunk_days=_chunk_days_for(CandlePeriod.ONE_DAY),
    )
    save_csv(df, MOEX_DIRS["derivatives"], "fut_1d", ticker, first_date, last_date)
    return len(df)


async def main() -> None:
    first_date = MOEX_DEFAULT_FIRST_DATE
    last_date = MOEX_DEFAULT_LAST_DATE

    print(f"\n========== MOEX algopack loader: {first_date} .. {last_date} ==========\n")

    report = RunReport("moex")

    for ticker in MOEX_DEFAULT_SHARES:
        print(f"\n========== shares: {ticker} ==========")
        await report.run(f"shares/{ticker}", shares, ticker, first_date, last_date, MOEX_DEFAULT_SHARES_PERIOD)
        await report.run(f"orderbook/{ticker}", orderbook, ticker, first_date, last_date)
        await report.run(f"tradestats/{ticker}", tradestats, ticker, first_date, last_date)
        await report.run(f"orderstats/{ticker}", orderstats, ticker, first_date, last_date)

    for ticker in MOEX_DEFAULT_INDICES:
        print(f"\n========== index: {ticker} ==========")
        await report.run(f"indices/{ticker}", indices, ticker, first_date, last_date)

    for ticker in MOEX_DEFAULT_OFZ_INDICES:
        print(f"\n========== ofz: {ticker} ==========")
        await report.run(f"ofz_curve/{ticker}", ofz_curve, ticker, first_date, last_date)

    for ticker in MOEX_DEFAULT_FUTURES:
        print(f"\n========== futures: {ticker} ==========")
        await report.run(f"derivatives/{ticker}", derivatives, ticker, first_date, last_date)

    report.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
