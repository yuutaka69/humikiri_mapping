# app.py
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os

# --- アプリの基本設定 ---
st.set_page_config(layout="wide")
st.title('踏切検索マップ 🗺️')

# --- 中心位置キロ程をカスタム形式に変換する関数 ---
def format_kilopost(value):
    """数値を 'XXkXXX.Xm' 形式の文字列に変換する"""
    if pd.isna(value):
        return ""  # 空白の場合は何も返さない
    try:
        # 念のため数値をfloat型に変換
        value = float(value)
        # キロメートル部分（整数）を取得
        kilo = int(value / 1000)
        # メートル部分（小数点以下含む）を取得
        meter = value % 1000
        # f-stringを使ってフォーマット。メートル部分は5桁でゼロ埋めし、小数点1桁まで表示
        return f"{kilo}k{meter:05.1f}m"
    except (ValueError, TypeError):
        return value  # 変換できない場合は元の値をそのまま返す


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
DATA_PATH = 'data/踏切_緯度経度追加_v5.csv'
df = load_data(DATA_PATH)

# --- サイドバー (検索・フィルター機能) ---
with st.sidebar:
    st.header('検索条件')
    if not df.empty:
        # 踏切名でのテキスト検索
        search_name = st.text_input('踏切名で検索 (部分一致)')
        
        # 【修正点】'線名'列が存在する場合のみフィルターを表示
        if '線名' in df.columns:
            unique_lines = ['すべて'] + sorted(df['線名'].dropna().astype(str).unique().tolist())
            selected_line = st.selectbox('路線で絞り込み', unique_lines)
        else:
            selected_line = 'すべて'
    else:
        st.warning("データを読み込めませんでした。")
        search_name, selected_line = "", "すべて"

# --- データの絞り込み処理 ---
if not df.empty:
    filtered_df = df.copy()
    # '踏切名'列が存在する場合のみ、絞り込み処理を実行
    if search_name and '踏切名' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['踏切名'].notna() & filtered_df['踏切名'].str.contains(search_name, na=False)]
    
    # 【修正点】'線名'列で絞り込み
    if selected_line != 'すべて' and '線名' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['線名'] == selected_line]

# --- メイン画面 (地図とデータ表示) ---
if not df.empty and not filtered_df.empty:
    center_lat = filtered_df['Lat'].mean()
    center_lon = filtered_df['Lon'].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

    for idx, row in filtered_df.iterrows():
        if pd.notna(row['Lat']) and pd.notna(row['Lon']):
            # 【修正点】 .get() を使って安全に列データにアクセスする
            popup_text = f"{row.get('踏切名', '名称不明')} ({row.get('線名', '')})"
            tooltip_text = row.get('踏切名', '')
            
            folium.Marker(
                [row['Lat'], row['Lon']],
                popup=popup_text,
                tooltip=tooltip_text
            ).add_to(m)
    
    st_folium(m, width='100%', height=500)
    
    st.write(f"表示件数: {len(filtered_df)}件")

    # --- 表示用データフレームの準備 ---
    # 【修正点】 表示したい列のうち、実際にデータフレームに存在する列だけを抽出
    ideal_display_cols = ['線名', '踏切名', '中心位置キロ程']
    display_cols = [col for col in ideal_display_cols if col in filtered_df.columns]
    
    if display_cols:
        display_df = filtered_df[display_cols].copy()
        
        # '中心位置キロ程'列が存在すればフォーマットを適用
        if '中心位置キロ程' in display_df.columns:
            display_df['中心位置キロ程'] = display_df['中心位置キロ程'].apply(format_kilopost)
        
        # データフレームを表示
        st.dataframe(display_df)

elif not df.empty:
    st.warning('指定された条件に一致する踏切はありませんでした。')
