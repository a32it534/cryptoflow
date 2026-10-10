import os
import math
import datetime

import ccxt
import webview


SUPPORTED_EXCHANGES = {
    "bingx": "BingX",
    "lbank": "LBank",
    "coinex": "CoinEx",
    "mexc": "MEXC",
    "bitget": "Bitget",
}


MAX_CANDLES = 1000


class DataFetchError(Exception):
    pass


def create_exchange_instance(exchange_id):
    exchange_id = str(exchange_id or "").strip().lower()
    if exchange_id not in SUPPORTED_EXCHANGES:
        raise DataFetchError(f"صرافی پشتیبانی‌نشده: {exchange_id}")
    exchange_class = getattr(ccxt, exchange_id)
    return exchange_class({"enableRateLimit": True, "timeout": 20000})


def smart_round(value, significant=8):
    if value is None:
        return None
    if value == 0:
        return 0.0
    return float(f"{value:.{significant}g}")


def calculate_sma(data, period=20):
    if period <= 0:
        raise ValueError("Period باید بزرگ‌تر از صفر باشد.")

    sma = []

    for i in range(len(data)):
        if i < period - 1:
            sma.append(None)
        else:
            window = data[i - period + 1:i + 1]
            average = sum(window) / period
            sma.append(round(average, 12))

    return sma


def calculate_ema(data, period=12):
    if period <= 0:
        raise ValueError("Period باید بزرگ‌تر از صفر باشد.")

    ema = []
    multiplier = 2 / (period + 1)

    for i in range(len(data)):
        if i < period - 1:
            ema.append(None)

        elif i == period - 1:
            initial_average = sum(data[:period]) / period
            ema.append(round(initial_average, 12))

        else:
            previous_ema = ema[-1]
            current_value = (data[i] - previous_ema) * multiplier + previous_ema
            ema.append(round(current_value, 12))

    return ema


def calculate_rsi(closes, period=14):
    if period <= 0:
        raise ValueError("Period باید بزرگ‌تر از صفر باشد.")

    if len(closes) < period + 1:
        return [None] * len(closes)

    deltas = [
        closes[i] - closes[i - 1]
        for i in range(1, len(closes))
    ]

    gains = [
        delta if delta > 0 else 0
        for delta in deltas
    ]

    losses = [
        -delta if delta < 0 else 0
        for delta in deltas
    ]

    average_gain = sum(gains[:period]) / period
    average_loss = sum(losses[:period]) / period

    rsi = [None] * period

    if average_loss == 0:
        initial_rsi = 100.0 if average_gain > 0 else 50.0
    else:
        relative_strength = average_gain / average_loss
        initial_rsi = 100 - (100 / (1 + relative_strength))

    rsi.append(round(initial_rsi, 2))

    for i in range(period, len(deltas)):
        average_gain = (
            (average_gain * (period - 1)) + gains[i]
        ) / period

        average_loss = (
            (average_loss * (period - 1)) + losses[i]
        ) / period

        if average_loss == 0:
            current_rsi = 100.0 if average_gain > 0 else 50.0
        else:
            relative_strength = average_gain / average_loss
            current_rsi = 100 - (100 / (1 + relative_strength))

        rsi.append(round(current_rsi, 2))

    return rsi


def calculate_bollinger_bands(closes, period=20, std_dev=2):
    middle_band = calculate_sma(closes, period)

    upper_band = []
    lower_band = []

    for i in range(len(closes)):
        if middle_band[i] is None:
            upper_band.append(None)
            lower_band.append(None)
            continue

        window = closes[i - period + 1:i + 1]

        variance = sum(
            (value - middle_band[i]) ** 2
            for value in window
        ) / period

        standard_deviation = math.sqrt(variance)

        upper_value = middle_band[i] + (
            standard_deviation * std_dev
        )

        lower_value = middle_band[i] - (
            standard_deviation * std_dev
        )

        upper_band.append(round(upper_value, 12))
        lower_band.append(round(lower_value, 12))

    return upper_band, middle_band, lower_band


def calculate_macd(closes, fast=12, slow=26, signal=9):
    fast_ema = calculate_ema(closes, fast)
    slow_ema = calculate_ema(closes, slow)

    macd_line = []

    for i in range(len(closes)):
        if fast_ema[i] is None or slow_ema[i] is None:
            macd_line.append(None)
        else:
            macd_value = fast_ema[i] - slow_ema[i]
            macd_line.append(round(macd_value, 12))

    valid_macd_values = [
        value for value in macd_line
        if value is not None
    ]

    valid_signal_values = calculate_ema(
        valid_macd_values,
        signal
    )

    padding_length = len(closes) - len(valid_signal_values)
    signal_line = (
        [None] * padding_length
    ) + valid_signal_values

    histogram = []

    for i in range(len(closes)):
        if (
            macd_line[i] is None
            or signal_line[i] is None
        ):
            histogram.append(None)
        else:
            histogram_value = (
                macd_line[i] - signal_line[i]
            )
            histogram.append(round(histogram_value, 12))

    return macd_line, signal_line, histogram


def calculate_ichimoku(highs, lows, closes):
    tenkan = []
    kijun = []

    for i in range(len(closes)):
        if i < 8:
            tenkan.append(None)
        else:
            highest_high = max(highs[i - 8:i + 1])
            lowest_low = min(lows[i - 8:i + 1])

            tenkan_value = (
                highest_high + lowest_low
            ) / 2

            tenkan.append(round(tenkan_value, 12))

        if i < 25:
            kijun.append(None)
        else:
            highest_high = max(highs[i - 25:i + 1])
            lowest_low = min(lows[i - 25:i + 1])

            kijun_value = (
                highest_high + lowest_low
            ) / 2

            kijun.append(round(kijun_value, 12))

    return tenkan, kijun


def get_volume_status(volume_ratio):
    if volume_ratio is None:
        return "N/A"

    if volume_ratio >= 2:
        return "VERY_HIGH"

    if volume_ratio >= 1.5:
        return "HIGH"

    if volume_ratio <= 0.5:
        return "LOW"

    return "NORMAL"


def normalize_symbol(symbol):
    sym = str(symbol or "").strip().upper().replace(" ", "")
    if not sym:
        raise DataFetchError("نماد رمزارز را وارد کنید.")
    if "/" not in sym:
        sym += "/USDT"
    return sym


def fetch_market_data(symbol, timeframe, limit=50, exchange_id="bingx"):
    exchange_id = str(exchange_id or "").strip().lower()
    exchange_name = SUPPORTED_EXCHANGES.get(exchange_id, exchange_id)

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        raise DataFetchError("تعداد کندل باید یک عدد صحیح باشد.")
    if limit < 1 or limit > MAX_CANDLES:
        raise DataFetchError(f"تعداد کندل باید بین ۱ تا {MAX_CANDLES} باشد.")

    symbol = normalize_symbol(symbol)
    exchange = create_exchange_instance(exchange_id)

    try:
        supported_tfs = list((exchange.timeframes or {}).keys())
        if supported_tfs and timeframe not in supported_tfs:
            raise DataFetchError(
                f"{exchange_name} تایم‌فریم {timeframe} را پشتیبانی نمی‌کند. "
                f"تایم‌فریم‌های مجاز: {', '.join(supported_tfs)}"
            )

        exchange.load_markets()
        if symbol not in exchange.markets:
            raise DataFetchError(f"نماد {symbol} در {exchange_name} پیدا نشد.")

        fetch_limit = min(limit + 60, MAX_CANDLES + 60)
        raw_ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=fetch_limit)

    except DataFetchError:
        raise
    except ccxt.NetworkError as error:
        raise DataFetchError(f"خطای شبکه هنگام اتصال به {exchange_name}: {error}")
    except ccxt.ExchangeError as error:
        raise DataFetchError(f"خطای صرافی {exchange_name}: {error}")
    except Exception as error:
        raise DataFetchError(f"خطا در دریافت اطلاعات از {exchange_name}: {error}")

    if not raw_ohlcv:
        raise DataFetchError(f"برای {symbol} در {exchange_name} داده‌ای دریافت نشد.")

    by_time = {}
    for candle in raw_ohlcv:
        if not candle or len(candle) < 6:
            continue
        try:
            ts = int(candle[0])
            by_time[ts] = [
                ts,
                float(candle[1]), float(candle[2]),
                float(candle[3]), float(candle[4]),
                float(candle[5]) if candle[5] is not None else 0.0,
            ]
        except (TypeError, ValueError):
            continue
    ohlcv = [by_time[ts] for ts in sorted(by_time)]

    if not ohlcv:
        raise DataFetchError(f"داده معتبری برای {symbol} دریافت نشد.")

    highs = [c[2] for c in ohlcv]
    lows = [c[3] for c in ohlcv]
    closes = [c[4] for c in ohlcv]
    volumes = [c[5] for c in ohlcv]

    rsi = calculate_rsi(closes, 14)
    bb_upper, bb_mid, bb_lower = calculate_bollinger_bands(closes, 20, 2)
    macd, macd_signal, macd_hist = calculate_macd(closes, 12, 26, 9)
    tenkan, kijun = calculate_ichimoku(highs, lows, closes)
    volume_sma = calculate_sma(volumes, 20)

    start = max(0, len(ohlcv) - limit)
    rows = []
    for i in range(start, len(ohlcv)):
        ts, o, h, l, c, v = ohlcv[i]
        avg_vol = volume_sma[i]
        ratio = (v / avg_vol) if (avg_vol and avg_vol > 0) else None

        rows.append([
            datetime.datetime.fromtimestamp(ts / 1000, tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M"),
            o, h, l, c,
            smart_round(v, 10),
            smart_round(avg_vol, 10),
            round(ratio, 2) if ratio is not None else None,
            get_volume_status(ratio),
            rsi[i],
            smart_round(bb_upper[i]), smart_round(bb_mid[i]), smart_round(bb_lower[i]),
            smart_round(macd[i]), smart_round(macd_signal[i]), smart_round(macd_hist[i]),
            smart_round(tenkan[i]), smart_round(kijun[i]),
        ])

    return symbol, rows


HTML_CODE = r"""
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>نبض بازار کریپتو</title>
<script>
(function () {
    var t = 'dark';
    try { t = localStorage.getItem('theme') || (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'); } catch (e) {}
    document.documentElement.dataset.theme = t;
})();
</script>
<style>
:root {
    --bg: #0f1319; --panel: #161b23; --panel-2: #1d232d; --line: #272f3b;
    --text: #e8ecf2; --muted: #8e99aa; --faint: #647084;
    --accent: #e3a72f; --accent-ink: #1a1405; --focus: #6aa8ff;
    --up: #34b88b; --up-bg: rgba(52, 184, 139, .15);
    --down: #ef6a5a; --down-bg: rgba(239, 106, 90, .15);
    --warn: #e3a72f; --warn-bg: rgba(227, 167, 47, .15);
    --radius: 10px;
    color-scheme: dark;
}
:root[data-theme="light"] {
    --bg: #f3f4f6; --panel: #ffffff; --panel-2: #f6f7f9; --line: #e0e4ea;
    --text: #161a21; --muted: #5b6676; --faint: #8a94a3;
    --accent: #dba022; --focus: #1d6fe0;
    --up: #0f8a60; --up-bg: rgba(15, 138, 96, .12);
    --down: #c8402f; --down-bg: rgba(200, 64, 47, .12);
    --warn: #9a6a00; --warn-bg: rgba(219, 160, 34, .18);
    color-scheme: light;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    background: var(--bg); color: var(--text);
    font: 14px/1.6 "Vazirmatn", "Segoe UI", Tahoma, "Noto Sans Arabic", sans-serif;
    -webkit-font-smoothing: antialiased;
}
button, input, select { font: inherit; color: inherit; }
:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
.num { direction: ltr; unicode-bidi: isolate; font-variant-numeric: tabular-nums; }

.app { display: grid; grid-template-columns: 288px minmax(0, 1fr); min-height: 100vh; }

.controls {
    position: sticky; top: 0; height: 100vh; overflow-y: auto;
    display: flex; flex-direction: column; gap: 16px; padding: 20px;
    background: var(--panel); border-inline-end: 1px solid var(--line);
}
.brand { display: flex; align-items: center; gap: 12px; padding-bottom: 16px; border-bottom: 1px solid var(--line); }
.brand-mark { width: 36px; height: 36px; border-radius: 9px; background: var(--accent); color: var(--accent-ink); display: grid; place-items: center; flex-shrink: 0; }
.brand-name { font-size: 1.05rem; font-weight: 700; line-height: 1.3; }
.brand-note { font-size: .78rem; color: var(--muted); }

.field { display: flex; flex-direction: column; gap: 6px; }
.field label { font-size: .8rem; font-weight: 600; color: var(--muted); }
.field select, .field input {
    width: 100%; height: 40px; padding: 0 12px;
    background: var(--panel-2); border: 1px solid var(--line); border-radius: 8px;
    transition: border-color .15s;
}
.field input[type="text"] { direction: ltr; text-align: left; }
.field select:hover, .field input:hover { border-color: var(--faint); }
.field select:focus, .field input:focus { border-color: var(--focus); outline: none; box-shadow: 0 0 0 3px color-mix(in srgb, var(--focus) 25%, transparent); }
.hint { font-size: .74rem; color: var(--faint); }

.actions { display: grid; gap: 8px; }
.btn {
    display: inline-flex; align-items: center; justify-content: center; gap: 8px;
    height: 42px; padding: 0 16px; border-radius: 8px; cursor: pointer; font-weight: 600;
    border: 1px solid var(--line); background: transparent; transition: background .15s, border-color .15s;
}
.btn:hover:not(:disabled) { background: var(--panel-2); border-color: var(--faint); }
.btn:disabled { opacity: .5; cursor: not-allowed; }
.btn-primary { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); font-weight: 700; }
.btn-primary:hover:not(:disabled) { background: var(--accent); border-color: var(--accent); filter: brightness(1.08); }
.btn-sm { height: 32px; padding: 0 12px; font-size: .8rem; }
.theme-btn { margin-top: auto; }

main { display: flex; flex-direction: column; gap: 20px; padding: 24px 28px; min-width: 0; }

.summary { display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 12px 32px; padding-bottom: 20px; border-bottom: 1px solid var(--line); }
.summary h1 { font-size: 1.1rem; font-weight: 700; }
.meta { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 12px; margin-top: 2px; font-size: .8rem; color: var(--muted); }
.price-row { display: flex; align-items: baseline; flex-wrap: wrap; gap: 8px 14px; margin-top: 8px; }
.price { font-size: clamp(1.9rem, 4.2vw, 2.9rem); font-weight: 700; line-height: 1.1; letter-spacing: -.02em; }
.range { font-size: .8rem; color: var(--muted); }
.range .num { color: var(--text); }

.status { display: inline-flex; align-items: center; gap: 8px; height: 28px; padding: 0 12px; border: 1px solid var(--line); border-radius: 14px; font-size: .8rem; color: var(--muted); }
.status::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
.status.busy { color: var(--warn); }
.status.ok { color: var(--up); }
.status.err { color: var(--down); }

.chip { display: inline-block; padding: 1px 8px; border-radius: 6px; font-size: .75rem; font-weight: 600; background: var(--panel-2); color: var(--muted); white-space: nowrap; }
.chip.up { background: var(--up-bg); color: var(--up); }
.chip.down { background: var(--down-bg); color: var(--down); }
.chip.warn { background: var(--warn-bg); color: var(--warn); }

.metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
.metric { background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); padding: 14px 16px; display: flex; flex-direction: column; gap: 10px; }
.metric-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.metric-title { font-size: .82rem; font-weight: 600; color: var(--muted); }
.metric-value { font-size: 1.5rem; font-weight: 700; line-height: 1.2; }
.rows { display: grid; gap: 6px; }
.rows > div { display: flex; justify-content: space-between; gap: 12px; font-size: .84rem; }
.rows dt { color: var(--muted); }
.rows dd { font-weight: 600; }
.gauge { position: relative; height: 6px; border-radius: 3px; background: var(--panel-2); }
.gauge-fill { position: absolute; inset-block: 0; inset-inline-start: 0; width: 50%; border-radius: 3px; background: var(--muted); transition: width .3s; }
.gauge-fill.up { background: var(--up); } .gauge-fill.down { background: var(--down); }
.gauge i { position: absolute; top: -3px; bottom: -3px; width: 1px; background: var(--faint); }
.gauge i:nth-of-type(1) { inset-inline-start: 30%; } .gauge i:nth-of-type(2) { inset-inline-start: 70%; }
.pos { color: var(--up); } .neg { color: var(--down); }

.table-panel { background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); display: flex; flex-direction: column; min-height: 320px; min-width: 0; }
.toolbar { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px; padding: 12px 16px; border-bottom: 1px solid var(--line); }
.toolbar-title { display: flex; align-items: center; gap: 10px; font-weight: 700; }
.toolbar-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; }
.switch { display: inline-flex; align-items: center; gap: 8px; font-size: .8rem; color: var(--muted); cursor: pointer; }
.switch input { width: 16px; height: 16px; accent-color: var(--accent); }

.table-scroll { overflow: auto; max-height: 56vh; flex: 1; }
table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: .84rem; white-space: nowrap; }
th, td { padding: 9px 14px; text-align: right; border-bottom: 1px solid var(--line); }
th { position: sticky; top: 0; z-index: 2; background: var(--panel-2); color: var(--muted); font-weight: 600; font-size: .78rem; }
td { font-variant-numeric: tabular-nums; }
tbody tr:hover td { background: var(--panel-2); }
tbody tr:last-child td { border-bottom: 0; }
th:first-child, td:first-child { position: sticky; inset-inline-start: 0; background: var(--panel); z-index: 1; }
th:first-child { background: var(--panel-2); z-index: 3; }
tbody tr:hover td:first-child { background: var(--panel-2); }
table:not(.show-all) .extra { display: none; }
td.t-up { color: var(--up); font-weight: 600; } td.t-down { color: var(--down); font-weight: 600; }
.empty { text-align: center !important; color: var(--faint); padding: 56px 16px; white-space: normal; }
.table-panel[aria-busy="true"] tbody { opacity: .45; }

.toast {
    position: fixed; inset-block-end: 20px; inset-inline-start: 20px; max-width: min(420px, calc(100vw - 40px));
    display: flex; align-items: center; gap: 10px; padding: 12px 16px;
    background: var(--panel); border: 1px solid var(--line); border-inline-start: 3px solid var(--muted);
    border-radius: 8px; box-shadow: 0 8px 24px rgba(0, 0, 0, .3); font-size: .86rem; word-break: break-word;
    opacity: 0; transform: translateY(12px); pointer-events: none; transition: opacity .2s, transform .2s; z-index: 50;
}
.toast.show { opacity: 1; transform: none; }
.toast.success { border-inline-start-color: var(--up); } .toast.error { border-inline-start-color: var(--down); }

.spin { animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 900px) {
    .app { grid-template-columns: 1fr; }
    .controls { position: static; height: auto; display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); align-items: end; border-inline-end: 0; border-bottom: 1px solid var(--line); }
    .brand, .actions, .theme-btn { grid-column: 1 / -1; }
    .actions { grid-template-columns: 1fr 1fr; }
    .theme-btn { margin-top: 0; }
    .table-scroll { max-height: none; }
}
@media (max-width: 560px) {
    main { padding: 16px 14px; }
    .controls { padding: 16px 14px; }
    .actions { grid-template-columns: 1fr; }
    .metrics { grid-template-columns: 1fr; }
    th, td { padding: 8px 10px; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
</style>
</head>
<body>
<div class="app">
    <aside class="controls" aria-label="تنظیمات دریافت داده">
        <div class="brand">
            <div class="brand-mark" aria-hidden="true">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>
            </div>
            <div>
               <div class="brand-name">نبض بازار کریپتو</div>
                <div class="brand-note">دریافت مستقیم داده از صرافی‌ها</div>
            </div>
        </div>

        <div class="field">
            <label for="exchange">صرافی</label>
            <select id="exchange">
                <option value="bingx" selected>BingX</option>
                <option value="lbank">LBank</option>
                <option value="coinex">CoinEx</option>
                <option value="mexc">MEXC</option>
                <option value="bitget">Bitget</option>
            </select>
        </div>

        <div class="field">
            <label for="symbol">نماد</label>
            <input type="text" id="symbol" value="BTC/USDT" placeholder="BTC/USDT" autocomplete="off" spellcheck="false">
            <span class="hint">مثلاً BTC یا ETH/USDT</span>
        </div>

        <div class="field">
            <label for="timeframe">تایم‌فریم</label>
            <select id="timeframe">
                <option value="1m">۱ دقیقه</option>
                <option value="5m">۵ دقیقه</option>
                <option value="15m">۱۵ دقیقه</option>
                <option value="30m">۳۰ دقیقه</option>
                <option value="1h">۱ ساعت</option>
                <option value="4h">۴ ساعت</option>
                <option value="1d" selected>روزانه</option>
                <option value="1w">هفتگی</option>
            </select>
        </div>

        <div class="field">
            <label for="limit">تعداد کندل</label>
            <input type="number" id="limit" value="100" min="100" max="1000" inputmode="numeric">
            <span class="hint">برای درستی داده و تحلیل داده ها از کندل های زیاد استفاده کنید حداقل 100 و حداکثر 1000 استفاده کنید </span>
        </div>
        <div class="actions">
            <button id="fetchBtn" class="btn btn-primary" type="button">دریافت داده</button>
            <button id="exportBtn" class="btn" type="button" disabled>ذخیره در اکسل</button>
        </div>

        <button id="themeBtn" class="btn btn-sm theme-btn" type="button">تغییر تم</button>
    </aside>

    <main>
        <header class="summary">
            <div>
                <h1 id="displayTitle">داده‌های بازار</h1>
                <div class="meta"><span id="lastUpdate">هنوز داده‌ای دریافت نشده</span><span class="num" id="clockText">--:--:--</span></div>
                <div class="price-row">
                    <span class="price num" id="statClose">-</span>
                    <span class="chip num" id="badgeChange">-</span>
                </div>
            </div>
            <div style="display:grid; gap:8px; justify-items:end;">
                <div id="statusBadge" class="status" role="status"><span id="statusText">آماده</span></div>
                <div class="range">دامنه کندل آخر: <span class="num" id="statRange">-</span></div>
            </div>
        </header>

        <section class="metrics" aria-label="اندیکاتورهای آخرین کندل">
            <article class="metric">
                <div class="metric-head"><span class="metric-title">RSI (14)</span><span class="chip" id="badgeRsi">-</span></div>
                <div class="metric-value num" id="statRSI">-</div>
                <div class="gauge" aria-hidden="true"><div class="gauge-fill" id="rsiFill"></div><i></i><i></i></div>
                <div class="hint">زیر ۳۰ اشباع فروش، بالای ۷۰ اشباع خرید</div>
            </article>

            <article class="metric">
                <div class="metric-head"><span class="metric-title">باندهای بولینگر (۲۰، ۲)</span></div>
                <dl class="rows">
                    <div><dt>باند بالا</dt><dd class="num" id="bbUpper">-</dd></div>
                    <div><dt>میانه</dt><dd class="num" id="bbMid">-</dd></div>
                    <div><dt>باند پایین</dt><dd class="num" id="bbLower">-</dd></div>
                </dl>
            </article>

            <article class="metric">
                <div class="metric-head"><span class="metric-title">MACD (12، 26، 9)</span><span class="chip" id="badgeMacd">-</span></div>
                <dl class="rows">
                    <div><dt>MACD</dt><dd class="num" id="macdVal">-</dd></div>
                    <div><dt>سیگنال</dt><dd class="num" id="macdSignal">-</dd></div>
                    <div><dt>هیستوگرام</dt><dd class="num" id="statHist">-</dd></div>
                </dl>
            </article>

            <article class="metric">
                <div class="metric-head"><span class="metric-title">ایچیموکو</span><span class="chip" id="badgeIchi">-</span></div>
                <dl class="rows">
                    <div><dt>تنکان‌سن (۹)</dt><dd class="num" id="statTenkan">-</dd></div>
                    <div><dt>کیجون‌سن (۲۶)</dt><dd class="num" id="statKijun">-</dd></div>
                </dl>
            </article>

            <article class="metric">
                <div class="metric-head"><span class="metric-title">حجم معاملات</span><span class="chip" id="badgeVol">-</span></div>
                <div class="metric-value num" id="statVol">-</div>
                <dl class="rows">
                    <div><dt>نسبت به میانگین ۲۰ کندل</dt><dd class="num" id="statVolRatio">-</dd></div>
                </dl>
            </article>
        </section>

        <section class="table-panel" id="tablePanel" aria-label="جدول کندل‌ها">
            <div class="toolbar">
                <div class="toolbar-title">کندل‌ها <span class="chip" id="candleCount">۰ کندل</span></div>
                <div class="toolbar-actions">
                    <label class="switch"><input type="checkbox" id="showAll"> نمایش همه اندیکاتورها</label>
                    <button class="btn btn-sm" id="copyBtn" type="button">کپی جدول</button>
                </div>
            </div>
            <div class="table-scroll">
                <table id="candleTable">
                    <thead>
                        <tr>
                            <th>تاریخ شمسی (ساعت UTC)</th><th>باز</th><th>بالا</th><th>پایین</th><th>بسته</th><th>حجم</th><th>وضعیت حجم</th><th>RSI</th>
                            <th class="extra">بولینگر بالا</th><th class="extra">بولینگر میانه</th><th class="extra">بولینگر پایین</th>
                            <th class="extra">MACD</th><th class="extra">سیگنال</th><th class="extra">هیستوگرام</th>
                            <th class="extra">تنکان</th><th class="extra">کیجون</th>
                        </tr>
                    </thead>
                    <tbody id="candleBody">
                        <tr><td class="empty" colspan="16">صرافی، نماد و تایم‌فریم را انتخاب کنید و «دریافت داده» را بزنید.</td></tr>
                    </tbody>
                </table>
            </div>
        </section>
    </main>
</div>

<div id="toast" class="toast" role="status" aria-live="polite"><span id="toastIcon"></span><span id="toastMessage"></span></div>

<script>
const $ = (id) => document.getElementById(id);
const VOL = { VERY_HIGH: ['بسیار بالا', 'up'], HIGH: ['بالا', 'up'], NORMAL: ['عادی', ''], LOW: ['کم', 'warn'] };
const FETCH_LABEL = 'دریافت داده';
let toastTimer;

function num(v) {
    if (v === null || v === undefined || v === '' || v === '-') return '-';
    const n = Number(v);
    if (!isFinite(n)) return '-';
    const a = Math.abs(n);
    return n.toLocaleString('en-US', { maximumFractionDigits: a >= 1000 ? 2 : a >= 1 ? 4 : 8 });
}

function setChip(el, text, cls) {
    el.textContent = text;
    el.className = 'chip' + (el.classList.contains('num') ? ' num' : '') + (cls ? ' ' + cls : '');
}

function setStatus(state, text) {
    $('statusBadge').className = 'status ' + state;
    $('statusText').textContent = text;
}

function showToast(message, type) {
    const t = $('toast');
    $('toastIcon').textContent = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ';
    $('toastMessage').textContent = message;
    t.className = 'toast show ' + (type || '');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { t.className = 'toast'; }, type === 'error' ? 6000 : 3500);
}

function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    $('themeBtn').textContent = theme === 'dark' ? 'تم روشن' : 'تم تیره';
    try { localStorage.setItem('theme', theme); } catch (e) {}
}

async function fetchMarketData() {
    const btn = $('fetchBtn');
    const symbol = $('symbol').value.trim();
    const exchange = $('exchange').value;
    const timeframe = $('timeframe').value;
    let limit = parseInt($('limit').value, 10);

    if (!symbol) { showToast('نماد را وارد کنید.', 'error'); $('symbol').focus(); return; }
    if (isNaN(limit)) limit = 50;
    limit = Math.min(Math.max(limit, 1), 1000);
    $('limit').value = limit;

    btn.disabled = true;
    btn.innerHTML = '<svg class="spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10" stroke-opacity=".25"/><path d="M12 2a10 10 0 0 1 10 10"/></svg> در حال دریافت...';
    $('tablePanel').setAttribute('aria-busy', 'true');
    setStatus('busy', 'در حال اتصال به ' + $('exchange').selectedOptions[0].text);

    try {
        const res = await pywebview.api.fetch_market_data(symbol, timeframe, exchange, limit);
        if (res.status === 'ok') {
            renderStats(res.stats);
            renderCandles(res.candles);
            $('displayTitle').textContent = res.symbol + ' · ' + $('timeframe').selectedOptions[0].text + ' · ' + $('exchange').selectedOptions[0].text;
            $('lastUpdate').textContent = 'آخرین به‌روزرسانی: ' + new Date().toLocaleDateString('fa-IR') + ' ' + new Date().toLocaleTimeString('fa-IR');
            $('exportBtn').disabled = false;
            setStatus('ok', 'به‌روز');
            showToast('داده‌ها دریافت شدند.', 'success');
        } else {
            setStatus('err', 'خطا');
            showToast(res.message, 'error');
        }
    } catch (err) {
        setStatus('err', 'خطای اتصال');
        showToast('ارتباط با برنامه برقرار نشد: ' + err, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = FETCH_LABEL;
        $('tablePanel').removeAttribute('aria-busy');
    }
}

function renderStats(s) {
    if (!s) return;

    $('statClose').textContent = num(s.close);
    const chg = s.change_pct;
    if (chg === null || chg === undefined) {
        setChip($('badgeChange'), '-', '');
    } else {
        const up = Number(chg) >= 0;
        setChip($('badgeChange'), (up ? '▲ +' : '▼ ') + chg + '%', up ? 'up' : 'down');
    }

    const rsi = Number(s.rsi);
    if (isFinite(rsi) && s.rsi !== '-') {
        $('statRSI').textContent = rsi.toFixed(2);
        const cls = rsi >= 70 ? 'down' : rsi <= 30 ? 'up' : '';
        $('rsiFill').style.width = Math.min(Math.max(rsi, 0), 100) + '%';
        $('rsiFill').className = 'gauge-fill ' + cls;
        setChip($('badgeRsi'), rsi >= 70 ? 'اشباع خرید' : rsi <= 30 ? 'اشباع فروش' : 'خنثی', cls);
    } else {
        $('statRSI').textContent = '-';
        setChip($('badgeRsi'), '-', '');
    }

    const bb = s.bollinger || {};
    $('bbUpper').textContent = num(bb.upper);
    $('bbMid').textContent = num(bb.mid);
    $('bbLower').textContent = num(bb.lower);

    const m = s.macd || {};
    $('macdVal').textContent = num(m.macd);
    $('macdSignal').textContent = num(m.signal);
    const hist = Number(m.hist);
    const histOk = isFinite(hist) && m.hist !== '-';
    $('statHist').textContent = num(m.hist);
    $('statHist').className = 'num ' + (histOk ? (hist >= 0 ? 'pos' : 'neg') : '');
    setChip($('badgeMacd'), histOk ? (hist >= 0 ? 'صعودی' : 'نزولی') : '-', histOk ? (hist >= 0 ? 'up' : 'down') : '');

    const ic = s.ichimoku || {};
    $('statTenkan').textContent = num(ic.tenkan);
    $('statKijun').textContent = num(ic.kijun);
    const tk = Number(ic.tenkan), kj = Number(ic.kijun);
    const icOk = isFinite(tk) && isFinite(kj) && ic.tenkan !== '-' && ic.kijun !== '-';
    setChip($('badgeIchi'), icOk ? (tk >= kj ? 'صعودی' : 'نزولی') : '-', icOk ? (tk >= kj ? 'up' : 'down') : '');

    $('statVol').textContent = num(s.volume);
    const v = VOL[s.volume_status];
    setChip($('badgeVol'), v ? v[0] : '-', v ? v[1] : '');
    $('statVolRatio').textContent = s.vol_ratio === '-' ? '-' : '×' + s.vol_ratio;
}

function renderCandles(candles) {
    const body = $('candleBody');
    if (!candles || !candles.length) {
        body.innerHTML = '<tr><td class="empty" colspan="16">داده‌ای پیدا نشد.</td></tr>';
        $('candleCount').textContent = '۰ کندل';
        return;
    }
    $('candleCount').textContent = candles.length.toLocaleString('fa-IR') + ' کندل';

    const cell = (v, cls) => '<td class="num ' + (cls || '') + '">' + num(v) + '</td>';
    let html = '';
    for (let i = candles.length - 1; i >= 0; i--) {
        const c = candles[i];
        const dir = Number(c.close) >= Number(c.open) ? 't-up' : 't-down';
        const vol = VOL[c.vol_status];
        html += '<tr><td class="num">' + c.timestamp + '</td>'
            + cell(c.open) + cell(c.high) + cell(c.low) + cell(c.close, dir) + cell(c.volume)
            + '<td>' + (vol ? '<span class="chip ' + vol[1] + '">' + vol[0] + '</span>' : '-') + '</td>'
            + '<td class="num">' + (c.rsi === '-' ? '-' : Number(c.rsi).toFixed(2)) + '</td>'
            + ['bb_upper', 'bb_mid', 'bb_lower', 'macd', 'signal', 'hist', 'tenkan', 'kijun']
                .map((k) => cell(c[k]).replace('<td class="num ', '<td class="extra num ')).join('')
            + '</tr>';
    }
    body.innerHTML = html;

    const last = candles[candles.length - 1];
    $('statRange').textContent = num(last.low) + ' – ' + num(last.high);
}

async function exportExcel() {
    try {
        const res = await pywebview.api.export_excel();
        if (res.status === 'ok') showToast('فایل ذخیره شد: ' + res.path, 'success');
        else showToast(res.message, 'error');
    } catch (err) {
        showToast('خطا: ' + err, 'error');
    }
}

function copyTableData() {
    const rows = [...$('candleTable').rows].map((r) =>
        [...r.cells].filter((c) => c.offsetParent !== null).map((c) => c.innerText.trim()).join('\t')
    );
    const text = rows.join('\n');
    const fallback = () => {
        const ta = document.createElement('textarea');
        ta.value = text; document.body.appendChild(ta); ta.select();
        const ok = document.execCommand('copy');
        ta.remove();
        showToast(ok ? 'جدول کپی شد.' : 'کپی انجام نشد.', ok ? 'success' : 'error');
    };
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => showToast('جدول کپی شد.', 'success')).catch(fallback);
    } else {
        fallback();
    }
}

$('fetchBtn').addEventListener('click', fetchMarketData);
$('exportBtn').addEventListener('click', exportExcel);
$('copyBtn').addEventListener('click', copyTableData);
$('showAll').addEventListener('change', (e) => $('candleTable').classList.toggle('show-all', e.target.checked));
$('themeBtn').addEventListener('click', () => applyTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'));
['symbol', 'limit'].forEach((id) => $(id).addEventListener('keydown', (e) => { if (e.key === 'Enter') fetchMarketData(); }));

applyTheme(document.documentElement.dataset.theme);
setInterval(() => { $('clockText').textContent = new Date().toLocaleTimeString('fa-IR'); }, 1000);
</script>
</body>
</html>
"""


def gregorian_to_jalali(gy, gm, gd):
    offsets = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = (355666 + 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100
            + (gy2 + 399) // 400 + gd + offsets[gm - 1])
    jy = -1595 + 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm, jd = 1 + days // 31, 1 + days % 31
    else:
        jm, jd = 7 + (days - 186) // 30, 1 + (days - 186) % 30
    return jy, jm, jd


def to_jalali_text(timestamp):
    try:
        date_part, time_part = timestamp.split(" ")
        gy, gm, gd = (int(x) for x in date_part.split("-"))
        jy, jm, jd = gregorian_to_jalali(gy, gm, gd)
        return f"{jy:04d}/{jm:02d}/{jd:02d} {time_part}"
    except Exception:
        return timestamp


def _fmt(value):
    return "-" if value is None else value


class MarketDataAPI:
    def __init__(self):
        self._last_candles = []
        self._last_symbol = ""
        self._last_timeframe = ""

    def fetch_market_data(self, symbol, timeframe, exchange, limit=50):
        try:
            try:
                limit_int = int(limit)
            except Exception:
                limit_int = 50

            sym, rows = fetch_market_data(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit_int,
                exchange_id=exchange,
            )

            candles = self._rows_to_candles(rows)
            if not candles:
                return {"status": "error", "message": "داده‌ای از صرافی دریافت نشد."}

            stats = self._extract_latest_stats(candles)

            self._last_candles = candles
            self._last_symbol = sym
            self._last_timeframe = timeframe

            return {
                "status": "ok",
                "symbol": sym,
                "timeframe": timeframe,
                "exchange": exchange,
                "stats": stats,
                "candles": candles,
            }
        except DataFetchError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": f"خطای غیرمنتظره: {e}"}

    def export_excel(self):
        if not self._last_candles:
            return {"status": "error", "message": "ابتدا دیتای بازار را دریافت کنید."}
        try:
            import pandas as pd
            df = pd.DataFrame(self._last_candles)
            filename = (
                f"candles_{self._last_symbol.replace('/', '_')}_{self._last_timeframe}_"
                f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            )
            filepath = os.path.join(os.getcwd(), filename)
            df.to_excel(filepath, index=False)
            return {"status": "ok", "path": filepath}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def _rows_to_candles(rows):
        keys = [
            "timestamp", "open", "high", "low", "close", "volume",
            "vol_sma20", "vol_ratio", "vol_status",
            "rsi", "bb_upper", "bb_mid", "bb_lower",
            "macd", "signal", "hist", "tenkan", "kijun",
        ]
        candles = []
        for row in rows:
            candle = {k: _fmt(v) for k, v in zip(keys, row)}
            candle["timestamp"] = to_jalali_text(candle["timestamp"])
            candles.append(candle)
        return candles

    def _extract_latest_stats(self, candles):
        if not candles:
            return {}
        c = candles[-1]

        change_pct = None
        if len(candles) >= 2:
            try:
                prev_c = float(candles[-2].get("close", 0))
                curr_c = float(c.get("close", 0))
                if prev_c > 0:
                    change_pct = round(((curr_c - prev_c) / prev_c) * 100, 2)
            except Exception:
                pass

        return {
            "close": c.get("close", "-"),
            "change_pct": change_pct,
            "rsi": c.get("rsi", "-"),
            "bollinger": {
                "upper": c.get("bb_upper", "-"),
                "mid": c.get("bb_mid", "-"),
                "lower": c.get("bb_lower", "-"),
            },
            "macd": {
                "macd": c.get("macd", "-"),
                "signal": c.get("signal", "-"),
                "hist": c.get("hist", "-"),
            },
            "ichimoku": {
                "tenkan": c.get("tenkan", "-"),
                "kijun": c.get("kijun", "-"),
            },
            "volume": c.get("volume", "-"),
            "volume_status": c.get("vol_status", "-"),
            "vol_ratio": c.get("vol_ratio", "-"),
        }


if __name__ == "__main__":
    api = MarketDataAPI()
    webview.create_window(
        title="نبض بازار کریپتو - دریافت و تحلیل داده‌های صرافی‌ها",
        html=HTML_CODE,
        js_api=api,
        width=1280,
        height=860,
        min_size=(1000, 680),
    )
    webview.start()
