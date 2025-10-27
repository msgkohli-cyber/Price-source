import streamlit as st

st.set_page_config(page_title="KCEX ↔️ Ourbit Arbitrage Tracker", layout="wide")

st.title("💹 KCEX ↔️ Ourbit Arbitrage Calculator")
st.caption("📊 Manual version (No API needed) — Enter prices manually and see potential profit instantly.")

st.divider()

# Input columns
col1, col2 = st.columns(2)

with col1:
    st.header("KCEX")
    kcex_buy = st.number_input("KCEX Buy Price (USDT)", min_value=0.0, step=0.01, format="%.4f")
    kcex_sell = st.number_input("KCEX Sell Price (USDT)", min_value=0.0, step=0.01, format="%.4f")

with col2:
    st.header("Ourbit")
    ourbit_buy = st.number_input("Ourbit Buy Price (USDT)", min_value=0.0, step=0.01, format="%.4f")
    ourbit_sell = st.number_input("Ourbit Sell Price (USDT)", min_value=0.0, step=0.01, format="%.4f")

st.divider()

# Transaction Fee Input
st.subheader("⚙️ Transaction Fee Setup")
fee_percent = st.number_input("Enter Trading Fee (%) per exchange", value=0.1, step=0.01)

st.divider()

# Arbitrage Calculations
if all([kcex_buy, kcex_sell, ourbit_buy, ourbit_sell]):
    fee = fee_percent / 100

    # Case 1: Buy on KCEX, Sell on Ourbit
    buy_kcex_sell_ourbit = ((ourbit_sell - kcex_buy) / kcex_buy - 2 * fee) * 100

    # Case 2: Buy on Ourbit, Sell on KCEX
    buy_ourbit_sell_kcex = ((kcex_sell - ourbit_buy) / ourbit_buy - 2 * fee) * 100

    st.subheader("📈 Arbitrage Opportunities")
    st.write(f"💰 **Buy on KCEX → Sell on Ourbit:** {buy_kcex_sell_ourbit:.2f}%")
    st.write(f"💰 **Buy on Ourbit → Sell on KCEX:** {buy_ourbit_sell_kcex:.2f}%")

    # Highlight best opportunity
    if buy_kcex_sell_ourbit > buy_ourbit_sell_kcex and buy_kcex_sell_ourbit > 0:
        st.success(f"✅ Best Option: Buy on KCEX and Sell on Ourbit for {buy_kcex_sell_ourbit:.2f}% profit.")
    elif buy_ourbit_sell_kcex > buy_kcex_sell_ourbit and buy_ourbit_sell_kcex > 0:
        st.success(f"✅ Best Option: Buy on Ourbit and Sell on KCEX for {buy_ourbit_sell_kcex:.2f}% profit.")
    else:
        st.warning("⚠️ No profitable arbitrage opportunity at the moment.")
else:
    st.info("Please fill in all price fields to calculate arbitrage opportunities.")
