# Instalamos todo lo necesario

from skyfield.api import EarthSatellite, load
from datetime import datetime, timezone
import reverse_geocoder as rg
import pytz # Para convertir la hora UCT a la hora de España
import requests
import os
import json
from dotenv import load_dotenv, find_dotenv # Para guardar la API Key
import streamlit as st
import pydeck as pdk

# API de n2yo.com

def get_satellite_position(satellite_id: int):
    # Cargar la ruta absoluta del archivo .env
    dotenv_path = os.path.join(os.path.dirname(__file__), 'n2yo_key.env')
    load_dotenv(dotenv_path)

    # Obtener la clave de la API
    api_key = os.getenv("n2yo_key")

    # Para ver Two-Line Element Set (TLE), un formato estándar que proporciona los elementos orbitales de un satélite para predecir su posición en el espacio
    url = f"https://api.n2yo.com/rest/v1/satellite/tle/{satellite_id}?apiKey={api_key}"
    response = requests.get(url)
    if response.status_code != 200:
        return None

    data = response.json()
    tle_lines = data.get('tle', '').splitlines()
    if len(tle_lines) != 2:
        return None

    satellite_name = data['info'].get("satname", "Unknown")

    # Calcular posición con Skyfield # A través del TLE anterior, y con Skyfield, podemos calcular la posición del satélite
    tle1, tle2 = tle_lines
    ts = load.timescale() # Crear el objeto del satélite
    sat = EarthSatellite(tle1, tle2, f"Satellite {satellite_id}", ts)
    now_utc = datetime.now(timezone.utc) # Tiempo actual con zona horaria UTC
    t = ts.utc(now_utc)
    subpoint = sat.at(t).subpoint() 

    lat = subpoint.latitude.degrees # Datos de latitud, longitud y altitud
    lon = subpoint.longitude.degrees
    elev = subpoint.elevation.km

    # Buscar ciudad y país usando reverse geocoding
    try:
        loc = rg.search((lat, lon))[0]
        city, country = loc['name'], loc['cc']
    except Exception:
        city, country = "Unknown", "Unknown"

    return {
        "Name": satellite_name,
        "UTC Time": now_utc.strftime("%Y-%m-%d %H:%M:%S"),
        "Latitude": f"{lat:.2f}°",
        "Longitude": f"{lon:.2f}°",
        "Altitude": f"{elev:.2f} km",
        "Location": f"Currently over: {city}, {country}"
    }

# Interfaz de usuario Streamlit

st.set_page_config(page_title="Real-Time Satellite Tracker", layout="centered")

# Título
st.title("🌍 Real-Time Satellite Tracker")

# Campo de entrada para el NORAD ID, predefinido en 25544 (ISS)
norad = st.number_input(
    "Enter the satellite's NORAD number",
    min_value=0,
    step=1,
    value=25544
)

# Botón para lanzar la consulta
if st.button("Track"):
    # Llamamos a la función del backend
    info = get_satellite_position(norad)

    if info is None:
        st.error("❌ Satellite data is currently unavailable. Please check the NORAD ID and try again shortly.")
    else:
         # Mostrar datos usando las mismas claves del backend
        st.subheader(info["Name"])
        st.write(f"**UTC Time:** {info['UTC Time']}")
        st.write(f"**Latitude:** {info['Latitude']}")
        st.write(f"**Longitude:** {info['Longitude']}")
        st.write(f"**Altitude:** {info['Altitude']}")
        st.write(f"**{info['Location']}**")

        # Preparar coordenadas para el mapa
        lat = float(info["Latitude"].strip("°"))
        lon = float(info["Longitude"].strip("°"))
        
        df = [{"lat": lat, "lon": lon}] # Usmos un df para pydeck

        # Mapa oscuro con punto rojo de radio pequeño
        st.pydeck_chart(pdk.Deck(
            initial_view_state=pdk.ViewState(
                latitude=lat,
                longitude=lon,
                zoom=3,
                pitch=0,
            ),
            layers=[
                pdk.Layer(
                    "ScatterplotLayer",
                    data=df,
                    get_position="[lon, lat]",
                    get_radius=20000,           # radio más razonable
                    get_color="[255, 0, 0, 200]",  # rojo
                    pickable=False,
                )
            ],
            tooltip={"text": f"Satellite {norad}\nLat: {lat:.2f}, Lon: {lon:.2f}"},
            map_style="mapbox://styles/mapbox/dark-v9"
        ))