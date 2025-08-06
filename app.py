import streamlit as st
import pandas as pd
import folium
from folium.plugins import Search
from streamlit_folium import st_folium
import os
import json

# --- アプリの基本設定 ---
st.set_page_config(layout="wide")
st.title('踏切検索マップ 🗺️')

# --- 中心位置キロ程をカスタム形式に変換する関数 ---
def format_kilopost(value):
    """数値を 'XXkXXX.Xm' 形式の文字列に変換する"""
    if pd.isna(value):
        return ""
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
            return pd.read_csv(file_path, encoding='utf-8')
        except Exception as e:
            st.error(f"CSVファイルの読み込み中にエラーが発生しました: {e}")
            return pd.DataFrame()
    else:
        st.error(f"データファイルが見つかりません: {file_path}")
        st.error("リポジトリの 'data' フォルダにCSVファイルが正しく配置されているか確認してください。")
        return pd.DataFrame()

# --- ★★★【ロジック改善】多機能フィルター付きHTMLを生成する関数 ★★★ ---
def create_multifilter_map_html(df):
    """
    複数の絞り込みフィルターと検索機能を持つインタラクティブなHTMLを生成する。
    JavaScriptのロジックを改善し、安定性を向上。
    """
    if df.empty:
        return "<h1>表示するデータがありません。</h1>"

    # NaN値を安全な値（空文字）に置換
    df_safe = df.fillna('')

    # 地図の中心を計算
    center_lat = df[df['Lat'].notna()]['Lat'].mean()
    center_lon = df[df['Lon'].notna()]['Lon'].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=10)

    # マーカーを管理するためのFeatureGroupを作成
    marker_group = folium.FeatureGroup(name="FumikiriMarkers", control=False).add_to(m)

    # --- マーカーとデータをJavaScriptで扱えるように準備 ---
    markers_data = []
    for idx, row in df_safe.iterrows():
        if pd.notna(row['Lat']) and pd.notna(row['Lon']):
            # JavaScriptで使うためのデータを整形
            # マーカーの生成はJavaScript側で行うことで効率化
            markers_data.append({
                'lat': row['Lat'],
                'lon': row['Lon'],
                'name': row.get('踏切名', ''),
                'line': row.get('線名', ''),
                'shisha': row.get('支社名', ''),
                'kasho': row.get('箇所名（系統名なし）', ''),
                'type': row.get('踏切種別', ''),
                'popup': f"""
                    <b>踏切名:</b> {row.get('踏切名', '名称不明')}<br>
                    <b>線名:</b> {row.get('線名', '')}<br>
                    <b>キロ程:</b> {format_kilopost(row.get('中心位置キロ程'))}<br>
                    <a href="https://www.google.com/maps?q={row['Lat']},{row['Lon']}" target="_blank" rel="noopener noreferrer">Google Mapで開く</a>
                """
            })

    # --- HTMLに埋め込むCSSとJavaScriptを定義 ---
    js_data = json.dumps(markers_data)

    custom_script_css = f"""
    <style>
        #filter-container {{
            position: fixed;
            top: 10px;
            left: 10px;
            z-index: 1000;
            background-color: white;
            padding: 10px 15px;
            border-radius: 5px;
            box-shadow: 0 0 15px rgba(0,0,0,0.2);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
            width: 260px;
            max-height: 95vh;
            overflow-y: auto;
        }}
        #filter-container h4 {{
            margin-top: 0;
            margin-bottom: 15px;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }}
        .filter-item {{
            margin-bottom: 12px;
        }}
        .filter-item label {{
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            font-size: 14px;
        }}
        .filter-item select, .filter-item input {{
            width: 100%;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid #ccc;
            box-sizing: border-box;
        }}
        #results-count {{
            margin-top: 15px;
            padding-top: 10px;
            border-top: 1px solid #eee;
            font-weight: bold;
        }}
    </style>

    <div id="filter-container">
        <h4>絞り込み検索</h4>
        <div class="filter-item">
            <label for="name-filter">踏切名</label>
            <input type="text" id="name-filter" placeholder="部分一致検索">
        </div>
        <div class="filter-item">
            <label for="line-filter">路線名</label>
            <select id="line-filter"></select>
        </div>
        <div class="filter-item">
            <label for="shisha-filter">支社名</label>
            <select id="shisha-filter"></select>
        </div>
        <div class="filter-item">
            <label for="kasho-filter">箇所名</label>
            <select id="kasho-filter"></select>
        </div>
        <div class="filter-item">
            <label for="type-filter">踏切種別</label>
            <select id="type-filter"></select>
        </div>
        <div id="results-count"></div>
    </div>

    <script>
    //DOMContentLoadedがfoliumのmap初期化より先に発火するのを防ぐため、少し遅延させる
    setTimeout(() => {{
        const allMarkersData = {js_data};
        const map = this.map;
        
        // マーカーを保持するレイヤーグループを作成
        const markersLayerGroup = L.featureGroup().addTo(map);
        const allMarkers = [];

        // 全てのマーカーを事前に作成
        allMarkersData.forEach(data => {{
            const marker = L.marker([data.lat, data.lon], {{
                icon: L.icon({{
                    iconUrl: 'https://cdn.rawgit.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png',
                    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [1, -34],
                    shadowSize: [41, 41]
                }})
            }});
            marker.bindPopup(data.popup);
            marker.bindTooltip(data.name);
            
            // フィルターで使うためのデータをマーカーに添付
            marker.fumikiriData = data;
            allMarkers.push(marker);
        }});

        // フィルター要素を取得
        const nameInput = document.getElementById('name-filter');
        const lineSelect = document.getElementById('line-filter');
        const shishaSelect = document.getElementById('shisha-filter');
        const kashoSelect = document.getElementById('kasho-filter');
        const typeSelect = document.getElementById('type-filter');
        const countDiv = document.getElementById('results-count');

        // ドロップダウンに選択肢を設定する関数（ロジック改善）
        function populateSelect(selectElement, property) {{
            // 空白やnullを除外してからユニークなリストを作成
            const options = [...new Set(allMarkersData.map(d => d[property]).filter(p => p && p.trim() !== ''))].sort();
            selectElement.innerHTML = '<option value="すべて">すべて</option>' + options.map(opt => `<option value="${{opt}}">${{opt}}</option>`).join('');
        }}

        // 各フィルターを初期化
        populateSelect(lineSelect, 'line');
        populateSelect(shishaSelect, 'shisha');
        populateSelect(kashoSelect, 'kasho');
        populateSelect(typeSelect, 'type');

        function applyFilters() {{
            markersLayerGroup.clearLayers(); // 表示中のマーカーを一旦クリア
            
            const nameFilter = nameInput.value.toLowerCase();
            const lineFilter = lineSelect.value;
            const shishaFilter = shishaSelect.value;
            const kashoFilter = kashoSelect.value;
            const typeFilter = typeSelect.value;
            
            let visibleCount = 0;

            allMarkers.forEach(marker => {{
                const data = marker.fumikiriData;
                const isVisible = 
                    (nameFilter === '' || data.name.toLowerCase().includes(nameFilter)) &&
                    (lineFilter === 'すべて' || data.line === lineFilter) &&
                    (shishaFilter === 'すべて' || data.shisha === shishaFilter) &&
                    (kashoFilter === 'すべて' || data.kasho === kashoFilter) &&
                    (typeFilter === 'すべて' || data.type === typeFilter);

                if (isVisible) {{
                    markersLayerGroup.addLayer(marker);
                    visibleCount++;
                }}
            }});
            countDiv.textContent = `表示件数: ${{visibleCount}}件`;
        }}

        // イベントリスナーを設定
        [nameInput, lineSelect, shishaSelect, kashoSelect, typeSelect].forEach(el => {{
            el.addEventListener('input', applyFilters);
            el.addEventListener('change', applyFilters);
        }});

        // 初期表示
        applyFilters();
    }}, 500);
    </script>
    """
    
    m.get_root().html.add_child(folium.Element(custom_script_css))
    
    return m._repr_html_()


# --- データファイルのパス ---
DATA_PATH = 'data/踏切_緯度経度追加_v5.csv'
df = load_data(DATA_PATH)

# --- サイドバー (Streamlitアプリ用フィルター) ---
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
                selected_kilo_range = st.slider('中心位置キロ程で絞り込み', min_value=float(min_kilo), max_value=float(max_kilo), value=(float(min_kilo), float(max_kilo)))
            else:
                selected_kilo_range = None
        else:
            selected_kilo_range = None
    else:
        st.warning("データを読み込めませんでした。")
        search_name, selected_line, selected_shisha, selected_kasho, selected_type = "", "すべて", "すべて", "すべて", "すべて"
        selected_kilo_range = None

# --- データの絞り込み処理 (Streamlitアプリ用) ---
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
        filtered_df = filtered_df[(filtered_df['中心位置キロ程'] >= selected_kilo_range[0]) & (filtered_df['中心位置キロ程'] <= selected_kilo_range[1])]

# --- メイン画面 (地図とデータ表示) ---
if not filtered_df.empty:
    center_lat = filtered_df['Lat'].mean()
    center_lon = filtered_df['Lon'].mean()
    m_main = folium.Map(location=[center_lat, center_lon], zoom_start=12)
    for idx, row in filtered_df.iterrows():
        if pd.notna(row['Lat']) and pd.notna(row['Lon']):
            popup_html = f"<b>踏切名:</b> {row.get('踏切名', '名称不明')}<br><b>線名:</b> {row.get('線名', '')}<br><b>キロ程:</b> {format_kilopost(row.get('中心位置キロ程'))}<br><a href='https://www.google.com/maps?q={row['Lat']},{row['Lon']}' target='_blank' rel='noopener noreferrer'>Google Mapで開く</a>"
            folium.Marker(location=[row['Lat'], row['Lon']], popup=folium.Popup(popup_html, max_width=300), tooltip=row.get('踏切名', ''), icon=folium.Icon(color='blue', icon='train', prefix='fa')).add_to(m_main)
    st_folium(m_main, width='100%', height=500)

    # --- ダウンロードセクション ---
    st.markdown("---")
    st.subheader("ダウンロードオプション")

    with st.expander("Ver.1 静的な地図をHTMLとしてダウンロード"):
        map_html_static = m_main._repr_html_()
        st.download_button(label="ダウンロード (Ver.1)", data=map_html_static, file_name="fumikiri_map_static.html", mime="text/html")
    
    with st.expander("Ver.2 多機能フィルター付き地図をHTMLとしてダウンロード"):
        map_html_multifilter = create_multifilter_map_html(filtered_df)
        st.download_button(
            label="ダウンロード (Ver.2)",
            data=map_html_multifilter,
            file_name="fumikiri_map_interactive.html",
            mime="text/html",
            help="現在絞り込まれている全ての踏切データと、多角的な検索・絞り込み機能を含んだHTMLファイルをダウンロードします。"
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
    st.info("データを読み込めませんでした。サイドバーで検索条件を調整してください。")
