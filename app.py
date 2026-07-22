import streamlit as st
import pandas as pd
import folium
from folium.plugins import Fullscreen
import streamlit.components.v1 as components
import xml.etree.ElementTree as ET
from datetime import datetime
import math

# Konfiguracja strony
st.set_page_config(page_title="Mapa Trasy GPX", layout="wide", initial_sidebar_state="collapsed")

# Styl CSS
st.markdown("""
    <style>
        .block-container {
            padding-top: 0.5rem;
            padding-bottom: 0rem;
            padding-left: 0.2rem;
            padding-right: 0.2rem;
        }
        iframe {
            width: 100% !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("Interaktywna Mapa GPX (Mapy.cz)")

def haversine(lat1, lon1, lat2, lon2):
    # Wyliczanie odległości między dwoma punktami GPS w metrach
    R = 6371000  # Promień Ziemi w metrach
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

@st.cache_data
def load_gpx_data():
    file_path = "Bulgarski poscikk.gpx"
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
    
    data = []
    for trkpt in root.findall('.//gpx:trkpt', ns):
        lat = float(trkpt.attrib['lat'])
        lon = float(trkpt.attrib['lon'])
        
        time_elem = trkpt.find('gpx:time', ns)
        dt = datetime.fromisoformat(time_elem.text.replace('Z', '+00:00')) if time_elem is not None else None
        
        ele_elem = trkpt.find('gpx:ele', ns)
        ele = float(ele_elem.text) if ele_elem is not None else None
        
        data.append({'lat': lat, 'lon': lon, 'dt': dt, 'ele': ele})
        
    df = pd.DataFrame(data)
    
    # Wyliczanie prędkości km/h
    speeds = [0.0]
    for i in range(1, len(df)):
        d = haversine(df.loc[i-1, 'lat'], df.loc[i-1, 'lon'], df.loc[i, 'lat'], df.loc[i, 'lon'])
        t_diff = (df.loc[i, 'dt'] - df.loc[i-1, 'dt']).total_seconds()
        
        if t_diff > 0:
            spd = (d / t_diff) * 3.6  # m/s -> km/h
            # Wyciszenie nierealistycznych skoków GPS (np. powyżej 200 km/h)
            speeds.append(round(min(spd, 200.0), 1))
        else:
            speeds.append(0.0)
            
    df['predkosc_kmh'] = speeds
    df['data'] = df['dt'].dt.strftime('%Y-%m-%d')
    df['czas_str'] = df['dt'].dt.strftime('%H:%M:%S')
    df['czas_dt'] = df['dt'].dt.time
    
    # Podział na dni
    grouped = {date: group.copy() for date, group in df.groupby('data')}
    return grouped

try:
    data_dict = load_gpx_data()
    dates = list(data_dict.keys())

    # --- PANEL BOCZNY ---
    st.sidebar.header("Filtrowanie")
    selected_date = st.sidebar.selectbox("Wybierz datę:", dates)

    df_selected = data_dict[selected_date]

    min_time = df_selected['czas_dt'].min()
    max_time = df_selected['czas_dt'].max()

    time_range = st.sidebar.slider(
        "Zakres czasu:",
        min_value=min_time,
        max_value=max_time,
        value=(min_time, max_time)
    )

    mask = (df_selected['czas_dt'] >= time_range[0]) & (df_selected['czas_dt'] <= time_range[1])
    df_filtered = df_selected.loc[mask]

    st.write(f"Dzień: **{selected_date}** | Godziny: **{time_range[0]} - {time_range[1]}** | Punkty: **{len(df_filtered)}**")

    if not df_filtered.empty:
        start_lat = df_filtered['lat'].mean()
        start_lon = df_filtered['lon'].mean()
        
        m = folium.Map(location=[start_lat, start_lon], zoom_start=12)
        Fullscreen(position="topright", title="Pełny ekran", title_cancel="Wyjdź", force_separate_button=True).add_to(m)
        
        coordinates = df_filtered[['lat', 'lon']].values.tolist()
        folium.PolyLine(coordinates, color="blue", weight=3, opacity=0.6).add_to(m)
        
        # Próbkowanie markerów do rysowania kolorowych punktów
        step = max(1, len(df_filtered) // 300)
        for idx, row in df_filtered.iloc[::step].iterrows():
            spd = row['predkosc_kmh']
            popup_info = f"Czas: {row['czas_str']}<br>Prędkość: {spd} km/h<br>Wysokość: {row['ele']} m n.p.m."
            
            if spd < 20:
                color = "green"
            elif spd < 60:
                color = "orange"
            else:
                color = "red"
                
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=3,
                popup=folium.Popup(popup_info, max_width=200),
                color=color,
                fill=True,
                fill_opacity=0.8
            ).add_to(m)
            
        m.fit_bounds(coordinates)
        map_html = m._repr_html_()
        components.html(map_html, height=750, scrolling=False)
    else:
        st.warning("Brak danych w wybranym przedziale czasu.")

except Exception as e:
    st.error(f"Nie udało się wczytać pliku GPX. Upewnij się, że plik 'Bulgarski poscikk.gpx' znajduje się w głównym folderze na GitHubie. Błąd: {e}")
