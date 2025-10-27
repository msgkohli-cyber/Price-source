import streamlit as st
import pandas as pd
import numpy as np
import ccxt
from statsmodels.tsa.stattools import grangercausalitytests

st.set_page_config(page_title="Price Source Detector", layout="centered")

st.title("🔍 Price Source Detector")
st.markdown("This tool compares live crypto prices between exchanges to detect if one might be following another.")

# --- User Input ---
target_exchange = st.text_input("Target Exchange (e.g. kcex)", value="kcex").lower().strip()
symbol = st.text_input("Coin Symbol (e.g. BTC/USDT)", value="BTC/USDT").upper().strip()
run_btn = st.button("Run Analysis")

# --- Config ---
CHECK_EXCHANGES = ['binance', 'okx', 'kucoin', 'bybit', 'gate', 'bitget', 'mexc', 'bitmart', 'huobi']
TIME_WINDOW_SEC = 180  # 3 minutes
RESAMPLE_FREQ = '1S'

def fetch_prices(exchange, symbol, since):
    try:
        ex = getattr(ccxt, exchange)({'enableRateLimit': True})
        ex.load_markets()
        trades = ex.fetch_trades(symbol, since=since, limit=500)
        if not trades:
            return None
        df = pd.DataFrame(trades)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df.set_index('timestamp')['price'].resample(RESAMPLE_FREQ).last().ffill()
    except Exception:
        return None

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

if run_btn:
    st.info(f"Fetching live data for {symbol} ... please wait up to 1 minute ⏳")

    now = int(ccxt.Exchange.milliseconds(ccxt.Exchange()))
    since = now - TIME_WINDOW_SEC * 1000

    # Target
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
        st.success("✅ Analysis Complete!")
        st.write("**Top likely price sources:**")
        st.dataframe(df[['exchange', 'score', 'best_lag', 'best_corr', 'granger_p']].round(4))
        top = df.iloc[0]
        st.markdown(f"👉 **Most likely price source:** `{top['exchange']}` (lag {top['best_lag']}s, corr {top['best_corr']:.2f})")
