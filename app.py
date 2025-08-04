# app.py
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os

# --- アプリの基本設定 ---
st.set_page_config(layout="wide")
st.title('踏切検索マップ 🗺️')

# --- データ読み込み ---
# @st.cache_data を使うと、データをキャッシュして2回目以降の読み込みを高速化します
@st.cache_data
def load_data(file_path):
    # GitHubリポジトリ内の相対パスからファイルを読み込む
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    else:
        st.error(f"データファイルが見つかりません: {file_path}")
        st.error("リポジトリの 'data' フォルダにCSVファイルが正しく配置されているか確認してください。")
        return pd.DataFrame()

# dataフォルダ内のCSVファイルを指定
DATA_PATH = 'data/踏切_全社_緯度経度追加_v2.csv' 
df = load_data(DATA_PATH)

# --- サイドバー (検索・フィルター機能) ---
with st.sidebar:
    st.header('検索条件')
    if not df.empty:
        # 踏切名でのテキスト検索
        search_name = st.text_input('踏切名で検索 (部分一致)')
        
        # 路線名での選択フィルター
        unique_lines = ['すべて'] + sorted(df['線名コード'].dropna().astype(str).unique().tolist())
        selected_line = st.selectbox('路線で絞り込み', unique_lines)
    else:
        st.warning("データを読み込めませんでした。")
        search_name, selected_line = "", "すべて"

# --- データの絞り込み処理 ---
if not df.empty:
    filtered_df = df.copy()
    if search_name:
        filtered_df = filtered_df[filtered_df['踏切名称'].notna() & filtered_df['踏切名称'].str.contains(search_name, na=False)]
    if selected_line != 'すべて':
        filtered_df = filtered_df[filtered_df['線名コード'] == selected_line]

# --- メイン画面 (地図とデータ表示) ---
if not df.empty and not filtered_df.empty:
    center_lat = filtered_df['Lat'].mean()
    center_lon = filtered_df['Lon'].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

    for idx, row in filtered_df.iterrows():
        if pd.notna(row['Lat']) and pd.notna(row['Lon']):
            folium.Marker(
                [row['Lat'], row['Lon']],
                popup=f"{row['踏切名称']} ({row['線名コード']})",
                tooltip=row['踏切名称']
            ).add_to(m)
    
    st_folium(m, width='100%', height=500)
    
    st.write(f"表示件数: {len(filtered_df)}件")
    display_cols = ['線名コード', '踏切名称', '中心位置キロ程', '誤差(m)', 'マッチング線別コード']
    st.dataframe(filtered_df[[col for col in display_cols if col in filtered_df.columns]])
elif not df.empty:
    st.warning('指定された条件に一致する踏切はありませんでした。')
