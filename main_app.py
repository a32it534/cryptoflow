import os
import re
import sys
import datetime
import webview

# افزودن مسیر پوشه جاری و پوشه والد به sys.path جهت اطمینان از ایمپورت شدن crypto_tools
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
for p in [current_dir, parent_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from crypto_tools import get_candles_with_indicators
except ImportError:
    try:
        from crypto_tools import get_lbank_candles_with_indicators as get_candles_with_indicators
    except Exception as e:
        raise ImportError(f"فایل crypto_tools.py در مسیر یافت نشد یا ناقص است: {e}")

HTML_CODE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>داشبورد دریافت دیتای بازار (CCXT)</title>
    <style>
        :root {
            --bg-base: #0b1220;
            --bg-surface: rgba(17, 27, 46, 0.72);
            --bg-surface-hover: rgba(23, 37, 63, 0.85);
            --bg-elevated: rgba(30, 41, 59, 0.85);
            --border-subtle: rgba(148, 163, 184, 0.12);
            --border-accent: rgba(56, 189, 248, 0.35);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --text-faint: #64748b;
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.25);
            --accent-gradient: linear-gradient(135deg, #0284c7 0%, #38bdf8 100%);
            --success: #10b981;
            --success-glow: rgba(16, 185, 129, 0.2);
            --danger: #ef4444;
            --danger-glow: rgba(239, 68, 68, 0.2);
            --warning: #f59e0b;
            --radius-lg: 16px;
            --radius-md: 10px;
            --radius-sm: 6px;
            --transition-smooth: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Tahoma, Roboto, sans-serif;
            -webkit-font-smoothing: antialiased;
        }

        body {
            background-color: var(--bg-base);
            color: var(--text-main);
            display: flex;
            height: 100vh;
            overflow: hidden;
            position: relative;
        }

        /* لایه‌های نوری در پس‌زمینه */
        .ambient-glow {
            position: absolute;
            width: 500px;
            height: 500px;
            border-radius: 50%;
            filter: blur(120px);
            opacity: 0.15;
            pointer-events: none;
            z-index: 0;
        }
        .glow-1 {
            top: -100px;
            right: -100px;
            background: #0284c7;
        }
        .glow-2 {
            bottom: -150px;
            left: 20%;
            background: #6366f1;
        }

        /* سایدبار تنطیمات */
        .sidebar {
            width: 320px;
            background: var(--bg-surface);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-left: 1px solid var(--border-subtle);
            display: flex;
            flex-direction: column;
            padding: 24px;
            gap: 18px;
            flex-shrink: 0;
            overflow-y: auto;
            z-index: 10;
        }

        .brand-header {
            display: flex;
            align-items: center;
            gap: 10px;
            padding-bottom: 14px;
            border-bottom: 1px solid var(--border-subtle);
        }

        .brand-icon {
            width: 36px;
            height: 36px;
            border-radius: 10px;
            background: var(--accent-gradient);
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 14px var(--accent-glow);
        }

        .brand-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--text-main);
            letter-spacing: -0.3px;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 7px;
        }

        label {
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 6px;
        }

        select, input {
            background-color: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border-subtle);
            color: var(--text-main);
            padding: 10px 14px;
            border-radius: var(--radius-md);
            font-size: 0.9rem;
            outline: none;
            transition: var(--transition-smooth);
        }

        select:focus, input:focus {
            border-color: var(--accent);
            box-shadow: 0 0 0 3px var(--accent-glow);
            background-color: rgba(15, 23, 42, 0.9);
        }

        .btn-primary {
            background: var(--accent-gradient);
            color: #0b1220;
            border: none;
            padding: 13px;
            border-radius: var(--radius-md);
            font-weight: 700;
            font-size: 0.92rem;
            cursor: pointer;
            transition: var(--transition-smooth);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            margin-top: 4px;
            box-shadow: 0 4px 16px var(--accent-glow);
        }

        .btn-primary:hover:not(:disabled) {
            transform: translateY(-1px);
            box-shadow: 0 6px 22px rgba(56, 189, 248, 0.4);
        }

        .btn-primary:active:not(:disabled) {
            transform: translateY(0);
        }

        .btn-primary:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            filter: grayscale(0.4);
        }

        .btn-secondary {
            background-color: rgba(30, 41, 59, 0.5);
            color: var(--text-main);
            border: 1px solid var(--border-subtle);
            padding: 11px;
            border-radius: var(--radius-md);
            font-weight: 600;
            font-size: 0.85rem;
            cursor: pointer;
            transition: var(--transition-smooth);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .btn-secondary:hover {
            background-color: rgba(51, 65, 85, 0.7);
            border-color: var(--text-muted);
        }

        .helper-card {
            background: rgba(15, 23, 42, 0.4);
            border: 1px dashed var(--border-subtle);
            border-radius: var(--radius-md);
            padding: 12px;
            font-size: 0.75rem;
            color: var(--text-muted);
            line-height: 1.5;
            margin-top: auto;
        }

        /* پنل اصلی محتوا */
        .main-panel {
            flex: 1;
            display: flex;
            flex-direction: column;
            padding: 24px 28px;
            gap: 20px;
            overflow-y: auto;
            z-index: 1;
        }

        .header-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--bg-surface);
            backdrop-filter: blur(16px);
            padding: 16px 24px;
            border-radius: var(--radius-lg);
            border: 1px solid var(--border-subtle);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        }

        .header-title-wrap {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .header-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--text-main);
            letter-spacing: -0.2px;
        }

        .header-subtitle {
            font-size: 0.8rem;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 0.82rem;
            font-weight: 600;
            padding: 6px 14px;
            border-radius: 30px;
            background: rgba(148, 163, 184, 0.1);
            color: var(--text-muted);
            border: 1px solid var(--border-subtle);
            transition: var(--transition-smooth);
        }

        .status-pill.active {
            background: var(--success-glow);
            color: var(--success);
            border-color: rgba(16, 185, 129, 0.3);
        }

        .status-pill.error {
            background: var(--danger-glow);
            color: var(--danger);
            border-color: rgba(239, 68, 68, 0.3);
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: currentColor;
        }

        /* گرید کارت‌های آماری */
        .indicators-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px;
        }

        .stat-card {
            background: var(--bg-surface);
            backdrop-filter: blur(14px);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-lg);
            padding: 16px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            gap: 10px;
            transition: var(--transition-smooth);
            position: relative;
            overflow: hidden;
        }

        .stat-card:hover {
            transform: translateY(-2px);
            background: var(--bg-surface-hover);
            border-color: var(--border-accent);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
        }

        .stat-card::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: transparent;
            transition: var(--transition-smooth);
        }

        .stat-card:hover::before {
            background: var(--accent-gradient);
        }

        .stat-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .stat-label {
            font-size: 0.76rem;
            font-weight: 600;
            color: var(--text-muted);
        }

        .stat-badge {
            font-size: 0.7rem;
            padding: 2px 7px;
            border-radius: 4px;
            font-weight: 600;
            background: rgba(148, 163, 184, 0.1);
            color: var(--text-muted);
        }

        .stat-badge.bullish {
            background: var(--success-glow);
            color: var(--success);
        }

        .stat-badge.bearish {
            background: var(--danger-glow);
            color: var(--danger);
        }

        .stat-value {
            font-size: 1.35rem;
            font-weight: 700;
            color: var(--text-main);
            letter-spacing: -0.5px;
            font-variant-numeric: tabular-nums;
        }

        .stat-subline {
            font-size: 0.74rem;
            color: var(--text-muted);
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid var(--border-subtle);
            padding-top: 8px;
            font-variant-numeric: tabular-nums;
        }

        /* نوار نشانگر RSI */
        .rsi-track {
            height: 4px;
            width: 100%;
            background: rgba(148, 163, 184, 0.15);
            border-radius: 2px;
            overflow: hidden;
            position: relative;
            margin-top: 4px;
        }
        .rsi-fill {
            height: 100%;
            width: 50%;
            background: var(--accent);
            border-radius: 2px;
            transition: width 0.4s ease;
        }

        /* کانتینر جدول کندل‌ها */
        .table-card {
            background: var(--bg-surface);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-lg);
            padding: 18px;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 12px;
            min-height: 360px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        }

        .table-toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 8px;
        }

        .table-title-group {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .table-title {
            font-size: 0.95rem;
            font-weight: 700;
            color: var(--text-main);
        }

        .pill-count {
            font-size: 0.72rem;
            padding: 3px 9px;
            border-radius: 12px;
            background: rgba(56, 189, 248, 0.1);
            color: var(--accent);
            font-weight: 600;
        }

        .table-actions {
            display: flex;
            gap: 8px;
        }

        .btn-mini {
            background: transparent;
            border: 1px solid var(--border-subtle);
            color: var(--text-muted);
            padding: 6px 12px;
            border-radius: var(--radius-sm);
            font-size: 0.75rem;
            font-weight: 600;
            cursor: pointer;
            transition: var(--transition-smooth);
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .btn-mini:hover {
            color: var(--text-main);
            border-color: var(--accent);
            background: rgba(56, 189, 248, 0.05);
        }

        .table-scroll {
            flex: 1;
            overflow: auto;
            border-radius: var(--radius-md);
            border: 1px solid var(--border-subtle);
            background: rgba(11, 18, 32, 0.4);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: right;
            font-size: 0.82rem;
            white-space: nowrap;
        }

        th {
            background: rgba(17, 27, 46, 0.95);
            backdrop-filter: blur(8px);
            color: var(--text-muted);
            padding: 11px 14px;
            font-weight: 600;
            font-size: 0.75rem;
            position: sticky;
            top: 0;
            z-index: 2;
            border-bottom: 1px solid var(--border-subtle);
        }

        td {
            padding: 10px 14px;
            border-bottom: 1px solid rgba(148, 163, 184, 0.06);
            color: var(--text-main);
            font-variant-numeric: tabular-nums;
        }

        tr:last-child td {
            border-bottom: none;
        }

        tr:hover td {
            background-color: rgba(56, 189, 248, 0.04);
        }

        .td-up {
            color: var(--success);
            font-weight: 600;
        }

        .td-down {
            color: var(--danger);
            font-weight: 600;
        }

        .tag-status {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 700;
        }
        .tag-HIGH { background: var(--success-glow); color: var(--success); }
        .tag-LOW { background: rgba(245, 158, 11, 0.15); color: var(--warning); }
        .tag-NORMAL { background: rgba(56, 189, 248, 0.12); color: var(--accent); }

        /* پیام اعلان (Toast) */
        .toast {
            position: fixed;
            bottom: 24px;
            left: 24px;
            background: var(--bg-elevated);
            color: var(--text-main);
            padding: 12px 18px;
            border-radius: var(--radius-md);
            border: 1px solid var(--border-subtle);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
            font-size: 0.84rem;
            display: flex;
            align-items: center;
            gap: 10px;
            z-index: 1000;
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            pointer-events: none;
        }
        .toast.show {
            transform: translateY(0);
            opacity: 1;
        }
        .toast.success { border-color: var(--success); }
        .toast.error { border-color: var(--danger); }

        /* ریسپانسیو برای مانیتورهای کوچک */
        @media (max-width: 1080px) {
            body {
                flex-direction: column;
                height: auto;
                min-height: 100vh;
                overflow: auto;
            }
            .sidebar {
                width: 100%;
                border-left: none;
                border-bottom: 1px solid var(--border-subtle);
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 12px;
            }
            .brand-header, .helper-card {
                grid-column: 1 / -1;
            }
        }
    </style>
</head>
<body>
    <div class="ambient-glow glow-1"></div>
    <div class="ambient-glow glow-2"></div>

    <!-- سایدبار کنترل و تنظیمات -->
    <div class="sidebar">
        <div class="brand-header">
            <div class="brand-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#0b1220" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"></polyline>
                    <polyline points="16 7 22 7 22 13"></polyline>
                </svg>
            </div>
            <div>
             <div class="brand-title">نبض بازار</div>
                <div style="font-size: 0.72rem; color: var(--text-muted);">واکشی مستقیم دیتای صرافی</div>
            </div>
        </div>

        <div class="form-group">
            <label>صرافی انتخابی</label>
            <select id="exchange">
                <option value="bingx" selected>BingX</option>
                <option value="lbank">LBank</option>
                <option value="coinex">CoinEx</option>
                <option value="mexc">MEXC</option>
                <option value="binance">Binance</option>
                <option value="bybit">Bybit</option>
                <option value="kucoin">KuCoin</option>
                <option value="gateio">Gate.io</option>
                <option value="bitget">Bitget</option>
            </select>
        </div>

        <div class="form-group">
            <label>نماد معاملاتی (Symbol)</label>
            <input type="text" id="symbol" value="BTC/USDT" placeholder="BTC/USDT" />
        </div>

        <div class="form-group">
            <label>تایم‌فریم (Timeframe)</label>
            <select id="timeframe">
                <option value="15m">۱۵ دقیقه (15m)</option>
                <option value="1h">۱ ساعت (1h)</option>
                <option value="4h">۴ ساعت (4h)</option>
                <option value="1d" selected>روزانه (1D)</option>
            </select>
        </div>

        <div class="form-group">
            <label>تعداد کندل‌ها (Limit)</label>
            <input type="number" id="limit" value="50" min="10" max="200" />
        </div>

        <button id="fetchBtn" class="btn-primary" onclick="fetchMarketData()">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.19"/>
            </svg>
            دریافت دیتای بازار
        </button>

        <button class="btn-secondary" onclick="exportExcel()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            خروجی اکسل (Excel)
        </button>

       
    </div>

    <!-- بدنه اصلی داشبورد -->
    <div class="main-panel">
        <!-- هدر بالای صفحه -->
        <div class="header-bar">
            <div class="header-title-wrap">
                <div class="header-title" id="displayTitle">داده‌های بازار</div>
                <div class="header-subtitle">
                    <span id="lastUpdate">در انتظار درخواست اولیه...</span>
                    <span>•</span>
                    <span id="clockText">--:--:--</span>
                </div>
            </div>
            <div id="statusBadge" class="status-pill">
                <span class="status-dot"></span>
                <span id="statusText">آماده</span>
            </div>
        </div>

        <!-- کارت‌های ۶ گانه آمار و اندیکاتورها -->
        <div class="indicators-grid">
            <!-- ۱. قیمت پایانی -->
            <div class="stat-card">
                <div class="stat-header">
                    <span class="stat-label">آخرین قیمت (Close)</span>
                    <span id="badgeChange" class="stat-badge">-</span>
                </div>
                <div class="stat-value" id="statClose">-</div>
                <div class="stat-subline">
                    <span>دامنه کندل:</span>
                    <span id="statRange">-</span>
                </div>
            </div>

            <!-- ۲. شاخص RSI -->
            <div class="stat-card">
                <div class="stat-header">
                    <span class="stat-label">شاخص قدرت نسبی (RSI 14)</span>
                    <span id="badgeRsi" class="stat-badge">-</span>
                </div>
                <div class="stat-value" id="statRSI">-</div>
                <div class="rsi-track">
                    <div id="rsiFill" class="rsi-fill" style="width: 50%;"></div>
                </div>
                <div class="stat-subline">
                    <span>محدوده:</span>
                    <span>30 (Oversold) - 70 (Overbought)</span>
                </div>
            </div>

            <!-- ۳. باندهای بولینگر -->
            <div class="stat-card">
                <div class="stat-header">
                    <span class="stat-label">باندهای بولینگر (20, 2)</span>
                    <span class="stat-badge">BBands</span>
                </div>
                <div class="stat-value" style="font-size: 1.05rem;" id="statBBMid">-</div>
                <div class="stat-subline">
                    <span>بالا / پایین:</span>
                    <span id="statBBLimits">-</span>
                </div>
            </div>

            <!-- ۴. مک‌دی -->
            <div class="stat-card">
                <div class="stat-header">
                    <span class="stat-label">شاخص MACD (12, 26, 9)</span>
                    <span id="badgeMacd" class="stat-badge">Momentum</span>
                </div>
                <div class="stat-value" style="font-size: 1.05rem;" id="statMACD">-</div>
                <div class="stat-subline">
                    <span>هیستوگرام:</span>
                    <span id="statHist">-</span>
                </div>
            </div>

            <!-- ۵. ایچیموکو -->
            <div class="stat-card">
                <div class="stat-header">
                    <span class="stat-label">ایچیموکو (Ichimoku)</span>
                    <span class="stat-badge">Trend</span>
                </div>
                <div class="stat-value" style="font-size: 1.05rem;" id="statTenkan">-</div>
                <div class="stat-subline">
                    <span>Kijun-sen:</span>
                    <span id="statKijun">-</span>
                </div>
            </div>

            <!-- ۶. حجم معاملات -->
            <div class="stat-card">
                <div class="stat-header">
                    <span class="stat-label">حجم معاملات (Volume)</span>
                    <span id="badgeVol" class="stat-badge">-</span>
                </div>
                <div class="stat-value" style="font-size: 1.15rem;" id="statVol">-</div>
                <div class="stat-subline">
                    <span>نسبت به میانگین ۲۰ کندل:</span>
                    <span id="statVolRatio">-</span>
                </div>
            </div>
        </div>

        <!-- جدول کندل‌ها -->
        <div class="table-card">
            <div class="table-toolbar">
                <div class="table-title-group">
                    <span class="table-title">کندل‌های دریافتی</span>
                    <span class="pill-count" id="candleCount">0 کندل</span>
                </div>
                <div class="table-actions">
                    <button class="btn-mini" onclick="copyTableData()">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                        </svg>
                        کپی داده‌ها
                    </button>
                </div>
            </div>

            <div class="table-scroll">
                <table id="candleTable">
                    <thead>
                        <tr>
                            <th>زمان (UTC)</th>
                            <th>قیمت باز (Open)</th>
                            <th>بیشترین (High)</th>
                            <th>کمترین (Low)</th>
                            <th>پایانی (Close)</th>
                            <th>حجم (Volume)</th>
                            <th>RSI</th>
                            <th>وضعیت حجم</th>
                        </tr>
                    </thead>
                    <tbody id="candleBody">
                        <tr>
                            <td colspan="8" style="text-align: center; color: var(--text-faint); padding: 40px;">
                                برای مشاهده اطلاعات، دکمه «دریافت دیتای بازار» را بزنید.
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- اعلان پیام Toast -->
    <div id="toast" class="toast">
        <span id="toastIcon">ℹ️</span>
        <span id="toastMessage">پیام سیستم</span>
    </div>

    <script>
        // ساعت دیجیتال زنده در هدر
        setInterval(() => {
            const now = new Date();
            document.getElementById('clockText').innerText = now.toLocaleTimeString('fa-IR');
        }, 1000);

        // فعال‌سازی با Enter
        document.getElementById('symbol').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') fetchMarketData();
        });

        function showToast(message, type = 'info') {
            const toast = document.getElementById('toast');
            const msg = document.getElementById('toastMessage');
            const icon = document.getElementById('toastIcon');

            toast.className = `toast show ${type}`;
            msg.innerText = message;
            icon.innerText = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ';

            setTimeout(() => {
                toast.className = 'toast';
            }, 3500);
        }

        function formatNum(val) {
            if (!val || val === '-' || isNaN(val)) return val || '-';
            const num = parseFloat(val);
            if (Math.abs(num) >= 1) {
                return num.toLocaleString('en-US', { maximumFractionDigits: 2 });
            }
            return num.toLocaleString('en-US', { maximumFractionDigits: 6 });
        }

        async function fetchMarketData() {
            const btn = document.getElementById('fetchBtn');
            const statusBadge = document.getElementById('statusBadge');
            const statusText = document.getElementById('statusText');
            const sym = document.getElementById('symbol').value.trim();
            const tf = document.getElementById('timeframe').value;
            const ex = document.getElementById('exchange').value;
            const lim = document.getElementById('limit').value || 50;

            btn.disabled = true;
            btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="spin"><circle cx="12" cy="12" r="10" stroke-opacity="0.25"/><path d="M12 2a10 10 0 0 1 10 10"/></svg> در حال دریافت...`;
            statusBadge.className = 'status-pill active';
            statusText.innerText = 'اتصال به ' + ex.toUpperCase();

            try {
                const res = await pywebview.api.fetch_market_data(sym, tf, ex, lim);
                if (res.status === 'ok') {
                    renderStats(res.stats);
                    renderCandles(res.candles);
                    document.getElementById('displayTitle').innerText = `${res.symbol} (${res.timeframe.toUpperCase()}) - ${res.exchange.toUpperCase()}`;
                    document.getElementById('lastUpdate').innerText = 'بروزرسانی: ' + new Date().toLocaleTimeString('fa-IR');
                    statusBadge.className = 'status-pill active';
                    statusText.innerText = 'همگام شد';
                    showToast('داده‌های بازار با موفقیت دریافت شدند.', 'success');
                } else {
                    statusBadge.className = 'status-pill error';
                    statusText.innerText = 'خطا';
                    showToast(res.message, 'error');
                }
            } catch (err) {
                statusBadge.className = 'status-pill error';
                statusText.innerText = 'خطای اتصال';
                showToast('خطا در برقراری ارتباط: ' + err, 'error');
            } finally {
                btn.disabled = false;
                btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.19"/></svg> دریافت دیتای بازار`;
            }
        }

        function renderStats(stats) {
            if (!stats) return;

            // ۱. قیمت پایانی و تغییر درصد
            document.getElementById('statClose').innerText = formatNum(stats.close);
            const badgeChange = document.getElementById('badgeChange');
            if (stats.change_pct !== undefined && stats.change_pct !== null) {
                const isPos = parseFloat(stats.change_pct) >= 0;
                badgeChange.innerText = (isPos ? '▲ +' : '▼ ') + stats.change_pct + '%';
                badgeChange.className = 'stat-badge ' + (isPos ? 'bullish' : 'bearish');
            } else {
                badgeChange.innerText = '-';
                badgeChange.className = 'stat-badge';
            }

            // ۲. RSI
            const rsiVal = parseFloat(stats.rsi);
            document.getElementById('statRSI').innerText = !isNaN(rsiVal) ? rsiVal.toFixed(2) : (stats.rsi || '-');
            const rsiFill = document.getElementById('rsiFill');
            const badgeRsi = document.getElementById('badgeRsi');
            if (!isNaN(rsiVal)) {
                rsiFill.style.width = Math.min(Math.max(rsiVal, 0), 100) + '%';
                if (rsiVal >= 70) {
                    badgeRsi.innerText = 'Overbought';
                    badgeRsi.className = 'stat-badge bearish';
                    rsiFill.style.background = 'var(--danger)';
                } else if (rsiVal <= 30) {
                    badgeRsi.innerText = 'Oversold';
                    badgeRsi.className = 'stat-badge bullish';
                    rsiFill.style.background = 'var(--success)';
                } else {
                    badgeRsi.innerText = 'Neutral';
                    badgeRsi.className = 'stat-badge';
                    rsiFill.style.background = 'var(--accent)';
                }
            }

            // ۳. بولینگر باند
            if (stats.bollinger) {
                document.getElementById('statBBMid').innerText = 'Mid: ' + formatNum(stats.bollinger.mid);
                document.getElementById('statBBLimits').innerText = formatNum(stats.bollinger.upper) + ' / ' + formatNum(stats.bollinger.lower);
            }

            // ۴. مک‌دی
            if (stats.macd) {
                document.getElementById('statMACD').innerText = 'M: ' + formatNum(stats.macd.macd) + ' | S: ' + formatNum(stats.macd.signal);
                const histVal = parseFloat(stats.macd.hist);
                const histEl = document.getElementById('statHist');
                histEl.innerText = formatNum(stats.macd.hist);
                histEl.style.color = histVal >= 0 ? 'var(--success)' : 'var(--danger)';
            }

            // ۵. ایچیموکو
            if (stats.ichimoku) {
                document.getElementById('statTenkan').innerText = 'Tenkan: ' + formatNum(stats.ichimoku.tenkan);
                document.getElementById('statKijun').innerText = formatNum(stats.ichimoku.kijun);
            }

            // ۶. حجم
            document.getElementById('statVol').innerText = formatNum(stats.volume);
            const badgeVol = document.getElementById('badgeVol');
            badgeVol.innerText = stats.volume_status || '-';
            badgeVol.className = 'stat-badge ' + (stats.volume_status === 'HIGH' ? 'bullish' : stats.volume_status === 'LOW' ? 'bearish' : '');
            document.getElementById('statVolRatio').innerText = stats.vol_ratio || '-';
        }

        function renderCandles(candles) {
            const tbody = document.getElementById('candleBody');
            if (!candles || candles.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 24px;">داده‌ای یافت نشد.</td></tr>';
                return;
            }

            document.getElementById('candleCount').innerText = `${candles.length} کندل`;
            
            // نمایش از جدیدترین به قدیمی‌ترین
            const reversed = [...candles].reverse();
            let rows = '';

            reversed.forEach((c, index) => {
                const openVal = parseFloat(c.open);
                const closeVal = parseFloat(c.close);
                const isBull = closeVal >= openVal;
                const closeClass = isBull ? 'td-up' : 'td-down';

                rows += `<tr>
                    <td style="color: var(--text-muted);">${c.timestamp || '-'}</td>
                    <td>${formatNum(c.open)}</td>
                    <td>${formatNum(c.high)}</td>
                    <td>${formatNum(c.low)}</td>
                    <td class="${closeClass}">${formatNum(c.close)}</td>
                    <td>${formatNum(c.volume)}</td>
                    <td>${c.rsi || '-'}</td>
                    <td><span class="tag-status tag-${c.vol_status}">${c.vol_status || '-'}</span></td>
                </tr>`;
            });
            tbody.innerHTML = rows;

            // نمایش دامنه کندل آخر در کارت قیمت
            if (candles.length > 0) {
                const latest = candles[candles.length - 1];
                document.getElementById('statRange').innerText = `${formatNum(latest.low)} - ${formatNum(latest.high)}`;
            }
        }

        async function exportExcel() {
            try {
                const res = await pywebview.api.export_excel();
                if (res.status === 'ok') {
                    showToast('فایل با موفقیت ذخیره شد:\\n' + res.path, 'success');
                } else {
                    showToast(res.message, 'error');
                }
            } catch (err) {
                showToast('خطا: ' + err, 'error');
            }
        }

        function copyTableData() {
            const table = document.getElementById('candleTable');
            let text = '';
            for (let r of table.rows) {
                let rowData = [];
                for (let c of r.cells) {
                    rowData.push(c.innerText.trim());
                }
                text += rowData.join('\\t') + '\\n';
            }
            navigator.clipboard.writeText(text).then(() => {
                showToast('اطلاعات جدول در کلیپ‌بورد کپی شد.', 'success');
            }).catch(() => {
                showToast('عدم دسترسی به کپی.', 'error');
            });
        }
    </script>
</body>
</html>
"""

class MarketDataAPI:
    def __init__(self):
        self._last_candles = []
        self._last_stats = {}
        self._last_symbol = ""
        self._last_timeframe = ""
        self._last_exchange = ""

    def fetch_market_data(self, symbol, timeframe, exchange, limit=50):
        try:
            sym = symbol.strip().upper()
            if "/" not in sym:
                sym = f"{sym}/USDT"

            try:
                limit_int = int(limit)
            except Exception:
                limit_int = 50

            # فراخوانی داده‌ها از CCXT
            raw_text = get_candles_with_indicators(
                symbol=sym,
                timeframe=timeframe,
                limit=limit_int,
                exchange_id=exchange
            )

            if isinstance(raw_text, str) and (raw_text.startswith("خطا") or "Error" in raw_text):
                return {"status": "error", "message": raw_text}

            candles = self._parse_candles(raw_text)
            if not candles:
                return {"status": "error", "message": "پاسخی از صرافی دریافت نشد یا فرمت ناشناخته است."}

            stats = self._extract_latest_stats(candles)

            self._last_candles = candles
            self._last_stats = stats
            self._last_symbol = sym
            self._last_timeframe = timeframe
            self._last_exchange = exchange

            return {
                "status": "ok",
                "symbol": sym,
                "timeframe": timeframe,
                "exchange": exchange,
                "stats": stats,
                "candles": candles
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def export_excel(self):
        if not self._last_candles:
            return {"status": "error", "message": "ابتدا دیتای بازار را دریافت کنید."}
        try:
            import pandas as pd
            df = pd.DataFrame(self._last_candles)
            filename = f"candles_{self._last_symbol.replace('/', '_')}_{self._last_timeframe}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = os.path.join(os.getcwd(), filename)
            df.to_excel(filepath, index=False)
            return {"status": "ok", "path": filepath}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _clean_val(self, val_str):
        if ":" in val_str:
            return val_str.split(":", 1)[1].strip()
        return val_str.strip()

    def _parse_candles(self, raw_text):
        candles = []
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        for line in lines:
            if "Time UTC" in line or line.startswith("داده‌های") or line.startswith("توجه"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 6:
                candle = {
                    "timestamp": parts[0],
                    "open": self._clean_val(parts[1]) if len(parts) > 1 else "",
                    "high": self._clean_val(parts[2]) if len(parts) > 2 else "",
                    "low": self._clean_val(parts[3]) if len(parts) > 3 else "",
                    "close": self._clean_val(parts[4]) if len(parts) > 4 else "",
                    "volume": self._clean_val(parts[5]) if len(parts) > 5 else "",
                    "vol_sma20": self._clean_val(parts[6]) if len(parts) > 6 else "",
                    "vol_ratio": self._clean_val(parts[7]) if len(parts) > 7 else "",
                    "vol_status": self._clean_val(parts[8]) if len(parts) > 8 else "",
                    "rsi": self._clean_val(parts[9]) if len(parts) > 9 else "",
                    "bb_upper": self._clean_val(parts[10]) if len(parts) > 10 else "",
                    "bb_mid": self._clean_val(parts[11]) if len(parts) > 11 else "",
                    "bb_lower": self._clean_val(parts[12]) if len(parts) > 12 else "",
                    "macd": self._clean_val(parts[13]) if len(parts) > 13 else "",
                    "signal": self._clean_val(parts[14]) if len(parts) > 14 else "",
                    "hist": self._clean_val(parts[15]) if len(parts) > 15 else "",
                    "tenkan": self._clean_val(parts[16]) if len(parts) > 16 else "",
                    "kijun": self._clean_val(parts[17]) if len(parts) > 17 else "",
                }
                candles.append(candle)
        return candles

    def _extract_latest_stats(self, candles):
        if not candles:
            return {}
        c = candles[-1]
        
        # محاسبه درصد تغییر کندل آخر نسبت به کندل قبل
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
                "lower": c.get("bb_lower", "-")
            },
            "macd": {
                "macd": c.get("macd", "-"),
                "signal": c.get("signal", "-"),
                "hist": c.get("hist", "-")
            },
            "ichimoku": {
                "tenkan": c.get("tenkan", "-"),
                "kijun": c.get("kijun", "-")
            },
            "volume": c.get("volume", "-"),
            "volume_status": c.get("vol_status", "-"),
            "vol_ratio": c.get("vol_ratio", "-")
        }


if __name__ == "__main__":
    api = MarketDataAPI()
    window = webview.create_window(
        title="CCXT Market Terminal",
        html=HTML_CODE,
        js_api=api,
        width=1280,
        height=860,
        min_size=(1000, 680)
    )
    webview.start()
