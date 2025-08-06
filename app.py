import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Search
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
        value = float(value)
        kilo = int(value / 1000)
        meter = value % 1000
        return f"{kilo}k{meter:05.1f}m"
    except (ValueError, TypeError):
        return value

# --- データ読み込み ---
@st.cache_data
def load_data(file_path):
    if os.path.exists(file_path):
        try:
            return pd.read_csv(file_path)
        except Exception as e:
            st.error(f"CSVファイルの読み込み中にエラーが発生しました: {e}")
            return pd.DataFrame()
    else:
        st.error(f"データファイルが見つかりません: {file_path}")
        st.error("リポジトリの 'data' フォルダにCSVファイルが正しく配置されているか確認してください。")
        return pd.DataFrame()

# --- ★★★【新規追加】検索機能付きHTMLを生成する関数 ★★★ ---
def create_searchable_map_html(df):
    """
    検索プラグインとマーカークラスターを含むFoliumマップのHTMLを生成する。
    """
    if df.empty:
        return "<h1>データがありません。</h1>"

    # 地図の中心を計算
    center_lat = df['Lat'].mean()
    center_lon = df['Lon'].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=10)

    # マーカークラスターを作成して地図に追加
    # 大量のマーカーをすっきりと表示できる
    marker_cluster = MarkerCluster().add_to(m)

    # データフレームをループしてマーカーをクラスターに追加
    for idx, row in df.iterrows():
        if pd.notna(row['Lat']) and pd.notna(row['Lon']):
            gmap_link = f"https://www.google.com/maps?q={row['Lat']},{row['Lon']}"
            formatted_kilopost = format_kilopost(row.get('中心位置キロ程'))
            popup_html = f"""
                <b>踏切名:</b> {row.get('踏切名', '名称不明')}<br>
                <b>線名:</b> {row.get('線名', '')}<br>
                <b>キロ程:</b> {formatted_kilopost}<br>
                <a href="{gmap_link}" target="_blank" rel="noopener noreferrer">Google Mapで開く</a>
            """
            popup = folium.Popup(popup_html, max_width=300)
            
            # 検索プラグインはtooltipの値を検索対象にする
            tooltip_text = row.get('踏切名', '名称不明')
            
            folium.Marker(
                location=[row['Lat'], row['Lon']],
                popup=popup,
                tooltip=tooltip_text,
                icon=folium.Icon(color='blue', icon='train', prefix='fa')
            ).add_to(marker_cluster) # マーカーを直接地図ではなく、クラスターに追加

    # 検索プラグインを追加
    # layer: 検索対象のレイヤー (ここではmarker_cluster)
    # search_label: 検索対象のプロパティ名 (MarkerClusterの場合はtooltipが使われるため'title'を指定)
    # placeholder: 検索ボックスのプレースホルダーテキスト
    search = Search(
        layer=marker_cluster,
        search_label="title", # Markerのtooltipは内部的にtitleとして扱われる
        placeholder='踏切名で検索...',
        collapsed=False, # 最初から検索ボックスを開いておく
        position='topright'
    ).add_to(m)

    # HTMLとして表現された地図オブジェクトを返す
    return m._repr_html_()


# --- データファイルのパス ---
DATA_PATH = 'data/踏切_緯度経度追加_v5.csv'
df = load_data(DATA_PATH)

# --- サイドバー (検索・フィルター機能) ---
with st.sidebar:
    st.header('検索条件')
    if not df.empty:
        search_name = st.text_input('踏切名で検索 (部分一致)')
        
        unique_lines = ['すべて'] + sorted(df['線名'].dropna().astype(str).unique().tolist())
        selected_line = st.selectbox('路線名で絞り込み', unique_lines)

        unique_shisha = ['すべて'] + sorted(df['支社名'].dropna().astype(str).unique().tolist())
        selected_shisha = st.selectbox('支社名で絞り込み', unique_shisha)
        
        unique_kasho = ['すべて'] + sorted(df['箇所名（系統名なし）'].dropna().astype(str).unique().tolist())
        selected_kasho = st.selectbox('箇所名で絞り込み', unique_kasho)
        
        unique_type = ['すべて'] + sorted(df['踏切種別'].dropna().astype(str).unique().tolist())
        selected_type = st.selectbox('踏切種別で絞り込み', unique_type)
        
        if '中心位置キロ程' in df.columns:
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
                selected_kilo_range = None
        else:
            selected_kilo_range = None
    else:
        st.warning("データを読み込めませんでした。")
        search_name, selected_line, selected_shisha, selected_kasho, selected_type = "", "すべて", "すべて", "すべて", "すべて"
        selected_kilo_range = None

# --- データの絞り込み処理 ---
filtered_df = pd.DataFrame()
if not df.empty:
    filtered_df = df.copy()
    if search_name:
        filtered_df = filtered_df[filtered_df['踏切名'].notna() & filtered_df['踏切名'].str.contains(search_name, na=False)]
    if selected_line != 'すべて':
        filtered_df = filtered_df[filtered_df['線名'] == selected_line]
    if selected_shisha != 'すべて':
        filtered_df = filtered_df[filtered_df['支社名'] == selected_shisha]
    if selected_kasho != 'すべて':
        filtered_df = filtered_df[filtered_df['箇所名（系統名なし）'] == selected_kasho]
    if selected_type != 'すべて':
        filtered_df = filtered_df[filtered_df['踏切種別'] == selected_type]
    if selected_kilo_range:
        filtered_df = filtered_df.dropna(subset=['中心位置キロ程'])
        filtered_df = filtered_df[
            (filtered_df['中心位置キロ程'] >= selected_kilo_range[0]) &
            (filtered_df['中心位置キロ程'] <= selected_kilo_range[1])
        ]

# --- メイン画面 (地図とデータ表示) ---
if not filtered_df.empty:
    center_lat = filtered_df['Lat'].mean()
    center_lon = filtered_df['Lon'].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

    for idx, row in filtered_df.iterrows():
        if pd.notna(row['Lat']) and pd.notna(row['Lon']):
            gmap_link = f"https://www.google.com/maps?q={row['Lat']},{row['Lon']}"
            formatted_kilopost = format_kilopost(row.get('中心位置キロ程'))
            popup_html = f"""
                <b>踏切名:</b> {row.get('踏切名', '名称不明')}<br>
                <b>線名:</b> {row.get('線名', '')}<br>
                <b>キロ程:</b> {formatted_kilopost}<br>
                <a href="{gmap_link}" target="_blank" rel="noopener noreferrer">Google Mapで開く</a>
            """
            popup = folium.Popup(popup_html, max_width=300)
            tooltip_text = row.get('踏切名', '')
            
            folium.Marker(
                location=[row['Lat'], row['Lon']],
                popup=popup,
                tooltip=tooltip_text,
                icon=folium.Icon(color='blue', icon='train', prefix='fa')
            ).add_to(m)
    
    st_folium(m, width='100%', height=500)

    # --- ダウンロードセクション ---
    st.markdown("---")
    st.subheader("ダウンロードオプション")

    # Ver1: 静的なHTML
    with st.expander("Ver.1 静的な地図をHTMLとしてダウンロード"):
        map_html_static = m._repr_html_()
        st.download_button(
            label="ダウンロード (Ver.1)",
            data=map_html_static,
            file_name="fumikiri_map_static.html",
            mime="text/html",
        )
    
    # ★★★【新規追加】Ver2: 検索機能付きHTML ★★★
    with st.expander("Ver.2 検索機能付きの地図をHTMLとしてダウンロード"):
        # 現在絞り込まれているデータで検索機能付きHTMLを生成
        map_html_searchable = create_searchable_map_html(filtered_df)
        st.download_button(
            label="ダウンロード (Ver.2)",
            data=map_html_searchable,
            file_name="fumikiri_map_searchable.html",
            mime="text/html",
            help="現在絞り込まれている全ての踏切データを含んだ、検索機能付きのHTMLファイルをダウンロードします。"
        )

    st.markdown("---")
    
    st.write(f"表示件数: {len(filtered_df)}件")

    with st.expander("絞り込み結果のデータを表示"):
        ideal_display_cols = ['支社名', '箇所名（系統名なし）', '線名', '踏切名', '踏切種別', '中心位置キロ程']
        display_cols = [col for col in ideal_display_cols if col in df.columns]
        
        if display_cols:
            display_df = filtered_df[display_cols].copy()
            if '中心位置キロ程' in display_df.columns:
                display_df['中心位置キロ程'] = display_df['中心位置キロ程'].apply(format_kilopost)
            st.dataframe(display_df, use_container_width=True)

elif not df.empty:
    st.warning('指定された条件に一致する踏切はありませんでした。')
else:
    # データフレームが最初から空の場合のメッセージ
    st.info("サイドバーで検索条件を指定してください。")
