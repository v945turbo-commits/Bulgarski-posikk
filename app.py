import streamlit as st
import pandas as pd
import folium
from folium.plugins import Fullscreen
import streamlit.components.v1 as components

# Konfiguracja strony
st.set_page_config(page_title="Mapa Trasy", layout="wide", initial_sidebar_state="collapsed")

# Styl CSS usuwający marginesy
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

st.title("Interaktywna Mapa Trasy z Prędkością")

@st.cache_data
def load_data():
    file_path = "trasa_11-20_lipca_2026.xlsx"
    xls = pd.ExcelFile(file_path)
    data = {}
    
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        df['czas_dt'] = pd.to_datetime(df['czas'], format='%H:%M:%S').dt.time
        data[sheet] = df
        
    return data

data_dict = load_data()
dates = list(data_dict.keys())

# --- PANEL BOCZNY ---
st.sidebar.header("Ustawienia filtru")
selected_date = st.sidebar.selectbox("Wybierz datę (arkusz):", dates)

df_selected = data_dict[selected_date]

min_time = df_selected['czas_dt'].min()
max_time = df_selected['czas_dt'].max()

time_range = st.sidebar.slider(
    "Wybierz fragment trasy (zakres czasu):",
    min_value=min_time,
    max_value=max_time,
    value=(min_time, max_time)
)

# Filtrowanie
mask = (df_selected['czas_dt'] >= time_range[0]) & (df_selected['czas_dt'] <= time_range[1])
df_filtered = df_selected.loc[mask]

st.write(f"Dzień: **{selected_date}** | Godziny: **{time_range[0]} - {time_range[1]}** | Wyświetlanych punktów: **{len(df_filtered)}**")

if not df_filtered.empty:
    start_lat = df_filtered['szerokosc'].mean()
    start_lon = df_filtered['dlugosc'].mean()
    
    m = folium.Map(location=[start_lat, start_lon], zoom_start=12)
    
    # Przycisk Pełnego Ekranu
    Fullscreen(position="topright", title="Pełny ekran", title_cancel="Wyjdź", force_separate_button=True).add_to(m)
    
    # Linia trasy
    coordinates = df_filtered[['szerokosc', 'dlugosc']].values.tolist()
    folium.PolyLine(coordinates, color="blue", weight=3, opacity=0.6).add_to(m)
    
    # RYSOWANIE 100% PUNKTÓW (BEZ PRÓBKOWANIA)
    for idx, row in df_filtered.iterrows():
        spd = row['predkosc_kmh']
        popup_info = f"Czas: {row['czas']}<br>Prędkość: {spd} km/h"
        
        if pd.isna(spd) or spd < 20:
            color = "green"
        elif spd < 60:
            color = "orange"
        else:
            color = "red"
            
        folium.CircleMarker(
            location=[row['szerokosc'], row['dlugosc']],
            radius=3,
            popup=folium.Popup(popup_info, max_width=200),
            color=color,
            fill=True,
            fill_opacity=0.8
        ).add_to(m)
        
    # Kadrowanie widoku do trasy
    m.fit_bounds(coordinates)
    
    # Wyświetlenie mapy
    map_html = m._repr_html_()
    components.html(map_html, height=750, scrolling=False)
else:
    st.warning("Brak danych w wybranym zakresie czasu.")
