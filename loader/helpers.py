import inspect
import os
from datetime import date, datetime, timedelta

import pandas as pd


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def is_weekday(d: date) -> bool:
    return d.weekday() < 5


def adjust_end_date(end_date: date) -> date:
    while not is_weekday(end_date):
        end_date -= timedelta(days=1)
    return end_date


def save_csv(df: pd.DataFrame, out_dir: str, name: str, ticker: str, first_date: str, last_date: str) -> str:
    ensure_dir(out_dir)
    out_path = os.path.join(out_dir, f"{name}_{ticker}_{first_date}_{last_date}.csv")
    df.to_csv(out_path, index=False)
    print(f"  -> saved {len(df)} rows to {out_path}")
    return out_path


class RunReport:
    """Collect per-task results for end-of-run summary.

    Каждый загрузчик вызывает self.run(label, callable). Любое исключение или
    возврат 0 строк трактуется как ошибка. В конце print_summary() печатает
    компактное резюме: что прошло, что упало и с какой ошибкой.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.successes: list[tuple[str, int]] = []
        self.errors: list[tuple[str, str]] = []

    async def run(self, label: str, fn, *args, **kwargs) -> int:
        try:
            if inspect.iscoroutinefunction(fn):
                rows = await fn(*args, **kwargs)
            else:
                rows = fn(*args, **kwargs)
            if not rows:
                self.errors.append((label, "no data (см. лог выше)"))
                return 0
            self.successes.append((label, rows))
            return rows
        except Exception as e:
            self.errors.append((label, f"{type(e).__name__}: {e}"))
            print(f"[{self.name}/{label}] uncaught error: {type(e).__name__}: {e}")
            return 0

    def print_summary(self) -> None:
        total = len(self.successes) + len(self.errors)
        ok_rows = sum(rows for _, rows in self.successes)
        print(f"\n========== {self.name} summary ==========")
        for label, rows in self.successes:
            print(f"  OK    {label:<20s} {rows} rows")
        for label, err in self.errors:
            print(f"  FAIL  {label:<20s} {err}")
        print(f"  ----")
        print(f"  total: {total}, ok: {len(self.successes)} ({ok_rows} rows), failed: {len(self.errors)}")
        print(f"========== end {self.name} ==========\n")
