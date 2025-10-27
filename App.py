import streamlit as st
import pandas as pd
import numpy as np
import ccxt
from statsmodels.tsa.stattools import grangercausalitytests
import time

# --- Streamlit Setup ---
st.set_page_config(page_title="Price Source Detector", layout="centered")

st.title("🔍 Price Source Detector")
st.markdown(
    "This tool compares live crypto prices between exchanges "
    "to detect if one might be following another."
)

# --- User Input ---
target_exchange = st.text_input("Target Exchange (e.g. kcex)", value="kcex").lower().strip()
symbol = st.text_input("Coin Symbol (e.g. BTC/USDT)", value="BTC/USDT").upper().strip()
run_btn = st.button("Run Analysis")

# --- Config ---
CHECK_EXCHANGES = ['binance', 'okx', 'kucoin', 'bybit', 'gate', 'bitget', 'mexc', 'bitmart', 'huobi']
TIME_WINDOW_SEC = 180  # 3 minutes
RESAMPLE_FREQ = '1S'

# --- Fetch Live Price Data ---
def fetch_prices(exchange, symbol, since):
    try:
        ex = getattr(ccxt, exchange.lower())({'enableRateLimit': True})
        ex.load_markets()

        # Check if symbol exists
        if symbol not in ex.markets:
            st.warning(f"⚠️ {symbol} not found on {exchange}. Trying variations...")
            alt_symbol = symbol.replace('/', '').upper()
            possible = [s for s in ex.markets.keys() if s.replace('/', '').upper() == alt_symbol]
            if possible:
                symbol = possible[0]
            else:
                st.error(f"❌ {symbol} not available on {exchange}.")
                return None

        trades = ex.fetch_trades(symbol, since=since, limit=500)
        if not trades:
            st.warning(f"⚠️ No trade data found for {symbol} on {exchange}.")
            return None

        df = pd.DataFrame(trades)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df.set_index('timestamp')['price'].resample(RESAMPLE_FREQ).last().ffill()

    except Exception as e:
        st.error(f"❌ Error fetching data from {exchange}: {e}")
        return None


# --- Analyze Price Relationship ---
def analyze_pair(target, other):
    df = pd.concat([target, other], axis=1).dropna()
    df.columns = ['target', 'other']
    if len(df) < 10:
        return None

    r_t = np.log(df['target']).diff().dropna()
    r_o = np.log(df['other']).diff().dropna()
    df2 = pd.concat([r_t, r_o], axis=1).dropna()
    df2.columns = ['rt', 'ro']

    # Cross-correlation
    lags = range(-5, 6)
    best_corr = 0
    best_lag = 0
    for lag in lags:
        if lag < 0:
            corr = r_t[:lag].corr(r_o[-lag:])
        elif lag > 0:
            corr = r_t[lag:].corr(r_o[:-lag])
        else:
            corr = r_t.corr(r_o)
        if corr and abs(corr) > abs(best_corr):
            best_corr = corr
            best_lag = lag

    # Granger causality
    try:
        gtest = grangercausalitytests(df2[['rt', 'ro']], maxlag=3, verbose=False)
        pvals = [v[0]['ssr_ftest'][1] for v in gtest.values()]
        g_p = min(pvals)
    except Exception:
        g_p = 1.0

    score = abs(best_corr) * (1 - g_p)
    if best_lag < 0:
        score *= 1.2  # reward if other leads
    return {
        'best_corr': best_corr,
        'best_lag': best_lag,
        'granger_p': g_p,
        'score': score
    }


# --- Main Logic ---
if run_btn:
    st.info(f"Fetching live data for {symbol} ...")

    now = int(time.time() * 1000)
    since = now - TIME_WINDOW_SEC * 1000

    # Target exchange prices
    target_prices = fetch_prices(target_exchange, symbol, since)
    if target_prices is None or target_prices.empty:
        st.error("❌ Target exchange data not found. Try another symbol or exchange.")
        st.stop()

    results = []
    for ex in CHECK_EXCHANGES:
        st.write(f"🔹 Checking {ex} ...")
        other_prices = fetch_prices(ex, symbol, since)
        if other_prices is None or other_prices.empty:
            continue
        res = analyze_pair(target_prices, other_prices)
        if res:
            res['exchange'] = ex
            results.append(res)

    if not results:
        st.error("⚠️ Could not find enough data to compare.")
    else:
        df = pd.DataFrame(results).sort_values('score', ascending=False)
        st.success("✅ Analysis complete!")
        st.dataframe(df)
        top = df.iloc[0]
        st.markdown(
            f"**📊 Most likely leader:** `{top['exchange']}`  "
            f"(corr={top['best_corr']:.3f}, lag={top['best_lag']}, p={top['granger_p']:.3f})"
        )
