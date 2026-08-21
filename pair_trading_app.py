import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from SmartApi import SmartConnect
import pyotp
import os
from numpy.linalg import lstsq
from statsmodels.tsa.stattools import adfuller

st.set_page_config(page_title='AlphaPairs', page_icon='📈', layout='wide')

# Hide Streamlit branding and GitHub link
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.viewerBadge_container__1QSob {display: none !important;}
.styles_viewerBadge__1yB5_ {display: none !important;}
[data-testid='stToolbar'] {display: none !important;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
st.markdown('<h1 style="text-align:center; color:#1f77b4;">AlphaPairs</h1>', unsafe_allow_html=True)
st.markdown('<h4 style="text-align:center; color:#444444;"><i>Find the Divergence. Capture the Convergence.</i></h4>', unsafe_allow_html=True)
st.markdown('<h5 style="text-align:center; color:gray;">Statistical Pair Trading — OLS | ADF | ECM | Cointegration | Live Angel One Data</h5>', unsafe_allow_html=True)
st.markdown('<h5 style="text-align:center; color:gray;">Powered by OLS Regression | ADF Test | ECM | Live Angel One Data</h5>', unsafe_allow_html=True)
if 'show_guide' not in st.session_state:
    st.session_state.show_guide = True
    st.session_state.show_guide = True

col_guide = st.columns([8, 1])
with col_guide[1]:
    if st.button('📖 Guide'):
        st.session_state.show_guide = True


@st.dialog('Welcome to AlphaPairs 📈', width='large')
def show_guide_modal():
    st.markdown('<p style="font-size:16px;">A <b>Quantitative Pair Trading Platform</b> analysing <b>204 NSE F&O stocks</b> with live Angel One signals.</p>', unsafe_allow_html=True)
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('**📊 Live Signals**')
        st.markdown('Active BUY/SELL signals with sector filters and live prices.')
    with c2:
        st.markdown('**🔍 Pair Analysis**')
        st.markdown('Charts, Z-Score history, trade levels and risk calculator.')
    with c3:
        st.markdown('**📋 All Pairs**')
        st.markdown('222 validated pairs that passed 6 statistical tests.')
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('**🚦 Signals**')
        st.success('BUY — Z-Score < -2')
        st.error('SELL — Z-Score > 2')
        st.warning('CAUTION — Z-Score > 3')
        st.info('NO TRADE — Z-Score between ±2')
    with c2:
        st.markdown('**📌 How to Trade**')
        st.markdown('1. Open **Live Signals** tab\n2. Check **Same Sector** filter\n3. Analyse pair in **Pair Analysis**\n4. Enter at Z-Score **±2**\n5. Exit at Z-Score **0**\n6. Stop Loss at Z-Score **±3**')
    st.divider()
    st.markdown('**🔬 Tests:** Correlation | Cointegration | OLS | ADF | Half Life | ECM')
    st.markdown('**📡 Data:** Yahoo Finance | Angel One API | NSE India | NSE Nifty 500')
    st.divider()
    st.success('💡 Pro Tip: Always select SAME SECTOR pairs for more accurate trades!')
    st.error('⚠️ DISCLAIMER: For EDUCATIONAL PURPOSE only. NOT financial advice. Consult SEBI registered advisor.')
    st.info('✖️ Click X on top right to close.')

if st.session_state.show_guide:
    show_guide_modal()
    st.session_state.show_guide = False

# Load data
@st.cache_data(ttl=3600)
def load_data():
    import io
    def load_gdrive(file_id, index_col=None, parse_dates=False):
        url = f'https://drive.google.com/uc?export=download&id={file_id}'
        return pd.read_csv(url, index_col=index_col, parse_dates=parse_dates)
    daily_prices = load_gdrive('1OYaAmKCCwFD4QR4OSR013bDfdYpSasEW', index_col=0, parse_dates=True)
    intraday_prices = load_gdrive('1gHtG4HylRb25nhaRi41cINk4TxlIkeJO', index_col=0, parse_dates=True)
    analysis_df = load_gdrive('1ogtOX5ysseqMExYmJugSHMu8crU3LPPK')
    analysis_df = analysis_df[analysis_df['Same Sector']==True]
    return daily_prices, intraday_prices, analysis_df

daily_prices, intraday_prices, analysis_df = load_data()

# Angel One Connection
try:
    API_KEY = st.secrets['ANGEL_API_KEY']
    CLIENT_ID = st.secrets['ANGEL_CLIENT_ID']
    PASSWORD = st.secrets['ANGEL_PASSWORD']
    TOTP_KEY = st.secrets['ANGEL_TOTP_KEY']
except:
    API_KEY = os.environ.get('ANGEL_API_KEY', '')
    CLIENT_ID = os.environ.get('ANGEL_CLIENT_ID', '')
    PASSWORD = os.environ.get('ANGEL_PASSWORD', '')
    TOTP_KEY = os.environ.get('ANGEL_TOTP_KEY', '')

@st.cache_resource
def load_instruments():
    import requests
    return pd.DataFrame(requests.get('https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json').json())

instruments = load_instruments()

@st.cache_resource(ttl=3600)
def connect_angel():
    try:
        import time
        time.sleep(1)
        totp = pyotp.TOTP(TOTP_KEY).now()
        obj = SmartConnect(api_key=API_KEY)
        data = obj.generateSession(CLIENT_ID, PASSWORD, totp)
        if data['status']:
            return obj
    except Exception as e:
        st.warning(f'Angel One connection failed: {e}')
    return None

angel_obj = connect_angel()

def get_token(symbol):
    result = instruments[(instruments['symbol'] == symbol + '-EQ') & (instruments['exch_seg'] == 'NSE')]
    return result.iloc[0]['token'] if len(result) > 0 else None

def get_live_price(symbol):
    try:
        import time
        time.sleep(0.3)
        if angel_obj:
            token = get_token(symbol)
            if token:
                data = angel_obj.ltpData('NSE', symbol + '-EQ', token)
                if data['status']:
                    return data['data']['ltp']
    except:
        pass
    return None

# Tabs
tab1, tab2, tab3 = st.tabs(['Live Signals', 'Pair Analysis', 'All Pairs'])

with tab1:
    st.markdown('<h2 style="text-align:center;">Live Trading Signals</h2>', unsafe_allow_html=True)
    st.divider()
    all_sectors = ['All Sectors'] + sorted(list(set(list(analysis_df['Sector 1'].unique()) + list(analysis_df['Sector 2'].unique()))))
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        selected_sector = st.selectbox('Filter by Sector', all_sectors)
    with fc2:
        min_corr = st.slider('Min Correlation', 0.70, 0.99, 0.80)
    with fc3:
        if st.button('Refresh Signals'):
            st.cache_data.clear()
            st.rerun()
    st.markdown(f'<p style="color:gray;">Last Updated: {datetime.now().strftime("%d %b %Y %I:%M %p")}</p>', unsafe_allow_html=True)
    filtered = analysis_df[(analysis_df['Stationary']=='YES') & (analysis_df['Signal']!='NO TRADE') & (analysis_df['Signal']!='N/A') & (analysis_df['Correlation'] >= min_corr)]
    if selected_sector != 'All Sectors':
        filtered = filtered[(filtered['Sector 1']==selected_sector) | (filtered['Sector 2']==selected_sector)]
    active = filtered
    # Recalculate live Z-Score for all pairs
    live_results = []
    for _, row in filtered.iterrows():
        s1 = row['Stock 1']
        s2 = row['Stock 2']
        p1 = get_live_price(s1)
        p2 = get_live_price(s2)
        if p1 and p2:
            hr = row['Hedge Ratio']
            spread = daily_prices[s1] - hr * daily_prices[s2]
            live_spread = p1 - hr * p2
            live_z = round((live_spread - spread.mean()) / spread.std(), 2)
            if live_z > 3: signal = 'CAUTION'
            elif live_z > 2: signal = 'SELL'
            elif live_z < -3: signal = 'CAUTION'
            elif live_z < -2: signal = 'BUY'
            else: signal = 'NO TRADE'
            row = row.copy()
            row['Live Z'] = live_z
            row['Signal'] = signal
        live_results.append(row)
    if live_results:
        active = pd.DataFrame(live_results)
        active = active[active['Signal']!='NO TRADE']
    else:
        active = filtered[filtered['Signal']!='NO TRADE']
    # Recalculate live Z-Score for all pairs
    live_results = []
    for _, row in filtered.iterrows():
        s1 = row['Stock 1']
        s2 = row['Stock 2']
        p1 = get_live_price(s1)
        p2 = get_live_price(s2)
        if p1 and p2:
            hr = row['Hedge Ratio']
            spread = daily_prices[s1] - hr * daily_prices[s2]
            live_spread = p1 - hr * p2
            live_z = round((live_spread - spread.mean()) / spread.std(), 2)
            if live_z > 3: signal = 'CAUTION'
            elif live_z > 2: signal = 'SELL'
            elif live_z < -3: signal = 'CAUTION'
            elif live_z < -2: signal = 'BUY'
            else: signal = 'NO TRADE'
            row = row.copy()
            row['Live Z'] = live_z
            row['Signal'] = signal
        live_results.append(row)
    if live_results:
        active = pd.DataFrame(live_results)
        active = active[active['Signal']!='NO TRADE']
    else:
        active = filtered[filtered['Signal']!='NO TRADE']
    buy_signals = active[active['Signal']=='BUY'].sort_values('Live Z')
    sell_signals = active[active['Signal']=='SELL'].sort_values('Live Z', ascending=False)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric('Total Valid Pairs', len(analysis_df[analysis_df['Stationary']=='YES']))
    with col2:
        st.metric('Active BUY Signals', len(buy_signals))
    with col3:
        st.metric('Active SELL Signals', len(sell_signals))
    with col4:
        st.metric('Last Updated', datetime.now().strftime('%H:%M:%S'))
    st.divider()
    bc, sc = st.columns(2)
    with bc:
        st.markdown('<h3 style="color:green;">BUY Signals</h3>', unsafe_allow_html=True)
        for _, row in buy_signals.iterrows():
            same = 'Same Sector' if row['Same Sector'] else 'Diff Sector'
            st.success(f"{row['Stock 1']} ({row['Sector 1']}) vs {row['Stock 2']} ({row['Sector 2']}) | {same} | Corr: {row['Correlation']} | Z: {row['Live Z']} | HL: {row['Half Life']}d | ADF: {row['ADF P-Val']}")
    with sc:
        st.markdown('<h3 style="color:red;">SELL Signals</h3>', unsafe_allow_html=True)
        caution_signals = active[active['Signal']=='CAUTION']
        for _, row in sell_signals.iterrows():
            same = 'Same Sector' if row['Same Sector'] else 'Diff Sector'
            st.error(f"{row['Stock 1']} ({row['Sector 1']}) vs {row['Stock 2']} ({row['Sector 2']}) | {same} | Corr: {row['Correlation']} | Z: {row['Live Z']} | HL: {row['Half Life']}d | ADF: {row['ADF P-Val']}")
        if len(caution_signals) > 0:
            st.markdown('<h3 style="color:darkorange;">⚠️ CAUTION Signals</h3>', unsafe_allow_html=True)
            for _, row in caution_signals.iterrows():
                same = 'Same Sector' if row['Same Sector'] else 'Diff Sector'
                st.warning(f"{row['Stock 1']} ({row['Sector 1']}) vs {row['Stock 2']} ({row['Sector 2']}) | {same} | Z: {row['Live Z']} — Beyond Stop Loss! Consider Exiting!")

with tab2:
    st.markdown('<h2 style="text-align:center;">Pair Analysis</h2>', unsafe_allow_html=True)
    st.divider()
    valid_pairs = analysis_df[analysis_df['Stationary']=='YES']
    pair_options = [f"{r['Stock 1']} vs {r['Stock 2']}" for _, r in valid_pairs.iterrows()]
    selected_pair = st.selectbox('Select Pair to Analyse', pair_options)
    if selected_pair:
        stock1 = selected_pair.split(' vs ')[0]
        stock2 = selected_pair.split(' vs ')[1]
        pair_data = valid_pairs[(valid_pairs['Stock 1']==stock1) & (valid_pairs['Stock 2']==stock2)].iloc[0]
        # Pair Summary Card
        corr = pair_data['Correlation']
        adf = pair_data['ADF P-Val']
        hl = pair_data['Half Life']
        live_z = pair_data['Live Z']
        signal = pair_data['Signal']
        coint_p = pair_data['Coint P-Val']

        # Confidence Level
        score = 0
        if corr > 0.90: score += 3
        elif corr > 0.80: score += 2
        else: score += 1
        if adf < 0.01: score += 3
        elif adf < 0.05: score += 2
        if hl < 15: score += 2
        elif hl < 25: score += 1
        if coint_p < 0.01: score += 2
        elif coint_p < 0.05: score += 1

        if score >= 8: confidence = 'HIGH'
        elif score >= 5: confidence = 'MEDIUM'
        else: confidence = 'LOW'

        if signal == 'BUY':
            action = f'BUY {stock1} futures | SELL {stock2} futures'
            card_color = 'green'
        elif signal == 'SELL':
            action = f'SELL {stock1} futures | BUY {stock2} futures'
            card_color = 'red'
        else:
            action = 'Wait for Z-Score to cross +2 or -2'
            card_color = 'orange'

        st.markdown(f"""
        <div style='background-color:#f0f2f6; padding:20px; border-radius:10px; border-left:5px solid {card_color};'>
        <h3 style='color:{card_color};'>{stock1} vs {stock2} — {signal}</h3>
        <p><b>Action:</b> {action}</p>
        <p><b>Confidence:</b> {confidence} ({score}/10)</p>
        <p><b>Live Z-Score:</b> {live_z} | <b>Half Life:</b> {hl} days | <b>Correlation:</b> {corr}</p>
        <p><b>ADF P-Value:</b> {adf} | <b>Cointegration P-Value:</b> {coint_p}</p>
        </div>
        """, unsafe_allow_html=True)
        st.divider()
        m1, m2, m3, m4, m5 = st.columns(5)
        with m1:
            st.metric('Correlation', pair_data['Correlation'])
        with m2:
            st.metric('Hedge Ratio', pair_data['Hedge Ratio'])
            st.caption(f"For every 1 lot of {stock1}, trade {pair_data['Hedge Ratio']} lots of {stock2}")
        with m3:
            st.metric('Half Life', str(pair_data['Half Life']) + ' days')
            st.caption(f"Spread takes ~{pair_data['Half Life']} days to revert halfway to mean")
        with m4:
            # Calculate live Z-Score
            live_p1 = get_live_price(stock1)
            live_p2 = get_live_price(stock2)
            hedge_ratio = pair_data['Hedge Ratio']
            spread = daily_prices[stock1] - hedge_ratio * daily_prices[stock2]
            if live_p1 and live_p2:
                live_spread = live_p1 - hedge_ratio * live_p2
                live_z = round((live_spread - spread.mean()) / spread.std(), 2)
                if live_z > 3: live_signal = 'CAUTION'
                elif live_z > 2: live_signal = 'SELL'
                elif live_z < -3: live_signal = 'CAUTION'
                elif live_z < -2: live_signal = 'BUY'
                else: live_signal = 'NO TRADE'
            else:
                live_z = pair_data['Live Z']
                live_signal = pair_data['Signal']
            st.metric('Live Z-Score', live_z)
        with m5:
            if live_signal == 'BUY':
                st.markdown('<h3 style="color:green;">BUY</h3>', unsafe_allow_html=True)
            elif live_signal == 'SELL':
                st.markdown('<h3 style="color:red;">SELL</h3>', unsafe_allow_html=True)
            elif live_signal == 'CAUTION':
                st.markdown('<h3 style="color:darkorange;">⚠️ CAUTION — Beyond Stop Loss!</h3>', unsafe_allow_html=True)
            else:
                st.markdown('<h3 style="color:gray;">NO TRADE</h3>', unsafe_allow_html=True)
        st.divider()
        hedge_ratio = pair_data['Hedge Ratio']
        spread = daily_prices[stock1] - hedge_ratio * daily_prices[stock2]
        zscore = (spread - spread.mean()) / spread.std()







        # Row 1 - Normalised Price (full width)
        norm1 = (daily_prices[stock1] / daily_prices[stock1].iloc[0]) * 100
        norm2 = (daily_prices[stock2] / daily_prices[stock2].iloc[0]) * 100
        fig2b = go.Figure()
        fig2b.add_trace(go.Scatter(x=daily_prices.index, y=norm1, name=stock1, line=dict(color='blue', width=1.5)))
        fig2b.add_trace(go.Scatter(x=daily_prices.index, y=norm2, name=stock2, line=dict(color='red', width=1.5)))
        fig2b.add_hline(y=100, line_dash='dash', line_color='gray')
        fig2b.update_layout(title=f'Normalised Price (Base=100) — {stock1} vs {stock2}', xaxis_title='Date', yaxis_title='Normalised Price', height=400)
        st.plotly_chart(fig2b, use_container_width=True, key='norm_price_chart')
        st.divider()
        # Row 2 - Log Spread + Z-Score side by side
        pc1, pc2 = st.columns(2)
        with pc1:
            fig2 = go.Figure()
            log_p1 = np.log(daily_prices[stock1])
            log_p2 = np.log(daily_prices[stock2])
            log_spread = log_p1 - hedge_ratio * log_p2
            fig2.add_trace(go.Scatter(x=daily_prices.index, y=log_spread, name='Log Spread', line=dict(color='purple', width=1.5)))
            fig2.add_hline(y=log_spread.mean(), line_dash='dash', line_color='gray', annotation_text='Mean')
            fig2.add_hline(y=log_spread.mean() + 2*log_spread.std(), line_dash='dash', line_color='red', annotation_text='+2 SD')
            fig2.add_hline(y=log_spread.mean() - 2*log_spread.std(), line_dash='dash', line_color='green', annotation_text='-2 SD')
            fig2.update_layout(title=f'Log Price Spread — {stock1} vs {stock2}', xaxis_title='Date', yaxis_title='Log Spread', height=400)
            st.plotly_chart(fig2, use_container_width=True, key='price_chart')
        with pc2:
            # Calculate historical signals
            buy_signals_hist = zscore[zscore < -2]
            sell_signals_hist = zscore[zscore > 2]
            exit_signals = zscore[(zscore.shift(1) > 2) & (zscore <= 2) | (zscore.shift(1) < -2) & (zscore >= -2)]
            fig_z = go.Figure()
            fig_z.add_trace(go.Scatter(x=zscore.index, y=zscore, mode='lines', name='Z-Score', line=dict(color='blue', width=1.5)))
            fig_z.add_trace(go.Scatter(x=buy_signals_hist.index, y=buy_signals_hist, mode='markers', name='BUY Signal', marker=dict(color='green', size=8, symbol='triangle-up')))
            fig_z.add_trace(go.Scatter(x=sell_signals_hist.index, y=sell_signals_hist, mode='markers', name='SELL Signal', marker=dict(color='red', size=8, symbol='triangle-down')))
            fig_z.add_trace(go.Scatter(x=exit_signals.index, y=exit_signals, mode='markers', name='EXIT Signal', marker=dict(color='orange', size=8, symbol='circle')))
            fig_z.add_hline(y=2, line_dash='dash', line_color='red', annotation_text='Sell Zone')
            fig_z.add_hline(y=-2, line_dash='dash', line_color='green', annotation_text='Buy Zone')
            fig_z.add_hline(y=3, line_dash='dot', line_color='darkred', annotation_text='Stop Loss')
            fig_z.add_hline(y=-3, line_dash='dot', line_color='darkgreen', annotation_text='Stop Loss')
            fig_z.add_hline(y=0, line_dash='dash', line_color='gray', annotation_text='Exit')
            fig_z.update_layout(
                title=f'Z-Score with Historical Signals — {stock1} vs {stock2}',
                xaxis_title='Date',
                yaxis_title='Z-Score',
                height=400,
                legend=dict(x=0, y=1)
            )
            st.plotly_chart(fig_z, use_container_width=True, key='zscore_chart')
            buy_count = len(buy_signals_hist)
            sell_count = len(sell_signals_hist)
            st.caption(f'Historical Signals — BUY: {buy_count} times | SELL: {sell_count} times')
        st.divider()
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=spread.index, y=spread, mode='lines', name='Spread', line=dict(color='purple')))
        fig3.add_hline(y=spread.mean(), line_dash='dash', line_color='gray', annotation_text='Mean')
        fig3.add_hline(y=spread.mean() + 2*spread.std(), line_dash='dash', line_color='red', annotation_text='Sell Level')
        fig3.add_hline(y=spread.mean() - 2*spread.std(), line_dash='dash', line_color='green', annotation_text='Buy Level')
        fig3.update_layout(title=f'Spread Chart — {stock1} vs {stock2}', xaxis_title='Date', yaxis_title='Spread')
        st.plotly_chart(fig3, use_container_width=True, key='spread_chart')
        st.divider()
        st.subheader('Trade Action Card')
        live_p1 = get_live_price(stock1)
        live_p2 = get_live_price(stock2)
        spread_mean = round(spread.mean(), 2)
        spread_std = round(spread.std(), 2)
        current_spread = round(spread.iloc[-1], 2)
        entry_sell = round(spread_mean + 2*spread_std, 2)
        entry_buy = round(spread_mean - 2*spread_std, 2)
        stop_loss_sell = round(spread_mean + 3*spread_std, 2)
        stop_loss_buy = round(spread_mean - 3*spread_std, 2)

        # Determine card color and action
        if live_signal == 'BUY':
            card_color = '#1a7a1a'
            action_text = f'BUY {stock1} Futures | SELL {stock2} Futures'
            stop_loss_level = '-3.0'
            stop_loss_spread = stop_loss_buy
            reward = round(abs(current_spread - spread_mean) * 1, 2)
            risk = round(abs(spread_std), 2)
        elif live_signal == 'SELL':
            card_color = '#7a1a1a'
            action_text = f'SELL {stock1} Futures | BUY {stock2} Futures'
            stop_loss_level = '+3.0'
            stop_loss_spread = stop_loss_sell
            reward = round(abs(current_spread - spread_mean) * 1, 2)
            risk = round(abs(spread_std), 2)
        elif live_signal == 'CAUTION':
            card_color = '#7a4a00'
            action_text = f'CAUTION — Beyond Stop Loss! Avoid new trades!'
            stop_loss_level = '±3.0'
            stop_loss_spread = 'N/A'
            reward = 0
            risk = 0
        else:
            card_color = '#1a3a7a'
            action_text = f'Wait for Z-Score to cross ±2'
            stop_loss_level = '±3.0'
            stop_loss_spread = 'N/A'
            reward = 0
            risk = 0

        rr_ratio = round(reward / risk, 2) if risk > 0 else 0
        half_life_val = pair_data['Half Life']

        st.markdown(f"""
        <div style='background-color:#1a1a2e; padding:20px; border-radius:12px; border-left:6px solid {card_color};'>
        <h3 style='color:{card_color}; margin:0;'>{live_signal} SIGNAL — {stock1} vs {stock2}</h3>
        <hr style='border-color:#333; margin:10px 0;'>
        <table style='width:100%; color:white; font-size:16px;'>
        <tr><td style='padding:5px;'>📌 <b>ACTION</b></td><td style='padding:5px; color:{card_color};'><b>{action_text}</b></td></tr>
        <tr><td style='padding:5px;'>📊 <b>LIVE Z-SCORE</b></td><td style='padding:5px;'>{live_z} (Signal Active!)</td></tr>
        <tr><td style='padding:5px;'>💰 <b>LIVE PRICES</b></td><td style='padding:5px;'>{stock1}: ₹{live_p1} | {stock2}: ₹{live_p2}</td></tr>
        <tr><td style='padding:5px;'>🎯 <b>ENTER</b></td><td style='padding:5px;'>Now — Z already crossed ±2</td></tr>
        <tr><td style='padding:5px;'>✅ <b>EXIT</b></td><td style='padding:5px;'>When Z returns to 0 (~{half_life_val} days)</td></tr>
        <tr><td style='padding:5px;'>🛑 <b>STOP LOSS</b></td><td style='padding:5px;'>If Z crosses {stop_loss_level} — Exit Immediately!</td></tr>
        </table>
        </div>
        """, unsafe_allow_html=True)
        st.divider()
        st.subheader('Risk Calculator')
        import json, requests
        lot_url = 'https://drive.google.com/uc?export=download&id=1zSbXdw7Qg4GkpWkfg9bA55qTI9n6oXXA'
        lot_sizes = requests.get(lot_url).json()
        default_lot1 = int(lot_sizes.get(stock1, 100))
        default_lot2 = int(lot_sizes.get(stock2, 100))
        rc1, rc2 = st.columns(2)
        with rc1:
            st.info(f'NSE Lot Size for {stock1}: {default_lot1}')
            lot_size1 = st.number_input(f'{stock1} Lots to Trade', min_value=1, value=1, step=1)
            total_units1 = lot_size1 * default_lot1
            st.caption(f'Total units: {total_units1}')
        with rc2:
            st.info(f'NSE Lot Size for {stock2}: {default_lot2}')
            lot_size2 = st.number_input(f'{stock2} Lots to Trade', min_value=1, value=1, step=1)
            total_units2 = lot_size2 * default_lot2
            st.caption(f'Total units: {total_units2}')
        current_signal = pair_data['Signal']
        if current_signal == 'SELL':
            entry_spread = entry_sell
            sl_spread = stop_loss_sell
            target_spread = spread_mean
        else:
            entry_spread = entry_buy
            sl_spread = stop_loss_buy
            target_spread = spread_mean
        risk_per_unit = abs(entry_spread - sl_spread)
        reward_per_unit = abs(entry_spread - target_spread)
        risk_lots = round(risk_per_unit * lot_size1, 2)
        reward_lots = round(reward_per_unit * lot_size1, 2)
        rr_ratio = round(reward_per_unit / risk_per_unit, 2) if risk_per_unit > 0 else 0
        r1, r2, r3, r4, r5 = st.columns(5)
        with r1:
            st.metric('Entry Spread', round(entry_spread, 2))
        with r2:
            st.metric('Stop Loss Spread', round(sl_spread, 2))
        with r3:
            st.metric('Target Spread', round(target_spread, 2))
        with r4:
            st.metric('Risk Per Lot', 'Rs ' + str(risk_lots))
        with r5:
            st.metric('Reward Per Lot', 'Rs ' + str(reward_lots))
        if rr_ratio >= 2:
            rr_color = 'green'
        elif rr_ratio >= 1:
            rr_color = 'orange'
        else:
            rr_color = 'red'
        st.markdown(f'<h4>Risk/Reward Ratio: <span style="color:{rr_color};">{rr_ratio}</span></h4>', unsafe_allow_html=True)
        if rr_ratio >= 2:
            st.success('Good Risk/Reward — Trade looks favorable!')
        elif rr_ratio >= 1:
            st.warning('Moderate Risk/Reward — Trade with caution!')
        else:
            st.error('Poor Risk/Reward — Avoid this trade!')
        st.divider()
        st.subheader('Live Prices')
        lp1, lp2 = st.columns(2)
        with lp1:
            st.metric(stock1 + ' Live Price', 'Rs ' + str(live_p1) if live_p1 else 'N/A')
        with lp2:
            st.metric(stock2 + ' Live Price', 'Rs ' + str(live_p2) if live_p2 else 'N/A')

with tab3:
    st.markdown('<h2 style="text-align:center;">All Valid Pairs</h2>', unsafe_allow_html=True)
    st.divider()
    display_df = analysis_df[analysis_df['Stationary']=='YES'].sort_values('Live Z', key=abs, ascending=False).reset_index(drop=True)
    display_df.index = display_df.index + 1
    st.dataframe(display_df, use_container_width=True)

st.divider()
st.markdown('<h4 style="text-align:center; color:gray;">© 2026 AlphaPairs | Built by Shashank Agarwal | Data: Angel One & Yahoo Finance | All Rights Reserved</h4>', unsafe_allow_html=True)
