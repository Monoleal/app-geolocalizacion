import streamlit as st
import pandas as pd
import numpy as np
import time
import requests
from geopy.distance import geodesic
from io import BytesIO

# ---------- FUNCIONES ----------
def get_coordinates(address, api_key):
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {'address': address, 'key': api_key}
    response = requests.get(base_url, params=params).json()

    if response['status'] == 'OK':
        location = response['results'][0]['geometry']['location']
        return location['lat'], location['lng']
    else:
        return np.nan, np.nan

def sort_by_proximity(df):
    remaining_clients = df.copy()
    ordered_clients = []

    start_point = remaining_clients.iloc[0]

    while not remaining_clients.empty:
        remaining_clients["distancia"] = remaining_clients.apply(
            lambda row: geodesic((start_point['Latitud'], start_point['Longitud']),
                                 (row['Latitud'], row['Longitud'])).km, axis=1)

        next_idx = remaining_clients["distancia"].idxmin()
        next_client = remaining_clients.loc[next_idx]

        ordered_clients.append(next_client)
        start_point = next_client
        remaining_clients = remaining_clients.drop(next_idx)

    return pd.DataFrame(ordered_clients)

def convertir_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Ruta')
    return output.getvalue()

# ---------- INTERFAZ ----------
st.set_page_config(page_title="Geolocalizador de Clientes", page_icon="📍", layout="centered")

st.markdown("<h1 style='text-align: center; color: #4CAF50;'>📍 Geolocalización de clientes</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Sube un archivo con tus clientes y agrupalos por cercania</p>", unsafe_allow_html=True)

# --------- INGRESO DE API Y ARCHIVO ---------
api_key = st.text_input("🔑 Ingresa tu API Key de Google Maps", type="password")
uploaded_file = st.file_uploader("📁 Cargar archivo Excel", type="xlsx")

# Control de estado para evitar ejecuciones repetidas
if 'procesado' not in st.session_state:
    st.session_state.procesado = False

# Si el usuario carga archivo y API, y aún no se ha procesado
if uploaded_file and api_key and not st.session_state.procesado:
    df = pd.read_excel(uploaded_file, dtype=str)
    df.columns = df.columns.str.strip()

    latitudes = []
    longitudes = []

    total_clients = len(df)
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, row in df.iterrows():
        full_address = f"{row['Dir. Suministro']}, {row['C.P.']}, {row['Población']}, {row['Provincia']}"
        lat, lng = get_coordinates(full_address, api_key)
        latitudes.append(lat)
        longitudes.append(lng)

        percent_complete = int((i + 1) / total_clients * 100)
        progress_bar.progress(percent_complete)
        status_text.text(f"🔄 Procesando clientes {i+1} de {total_clients} ({percent_complete}%)")
        time.sleep(0.5)

    df['Latitud'] = latitudes
    df['Longitud'] = longitudes
    df = df.dropna(subset=['Latitud', 'Longitud']).copy()

    if df.empty:
        st.error("🚨 No se encontraron coordenadas válidas. Verifica las direcciones.")
    else:
        df_sorted = sort_by_proximity(df)
        st.success("✅ Grupo generado con éxito.")

        # Mostrar mapa con puntos geolocalizados
        st.subheader("🗺️ Mapa de los clientes geolocalizados")
        st.map(df_sorted[['Latitud', 'Longitud']].rename(columns={"Latitud": "lat", "Longitud": "lon"}))

        # Convertir a Excel
        excel_file = convertir_excel(df_sorted)

        # Botón para descargar archivo Excel
        st.download_button(
            label="⬇️ Descargar nuevo archivo Excel optimizado",
            data=excel_file,
            file_name='clientes_ruteados.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

        st.session_state.procesado = True  # Marcar como ya procesado

# Mensaje si ya se procesó
elif st.session_state.procesado:
    st.info("✅ Ya procesaste un archivo. Sube uno nuevo para volver a ejecutar el sistema.")
