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
        # --- 既存のフィルター ---
        search_name = st.text_input('踏切名で検索 (部分一致)')
        
        if '線名' in df.columns:
            unique_lines = ['すべて'] + sorted(df['線名'].dropna().astype(str).unique().tolist())
            selected_line = st.selectbox('路線名で絞り込み', unique_lines)
        else:
            selected_line = 'すべて'

        # --- 【追加】新しいフィルター ---
        if '支社名' in df.columns:
            unique_shisha = ['すべて'] + sorted(df['支社名'].dropna().astype(str).unique().tolist())
            selected_shisha = st.selectbox('支社名で絞り込み', unique_shisha)
        else:
            selected_shisha = 'すべて'
            
        if '箇所名（系統名なし）' in df.columns:
            unique_kasho = ['すべて'] + sorted(df['箇所名（系統名なし）'].dropna().astype(str).unique().tolist())
            selected_kasho = st.selectbox('箇所名で絞り込み', unique_kasho)
        else:
            selected_kasho = 'すべて'
            
        if '踏切種別' in df.columns:
            unique_type = ['すべて'] + sorted(df['踏切種別'].dropna().astype(str).unique().tolist())
            selected_type = st.selectbox('踏切種別で絞り込み', unique_type)
        else:
            selected_type = 'すべて'
            
        if '中心位置キロ程' in df.columns:
            # NaNを除外して最小値と最大値を取得
            min_kilo = df['中心位置キロ程'].dropna().min()
            max_kilo = df['中心位置キロ程'].dropna().max()
            
            if pd.notna(min_kilo) and pd.notna(max_kilo) and min_kilo < max_kilo:
                selected_kilo_range = st.slider(
                    '中心位置キロ程で絞り込み',
                    min_value=float(min_kilo),
                    max_value=float(max_kilo),
                    value=(float(min_kilo), float(max_kilo))
                )
            else:
                selected_kilo_range = None # スライダーが作成できない場合はNoneに
        else:
            selected_kilo_range = None

    else:
        st.warning("データを読み込めませんでした。")
        search_name, selected_line, selected_shisha, selected_kasho, selected_type = "", "すべて", "すべて", "すべて", "すべて"
        selected_kilo_range = None

# --- データの絞り込み処理 ---
if not df.empty:
    filtered_df = df.copy()
    # 既存のフィルター
    if search_name and '踏切名' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['踏切名'].notna() & filtered_df['踏切名'].str.contains(search_name, na=False)]
    if selected_line != 'すべて' and '線名' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['線名'] == selected_line]
        
    # 【追加】新しいフィルターでの絞り込み
    if selected_shisha != 'すべて' and '支社名' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['支社名'] == selected_shisha]
    if selected_kasho != 'すべて' and '箇所名（系統名なし）' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['箇所名（系統名なし）'] == selected_kasho]
    if selected_type != 'すべて' and '踏切種別' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['踏切種別'] == selected_type]
    if selected_kilo_range and '中心位置キロ程' in filtered_df.columns:
        # スライダーで選択された範囲でフィルタリングする前に、NaN値を持つ行を除外
        filtered_df = filtered_df.dropna(subset=['中心位置キロ程'])
        filtered_df = filtered_df[
            (filtered_df['中心位置キロ程'] >= selected_kilo_range[0]) &
            (filtered_df['中心位置キロ程'] <= selected_kilo_range[1])
        ]

# --- メイン画面 (地図とデータ表示) ---
if not df.empty and not filtered_df.empty:
    center_lat = filtered_df['Lat'].mean()
    center_lon = filtered_df['Lon'].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

    for idx, row in filtered_df.iterrows():
        if pd.notna(row['Lat']) and pd.notna(row['Lon']):
            # ★★★ 変更点 1: Google Mapのリンクを一般的な形式に修正 ★★★
            gmap_link = f"https://www.google.com/maps?q={row['Lat']},{row['Lon']}"
            
            formatted_kilopost = format_kilopost(row.get('中心位置キロ程'))
            popup_html = f"""
                <b>踏切名:</b> {row.get('踏切名', '名称不明')}<br>
                <b>線名:</b> {row.get('線名', '')}<br>
                <b>キロ程:</b> {formatted_kilopost}<br>
                <a href="{gmap_link}" target="_blank" rel="noopener noreferrer">Google Mapで開く</a>
            """
            tooltip_text = row.get('踏切名', '')
            popup = folium.Popup(popup_html, max_width=300)
            
            # ★★★ 変更点 2: マーカーにアイコンを明示的に指定 ★★★
            folium.Marker(
                location=[row['Lat'], row['Lon']],
                popup=popup,
                tooltip=tooltip_text,
                # Font Awesomeのアイコンを指定 (例: 'train', 'road', 'map-marker' など)
                icon=folium.Icon(color='blue', icon='map-marker', prefix='fa') 
            ).add_to(m)
    
    st_folium(m, width='100%', height=500)

    with st.expander("📥 地図をHTMLファイルとしてダウンロードする"):
        map_html = m._repr_html_()
        st.download_button(
            label="ダウンロード",
            data=map_html,
            file_name="fumikiri_map.html",
            mime="text/html",
        )
    
    st.write(f"表示件数: {len(filtered_df)}件")

    # --- データ一覧をexpander内に配置 ---
    with st.expander("絞り込み結果のデータを表示"):
        # 表示用データフレームの準備
        ideal_display_cols = ['支社名', '箇所名（系統名なし）', '線名', '踏切名', '踏切種別', '中心位置キロ程']
        display_cols = [col for col in ideal_display_cols if col in filtered_df.columns]
        
        if display_cols:
            display_df = filtered_df[display_cols].copy()
            if '中心位置キロ程' in display_df.columns:
                display_df['中心位置キロ程'] = display_df['中心位置キロ程'].apply(format_kilopost)
            st.dataframe(display_df)

elif not df.empty:
    st.warning('指定された条件に一致する踏切はありませんでした。')
