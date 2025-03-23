import streamlit as st
import pandas as pd
import numpy as np
import time
import requests
from geopy.distance import geodesic

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

# 👉 Interfaz de usuario
st.title("📍 Ordenador de Rutas por Geolocalización")
st.write("Sube un archivo CSV con direcciones de tus clientes para obtener una ruta optimizada.")

api_key = st.text_input("🔑 Ingresa tu API Key de Google Maps", type="password")
uploaded_file = st.file_uploader("📁 Cargar archivo CSV", type="csv")

if uploaded_file and api_key:
    df = pd.read_csv(uploaded_file, dtype=str)
    df.columns = df.columns.str.strip()

    latitudes = []
    longitudes = []

    with st.spinner("⏳ Obteniendo coordenadas..."):
        for i, row in df.iterrows():
            full_address = f"{row['Dir. Suministro']}, {row['C.P.']}, {row['Población']}, {row['Provincia']}"
            lat, lng = get_coordinates(full_address, api_key)
            latitudes.append(lat)
            longitudes.append(lng)
            time.sleep(0.5)

    df['Latitud'] = latitudes
    df['Longitud'] = longitudes
    df = df.dropna(subset=['Latitud', 'Longitud']).copy()

    if df.empty:
        st.error("🚨 No se encontraron coordenadas válidas.")
    else:
        df_sorted = sort_by_proximity(df)
        st.success("✅ Ruta optimizada generada con éxito.")

        st.download_button(
            label="⬇️ Descargar archivo procesado",
            data=df_sorted.to_csv(index=False).encode('utf-8'),
            file_name='clientes_ruteados.csv',
            mime='text/csv'
        )
