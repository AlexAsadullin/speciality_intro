import os
# must be in the project root

# project
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_ROOT = os.getenv("DATA_ROOT", os.path.join(PROJECT_ROOT, "data"))

# cbr
CBR_ROOT = os.path.join(DATA_ROOT, "cbr")
CBR_DIRS = {
    "key_rate": os.path.join(CBR_ROOT, "key_rate"),
    "refinancing_rate": os.path.join(CBR_ROOT, "refinancing_rate"),
    "ruonia": os.path.join(CBR_ROOT, "ruonia"),
    "currency_rates": os.path.join(CBR_ROOT, "currency_rates"),
    "reserves": os.path.join(CBR_ROOT, "reserves"),
    "metals_prices": os.path.join(CBR_ROOT, "metals_prices"),
    "ibor": os.path.join(CBR_ROOT, "ibor"),
    "roisfix": os.path.join(CBR_ROOT, "roisfix"),
}
CBR_DEFAULT_FIRST_DATE = "2020-01-01"
CBR_DEFAULT_LAST_DATE = "2026-04-26"
CBR_CURRENCY_TICKERS = ["USD", "EUR", "CNY"]

# moex
MOEX_ROOT = os.path.join(DATA_ROOT, "moex")
MOEX_DIRS = {
    "shares": os.path.join(MOEX_ROOT, "shares"),
    "orderbook": os.path.join(MOEX_ROOT, "orderbook"),
    "tradestats": os.path.join(MOEX_ROOT, "tradestats"),
    "orderstats": os.path.join(MOEX_ROOT, "orderstats"),
    "indices": os.path.join(MOEX_ROOT, "indices"),
    "ofz_curve": os.path.join(MOEX_ROOT, "ofz_curve"),
    "derivatives": os.path.join(MOEX_ROOT, "derivatives"),
}

MOEX_DEFAULT_FIRST_DATE = "2025-01-01"
MOEX_DEFAULT_LAST_DATE = "2026-04-26"

MOEX_DEFAULT_SHARES = ["SBER", "GAZP", "LKOH"]
MOEX_DEFAULT_INDICES = ["IMOEX", "RTSI", "MOEXBC", "MOEXOG", "MOEXFN"]
MOEX_DEFAULT_OFZ_INDICES = ["RGBI", "RGBITR"]
MOEX_DEFAULT_FUTURES = ["SiH6", "RIH6", "GZH6", "BRH6"]

# Целевой размер чанка -- в СТРОКАХ (свечах), не в днях.
# MOEX ISS отдаёт пакетами; ~8000 строк на запрос -- безопасный верхний предел.
MOEX_CHUNK_TARGET_ROWS = 8000

# Сколько свечей данного таймфрейма приходится на один КАЛЕНДАРНЫЙ день.
# Торговый день MOEX ~15 ч × 60 = 900 минутных свечей, ~5 торг. дней / 7 календ.
MOEX_ROWS_PER_CALENDAR_DAY = {
    "ONE_MINUTE":  900 * 5 / 7,   # ~643
    "TEN_MINUTES":  90 * 5 / 7,   # ~64
    "ONE_HOUR":     15 * 5 / 7,   # ~10.7
    "ONE_DAY":           5 / 7,   # ~0.71
    "ONE_WEEK":          1 / 7,   # ~0.143
    "ONE_MONTH":         1 / 30,  # ~0.033
}

# Метрики (obstats/tradestats/orderstats) -- секундные тики, агрегированные по 5-мин барам.
# Эмпирически 34 календ. дня = около 8000 строк на ликвидной бумаге.
MOEX_CHUNK_DAYS_METRICS = 34
MOEX_DEFAULT_SHARES_PERIOD = "ONE_DAY"

# rosstat (через fedstat.ru / EMISS, формат SDMX-ML v1.0)
ROSSTAT_ROOT = os.path.join(DATA_ROOT, "rosstat")
ROSSTAT_DIRS = {
    "cpi": os.path.join(ROSSTAT_ROOT, "cpi"),
    "ipp": os.path.join(ROSSTAT_ROOT, "ipp"),
}
FEDSTAT_CPI_URL = "https://fedstat.ru/indicator/data.do?id=31074&format=sdmx"
FEDSTAT_IPP_URL = "https://fedstat.ru/indicator/data.do?id=40557&format=sdmx"
FEDSTAT_SDMX_NS = {
    "msg": "http://www.SDMX.org/resources/SDMXML/schemas/v1_0/message",
    "gen": "http://www.SDMX.org/resources/SDMXML/schemas/v1_0/generic",
}
ROSSTAT_HTTP_TIMEOUT = 60
ROSSTAT_USER_AGENT = "Mozilla/5.0 (compatible; moex-tech-test-poligon/1.0)"

# minfin (OpenData portal + HTML fallback)
MINFIN_ROOT = os.path.join(DATA_ROOT, "minfin")
MINFIN_DIRS = {
    "budget": os.path.join(MINFIN_ROOT, "budget"),
    "fnb": os.path.join(MINFIN_ROOT, "fnb"),
    "ofz_auctions": os.path.join(MINFIN_ROOT, "ofz_auctions"),
    "state_support": os.path.join(MINFIN_ROOT, "state_support"),
}
MINFIN_OPENDATA_URL = "https://minfin.gov.ru/opendata"
MINFIN_DATASET_BUDGET = "7710168360-fedbud_month"
MINFIN_DATASET_FNB = "7710168360-NationalWealthFund"
# У аукционов ОФЗ публичного OpenData-датасета нет (id 7710168360-OFZ возвращает 404).
# Оставляем None, чтобы пропустить OpenData-шаг и сразу идти на HTML.
MINFIN_DATASET_OFZ_AUCTIONS = None
MINFIN_BUDGET_HTML_URL = "https://minfin.gov.ru/ru/statistics/fedbud/execute/"
MINFIN_FNB_HTML_URL = "https://minfin.gov.ru/ru/perfomance/nationalwealthfund/"
# Раздел публичного долга / внутренних заимствований (родительская страница, без /auctions/ -- она 404).
MINFIN_OFZ_AUCTIONS_HTML_URL = "https://minfin.gov.ru/ru/perfomance/public_debt/internal/operations/ofz/"
# приоритеты господдержки -- структурированных данных нет, только HTML-скрейп бюджетного раздела.
MINFIN_STATE_SUPPORT_HTML_URL = "https://minfin.gov.ru/ru/perfomance/budget/"
# ссылки на пасспортной странице вида:
#   .../opendata/{id}/data-YYYYMMDDThhmm-structure-YYYYMMDDThhmm.csv
MINFIN_DATA_LINK_REGEX = (
    r'href="(https?://minfin\.gov\.ru/opendata/[^"]*?data-(\d{8}T\d{4})-structure-\d{8}T\d{4}\.csv)"'
)
MINFIN_HTTP_TIMEOUT = 60
MINFIN_USER_AGENT = "Mozilla/5.0 (compatible; moex-tech-test-poligon/1.0)"

# --- minfin doc-cards scraper (cloudscraper + BeautifulSoup) ---
# minfin.gov.ru блокирует plain requests с DC-IP (403/404), нужен cloudscraper.
# Доп. трюк: скобки [] в TAG_ID_4[] нельзя кодировать как %5B%5D -- сервер их режет.
_MINFIN_BASE = "https://minfin.gov.ru"
MINFIN_SCRAPE_DELAY_S = 1.2
MINFIN_SCRAPE_TIMEOUT_S = 20
MINFIN_SCRAPE_MAX_PAGES = 3

MINFIN_OFZ_SECTIONS = [
    (f"{_MINFIN_BASE}/ru/perfomance/public_debt/internal/operations/ofz/",                            "auction"),
    (f"{_MINFIN_BASE}/ru/perfomance/public_debt/internal/operations/ofz/auction/",                    "auction"),
    (f"{_MINFIN_BASE}/ru/document?TAG_ID_4[]=76&TAG_ID_4[]=1349&TAG_ID_4[]=1360",                     "auction"),
    (f"{_MINFIN_BASE}/ru/perfomance/public_debt/internal/operations/ofz/distribution_second_market/", "secondary_market"),
    (f"{_MINFIN_BASE}/ru/document?TAG_ID_4[]=76&TAG_ID_4[]=1192&TAG_ID_4[]=1360",                     "secondary_market"),
]

MINFIN_BUDGET_SECTIONS = [
    ("budget_main",        f"{_MINFIN_BASE}/ru/perfomance/budget/"),
    ("budget_policy",      f"{_MINFIN_BASE}/ru/perfomance/budget/policy/"),
    ("budget_main_dirs",   f"{_MINFIN_BASE}/ru/perfomance/budget/policy/osnov/"),
    ("budget_tax_expenses",f"{_MINFIN_BASE}/ru/perfomance/budget/policy/raskhod/"),
    ("budget_drafting",    f"{_MINFIN_BASE}/ru/perfomance/budget/process/sostavlenie/"),
    ("budget_approval",    f"{_MINFIN_BASE}/ru/perfomance/budget/process/utverzhdenie/"),
    ("budget_execution",   f"{_MINFIN_BASE}/ru/perfomance/budget/process/ispolnenie/"),
    ("budget_report",      f"{_MINFIN_BASE}/ru/perfomance/budget/process/otchet/"),
    ("budget_control",     f"{_MINFIN_BASE}/ru/perfomance/budget/process/kontrol/"),
    ("gov_finance_stats",  f"{_MINFIN_BASE}/ru/perfomance/budget/gosfin/"),
    ("accounting",         f"{_MINFIN_BASE}/ru/perfomance/budget/gosfin/bu_gs/"),
    ("budget_classifier",  f"{_MINFIN_BASE}/ru/document?TAG_ID_4[]=80"),
]
