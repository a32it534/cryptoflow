"""
ماژول دریافت داده بازار با ccxt (فقط صرافی‌های KuCoin، BingX و LBank)
و محاسبه اندیکاتورها. هیچ بخش هوش مصنوعی‌ای در این فایل وجود ندارد.
"""
import math
from datetime import datetime, timezone

import ccxt


# صرافی‌های پشتیبانی‌شده: شناسه ccxt -> نام نمایشی
SUPPORTED_EXCHANGES = {
    "kucoin": "KuCoin",
    "bingx": "BingX",
    "lbank": "LBank",
}

# تایم‌فریم‌هایی که در رابط کاربری نمایش داده می‌شوند.
# پیش از دریافت، پشتیبانی هر صرافی از تایم‌فریم انتخابی بررسی می‌شود.
COMMON_TIMEFRAMES = [
    "1m", "3m", "5m", "15m", "30m",
    "1h", "2h", "4h", "6h", "8h", "12h",
    "1d", "1w",
]

MAX_CANDLES = 1000

COLUMNS = [
    "Time (UTC)", "Open", "High", "Low", "Close", "Volume",
    "Vol_SMA20", "Vol_Ratio", "Vol_Status",
    "RSI(14)", "BB_Upper", "BB_Mid", "BB_Lower",
    "MACD", "Signal", "Histogram", "Tenkan(9)", "Kijun(26)",
]


class DataFetchError(Exception):
    """خطای قابل‌نمایش به کاربر هنگام دریافت یا پردازش داده."""


def create_exchange_instance(exchange_id):
    """ساخت کلاینت عمومی ccxt (بدون نیاز به API Key)."""
    exchange_id = str(exchange_id or "").strip().lower()
    if exchange_id not in SUPPORTED_EXCHANGES:
        raise DataFetchError(f"صرافی پشتیبانی‌نشده: {exchange_id}")
    exchange_class = getattr(ccxt, exchange_id)
    return exchange_class({"enableRateLimit": True, "timeout": 20000})


def smart_round(value, significant=8):
    """گرد کردن بر اساس ارقام معنادار؛ برای ارزهای ارزان‌قیمت هم صفر نمی‌شود."""
    if value is None:
        return None
    if value == 0:
        return 0.0
    return float(f"{value:.{significant}g}")


def calculate_sma(data, period=20):
    """
    محاسبه میانگین متحرک ساده.
    """
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
    """
    محاسبه میانگین متحرک نمایی.
    """
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
    """
    محاسبه RSI با روش Wilder.
    """
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
    """
    محاسبه باندهای بولینگر.

    خروجی:
    upper_band, middle_band, lower_band
    """
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
    """
    محاسبه MACD، خط سیگنال و هیستوگرام.
    """
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

    # هماهنگ‌سازی خط سیگنال با طول کل داده‌ها
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
    """
    محاسبه Tenkan-sen و Kijun-sen ایچیموکو.

    Tenkan-sen: دوره ۹
    Kijun-sen: دوره ۲۶
    """
    tenkan = []
    kijun = []

    for i in range(len(closes)):

        # Tenkan-sen
        if i < 8:
            tenkan.append(None)
        else:
            highest_high = max(highs[i - 8:i + 1])
            lowest_low = min(lows[i - 8:i + 1])

            tenkan_value = (
                highest_high + lowest_low
            ) / 2

            tenkan.append(round(tenkan_value, 12))

        # Kijun-sen
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
    """
    تعیین وضعیت حجم نسبت به میانگین حجم ۲۰ کندل.
    """
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
    """BTC -> BTC/USDT ، btc/usdt -> BTC/USDT"""
    sym = str(symbol or "").strip().upper().replace(" ", "")
    if not sym:
        raise DataFetchError("نماد رمزارز را وارد کنید.")
    if "/" not in sym:
        sym += "/USDT"
    return sym


def fetch_market_data(symbol, timeframe, limit=50, exchange_id="kucoin",
                      drop_unclosed=False):
    """
    دریافت کندل‌ها از صرافی انتخاب‌شده و محاسبه اندیکاتورها.

    خروجی: دیکشنری با کلیدهای
        columns : نام ستون‌ها
        rows    : لیست ردیف‌ها (عدد خام؛ None برای مقدار نامعلوم)
        meta    : symbol / timeframe / exchange / count
    در صورت خطا DataFetchError با پیام فارسی ایجاد می‌شود.
    """
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

        # چند کندل اضافه برای گرم‌شدن اندیکاتورها (MACD/Ichimoku) دریافت می‌شود
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

    # پاک‌سازی، حذف تکراری‌ها و مرتب‌سازی صعودی بر اساس زمان
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

    if drop_unclosed and len(ohlcv) > 1:
        ohlcv = ohlcv[:-1]

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
            datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
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

    return {
        "columns": COLUMNS,
        "rows": rows,
        "meta": {
            "symbol": symbol,
            "timeframe": timeframe,
            "exchange": exchange_id,
            "exchange_name": exchange_name,
            "count": len(rows),
        },
    }
