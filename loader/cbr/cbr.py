import asyncio
import os
import sys

import cbrapi as cbr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import (
    CBR_DIRS,
    CBR_DEFAULT_FIRST_DATE,
    CBR_DEFAULT_LAST_DATE,
    CBR_CURRENCY_TICKERS,
)
from loader.helpers import RunReport, ensure_dir


async def key_rate(first_date: str, last_date: str) -> int:
    def _run() -> int:
        series = cbr.get_key_rate(first_date=first_date, last_date=last_date, period="D")
        ensure_dir(CBR_DIRS["key_rate"])
        series.to_csv(os.path.join(CBR_DIRS["key_rate"], f"key_rate_{first_date}_{last_date}.csv"), header=True)
        return len(series)
    return await asyncio.to_thread(_run)


async def refinancing_rate(first_date: str, last_date: str) -> int:
    # С 2016 года ставка рефинансирования приравнена к ключевой ставке ЦБ РФ.
    def _run() -> int:
        series = cbr.get_key_rate(first_date=first_date, last_date=last_date, period="D")
        ensure_dir(CBR_DIRS["refinancing_rate"])
        series.to_csv(os.path.join(CBR_DIRS["refinancing_rate"], f"refinancing_rate_{first_date}_{last_date}.csv"), header=True)
        return len(series)
    return await asyncio.to_thread(_run)


async def ruonia(first_date: str, last_date: str) -> int:
    def _run() -> int:
        df = cbr.get_ruonia_index(first_date=first_date, last_date=last_date, period="D")
        ensure_dir(CBR_DIRS["ruonia"])
        df.to_csv(os.path.join(CBR_DIRS["ruonia"], f"ruonia_{first_date}_{last_date}.csv"))
        return len(df)
    return await asyncio.to_thread(_run)


async def currency_rates(first_date: str, last_date: str) -> int:
    def _run() -> int:
        out_dir = CBR_DIRS["currency_rates"]
        ensure_dir(out_dir)
        listing = cbr.get_currencies_list()
        listing.to_csv(os.path.join(out_dir, "currencies_list.csv"), index=False)
        total = 0
        for ticker in CBR_CURRENCY_TICKERS:
            series = cbr.get_time_series(
                symbol=ticker,
                first_date=first_date,
                last_date=last_date,
                period="D",
            )
            series.to_csv(os.path.join(out_dir, f"{ticker}_{first_date}_{last_date}.csv"), header=True)
            total += len(series)
        return total
    return await asyncio.to_thread(_run)


async def reserves(first_date: str, last_date: str) -> int:
    def _run() -> int:
        df = cbr.get_mrrf(first_date=first_date, last_date=last_date, period="M")
        ensure_dir(CBR_DIRS["reserves"])
        df.to_csv(os.path.join(CBR_DIRS["reserves"], f"reserves_{first_date}_{last_date}.csv"))
        return len(df)
    return await asyncio.to_thread(_run)


async def metals_prices(first_date: str, last_date: str) -> int:
    def _run() -> int:
        df = cbr.get_metals_prices(first_date=first_date, last_date=last_date, period="D")
        ensure_dir(CBR_DIRS["metals_prices"])
        df.to_csv(os.path.join(CBR_DIRS["metals_prices"], f"metals_prices_{first_date}_{last_date}.csv"))
        return len(df)
    return await asyncio.to_thread(_run)


async def ibor(first_date: str, last_date: str) -> int:
    def _run() -> int:
        df = cbr.get_ibor(first_date=first_date, last_date=last_date, period="M")
        ensure_dir(CBR_DIRS["ibor"])
        df.to_csv(os.path.join(CBR_DIRS["ibor"], f"ibor_{first_date}_{last_date}.csv"))
        return len(df)
    return await asyncio.to_thread(_run)


async def roisfix(first_date: str, last_date: str) -> int:
    def _run() -> int:
        df = cbr.get_roisfix(first_date=first_date, last_date=last_date, period="D")
        ensure_dir(CBR_DIRS["roisfix"])
        df.to_csv(os.path.join(CBR_DIRS["roisfix"], f"roisfix_{first_date}_{last_date}.csv"))
        return len(df)
    return await asyncio.to_thread(_run)


async def main() -> None:
    first_date = CBR_DEFAULT_FIRST_DATE
    last_date = CBR_DEFAULT_LAST_DATE

    report = RunReport("cbr")
    await report.run("key_rate", key_rate, first_date, last_date)
    await report.run("refinancing_rate", refinancing_rate, first_date, last_date)
    await report.run("ruonia", ruonia, first_date, last_date)
    await report.run("currency_rates", currency_rates, first_date, last_date)
    await report.run("reserves", reserves, first_date, last_date)
    await report.run("metals_prices", metals_prices, first_date, last_date)
    await report.run("ibor", ibor, first_date, last_date)
    await report.run("roisfix", roisfix, first_date, last_date)
    report.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
