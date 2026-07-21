import streamlit as st
import pandas as pd
import folium
from folium.plugins import Fullscreen
import streamlit.components.v1 as components

# Konfiguracja strony - ukrywamy marginesy Streamlita
st.set_page_config(page_title="Mapa Trasy", layout="wide", initial_sidebar_state="collapsed")

# Styl CSS pozbywający się marginesów na telefonie
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
            padding-left: 0.5rem;
            padding-right: 0.5rem;
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

# --- PANEL BOCZNY (Filtrowanie) ---
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

# Filtrowanie po czasie
mask = (df_selected['czas_dt'] >= time_range[0]) & (df_selected['czas_dt'] <= time_range[1])
df_filtered = df_selected.loc[mask]

st.write(f"Wyświetlam trasę z dnia **{selected_date}** w godzinach **{time_range[0]} - {time_range[1]}** (Punktów: {len(df_filtered)}).")

if not df_filtered.empty:
    start_lat = df_filtered['szerokosc'].mean()
    start_lon = df_filtered['dlugosc'].mean()
    
    # Tworzenie mapy
    m = folium.Map(location=[start_lat, start_lon], zoom_start=12)
    
    # Dodanie przycisku Pełnego Ekranu na mapie
    Fullscreen(position="topright", title="Pełny ekran", title_cancel="Wyjdź z pełnego ekranu", force_separate_button=True).add_to(m)
    
    # Rysowanie trasy
    coordinates = df_filtered[['szerokosc', 'dlugosc']].values.tolist()
    folium.PolyLine(coordinates, color="blue", weight=4, opacity=0.8).add_to(m)
    
    # Punkty z prędkością
    step = max(1, len(df_filtered) // 300) 
    for idx, row in df_filtered.iloc[::step].iterrows():
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
            radius=4,
            popup=folium.Popup(popup_info, max_width=200),
            color=color,
            fill=True,
            fill_opacity=0.8
        ).add_to(m)
        
    # Automatyczne dopasowanie widoku do całej trasy
    m.fit_bounds(coordinates)
    
    # Renderowanie wysokiego okna mapy (wysokość 750px na telefonie)
    map_html = m._repr_html_()
    components.html(map_html, height=750, scrolling=False)
else:
    st.warning("Brak danych z GPS w wybranym przedziale czasu.")
