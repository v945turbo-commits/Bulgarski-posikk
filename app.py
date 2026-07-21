import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# Konfiguracja strony
st.set_page_config(page_title="Mapa Trasy", layout="wide")
st.title("Interaktywna Mapa Trasy z Prędkością")

@st.cache_data
def load_data():
    file_path = "trasa_11-20_lipca_2026.xlsx"
    xls = pd.ExcelFile(file_path)
    data = {}
    
    # Wczytywanie każdego arkusza (dnia) do słownika
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        
        # Konwersja kolumny czasowej na obiekt time (do obsługi suwaka)
        df['czas_dt'] = pd.to_datetime(df['czas'], format='%H:%M:%S').dt.time
        data[sheet] = df
        
    return data

# Ładowanie danych
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

# --- EKRAN GŁÓWNY ---
st.write(f"Wyświetlam trasę z dnia **{selected_date}** w godzinach **{time_range[0]} - {time_range[1]}**.")
st.write(f"Liczba punktów na mapie: {len(df_filtered)}")

if not df_filtered.empty:
    # Centrowanie mapy
    start_lat = df_filtered['szerokosc'].mean()
    start_lon = df_filtered['dlugosc'].mean()
    
    m = folium.Map(location=[start_lat, start_lon], zoom_start=13)
    
    # Rysowanie głównej linii trasy
    coordinates = df_filtered[['szerokosc', 'dlugosc']].values.tolist()
    folium.PolyLine(coordinates, color="blue", weight=3, opacity=0.7).add_to(m)
    
    # Dodawanie markerów z prędkością
    # Ze względów wydajnościowych wyświetlamy max ~500 punktów z detalami
    step = max(1, len(df_filtered) // 500) 
    
    for idx, row in df_filtered.iloc[::step].iterrows():
        popup_info = f"Czas: {row['czas']}<br>Prędkość: {row['predkosc_kmh']} km/h"
        
        # Kolor w zależności od prędkości
        if row['predkosc_kmh'] < 20:
            color = "green"
        elif row['predkosc_kmh'] < 60:
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
        
    # Wyświetlenie mapy w aplikacji Streamlit
    st_folium(m, width=900, height=600)
else:
    st.warning("Brak danych z GPS w wybranym przedziale czasu.")
