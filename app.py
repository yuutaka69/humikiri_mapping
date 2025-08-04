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

    # --- 表示用データフレームの準備 ---
    # 表示する列を絞り込む
    display_cols = ['線名コード', '踏切名称', '中心位置キロ程']
    display_df = filtered_df[display_cols].copy()
    
    # 【変更点】キロ程の表示をカスタム形式に変換
    display_df['中心位置キロ程'] = display_df['中心位置キロ程'].apply(format_kilopost)
    
    # データフレームを表示
    st.dataframe(display_df)

elif not df.empty:
    st.warning('指定された条件に一致する踏切はありませんでした。')
```

### 主な変更点

1.  **`format_kilopost`関数を追加**: コードの冒頭に、中心位置キロ程の数値を指定の文字列形式（例: `12k345.6m`）に変換するための関数を定義しました。
2.  **表示用データフレームを準備**: 絞り込み後のデータ(`filtered_df`)から、表示に必要な列だけを抜き出した`display_df`を作成しました。
3.  **フォーマットを適用**: `display_df`の「中心位置キロ程」列に`format_kilopost`関数を適用し、セルの値を新しい表示形式に書き換えています。
4.  **`st.dataframe`の修正**: 最終的に表示するデータフレームを、加工済みの`display_df`に変更しました。

この`app.py`ファイルをGitHubにプッシュすれば、Streamlitアプリに自動で変更が反映され
