import logging
import folium
from geopy.distance import geodesic
import googlemaps
from datetime import datetime
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
from django.conf import settings

logging.basicConfig(level=logging.INFO)

GOOGLE_MAPS_API_KEY = 'AIzaSyA0LAf7WqZMfsePZMHMv8O3tjw9EswXl_g'
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

base_dir = settings.BASE_DIR / 'assets'
excel_path = base_dir / 'soil_type.xlsx'
img_path = base_dir / 'sitemapanaloverlay.png'

# script_dir = os.path.dirname(os.path.abspath(__file__))
# excel_path = os.path.join(script_dir, 'soil_type.xlsx')

def get_user_input():
    while True:
        try:
            latitude = float(input("Enter latitude: "))
            longitude = float(input("Enter longitude: "))
            if -90 <= latitude <= 90 and -180 <= longitude <= 180:
                return latitude, longitude
            else:
                print("Invalid latitude or longitude. Please enter valid values.")
        except ValueError:
            print("Invalid input. Please enter numerical values for latitude and longitude.")

def create_map(latitude, longitude, zoom=20, min_zoom=16):
    folium_map = folium.Map(
        location=[latitude, longitude],
        zoom_start=zoom,
        min_zoom=min_zoom,
        max_zoom=20, 
    )
    return folium_map

def add_marker(map_obj, latitude, longitude, color, popup):
    folium.Marker(
        [latitude, longitude], 
        icon=folium.Icon(color=color, icon='info-sign'),
        popup=popup
    ).add_to(map_obj)

def find_nearby_places(map_obj, latitude, longitude, place_types, radius):
    add_marker(map_obj, latitude, longitude, 'red', 'Your Location')
    folium.Circle(
        location=(latitude, longitude),
        radius=200,
        color='blue',
        fill=True,
        fill_color='blue',
        fill_opacity=0.1
    ).add_to(map_obj)
    colors = {
        "park": "green",
        "shopping_mall": "blue",
        "bank": "purple",
        "hotel": "orange",
        "school": "gray"
    }
    for place_type in place_types:
        print(f"Searching for nearby {place_type}s within {radius} meters...")
        places_result = gmaps.places_nearby(
            location=(latitude, longitude),
            radius=radius,
            type=place_type
        )
        if places_result['status'] == 'OK':
            for place in places_result['results']:
                place_lat = place['geometry']['location']['lat']
                place_lon = place['geometry']['location']['lng']
                place_name = place['name']
                place_address = place.get('vicinity', 'Address not available')
                place_distance = geodesic((latitude, longitude), (place_lat, place_lon)).meters
                popup_text = f"<b><span style='color:red;'>NAME:</span></b> {place_name}<br>" \
                             f"<b><span style='color:red;'>CATEGORY:</span></b> {place_type}<br>" \
                             f"<b><span style='color:red;'>DISTANCE:</span></b> {place_distance:.2f} meters"
                add_marker(map_obj, place_lat, place_lon, colors.get(place_type, 'blue'), popup_text)
            
            print(f"Found {len(places_result['results'])} {place_type}(s)")
        else:
            print(f"No nearby {place_type}s found or error in API response.")
    
    print("Searching for nearby roads...")
    reverse_geocode_result = gmaps.reverse_geocode((latitude, longitude))
    if reverse_geocode_result:
        for result in reverse_geocode_result:
            if 'route' in result['types']:
                road_name = result['address_components'][0]['long_name']
                road_lat = result['geometry']['location']['lat']
                road_lon = result['geometry']['location']['lng']
                road_distance = geodesic((latitude, longitude), (road_lat, road_lon)).meters
                add_marker(map_obj, road_lat, road_lon, 'gray', f"{road_name} ({road_distance:.2f} meters)")
                break  
    else:
        print("No nearby roads found.")
    
    return map_obj

def load_image(image_path):
    try:
        from matplotlib import pyplot as plt
        import matplotlib.image as mpimg
        img = mpimg.imread(image_path)
        return img
    except FileNotFoundError:
        logging.error(f"Error: Image file '{image_path}' not found.")
        return None
    except Exception as e:
        logging.error(f"Error loading image '{image_path}': {e}")
        return None

def add_image_overlay(map_obj, img, latitude, longitude, size_factor=0.0005):
    lat_offset = size_factor
    lon_offset = size_factor
    south = latitude - lat_offset
    north = latitude + lat_offset
    west = longitude - lon_offset
    east = longitude + lon_offset
    image_overlay = folium.raster_layers.ImageOverlay(
        image=img,
        bounds=[[south, west], [north, east]],
        interactive=True,
        cross_origin=False,
        zindex=1
    )
    image_overlay.add_to(map_obj)
    return image_overlay

def add_compass_markers(map_obj, latitude, longitude, size_factor=0.0005):
    distance = size_factor * 2  
    compass_points = {
        'N': [latitude + distance, longitude],
        'S': [latitude - distance, longitude],
        'E': [latitude, longitude + distance],
        'W': [latitude, longitude - distance]
    }
    for direction, coords in compass_points.items():
        folium.Marker(
            coords,
            tooltip=direction,
            icon=folium.DivIcon(html=f'<div style="color: red; font-size: 24px; font-weight: bold;">{direction}</div>')
        ).add_to(map_obj)

def add_zoom_handler(folium_map, latitude, longitude, size_factor):
    script = f"""
    <script>
        function updateImageOverlay() {{
            var map = document.querySelector('.leaflet-container')._leaflet_map;
            var zoom = map.getZoom();
            var sizeFactor = {size_factor} * Math.pow(2, 21 - zoom);
            var south = {latitude} - sizeFactor;
            var north = {latitude} + sizeFactor;
            var west = {longitude} - sizeFactor;
            var east = {longitude} + sizeFactor;
            imageOverlay.setBounds([[south, west], [north, east]]);
        }}
        
        var map = document.querySelector('.leaflet-container')._leaflet_map;
        var imageOverlay;
        map.eachLayer(function (layer) {{
            if (layer instanceof L.ImageOverlay) {{
                imageOverlay = layer;
            }}
        }});
        map.on('zoomend', updateImageOverlay);
        updateImageOverlay();
    </script>
    """
    folium_map.get_root().html.add_child(folium.Element(script))

def overlay_image_on_map(map_obj, latitude, longitude, image_path, size_factor=0.005):
    img = load_image(image_path)
    if img is None:
        print("Unable to load image. Exiting.")
        return None

    image_overlay = add_image_overlay(map_obj, img, latitude, longitude, size_factor=size_factor)
    add_compass_markers(map_obj, latitude, longitude, size_factor=size_factor)
    add_zoom_handler(map_obj, latitude, longitude, size_factor)
    return map_obj

def main(output_file, latitude, longitude):
    image_path = img_path  
    place_types = ["park", "shopping_mall", "bank", "hotel", "school"]  
    search_radius = 2000  
    
    logging.info("Wind direction: South West to North East\nSun direction: East to West")
    
    folium_map = create_map(latitude, longitude, zoom=20)  
    folium_map = find_nearby_places(folium_map, latitude, longitude, place_types, search_radius)
    folium_map = overlay_image_on_map(folium_map, latitude, longitude, image_path, size_factor=0.0005)
    
    if folium_map is None:
        logging.error("Failed to create map with image overlay. Exiting.")
        return
    
    # Ensure the maps directory exists within media folder
    media_maps_dir = os.path.join(settings.MEDIA_ROOT, 'maps')
    if not os.path.exists(media_maps_dir):
        os.makedirs(media_maps_dir)
    
    # Save the map file within media/maps directory
    map_file_path = os.path.join(media_maps_dir, output_file)
    folium_map.save(map_file_path)
    
    logging.info(f"Map saved as '{map_file_path}'")
    
    # Return the relative path to be stored in the database
    return os.path.relpath(map_file_path, settings.MEDIA_ROOT)

import pandas as pd
soil = pd.read_excel(excel_path)

import numpy as np

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  
    
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)
    
    a = np.sin(delta_phi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2.0) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    distance = R * c
    
    return distance

def soil_type(df, latitude, longitude):
    inp_lat = latitude
    inp_long = longitude

    dist = []

    for index, rows in df.iterrows():
        soil_lat = rows['Latitude']
        soil_long = rows['Longitude']

        val = haversine(inp_lat, inp_long, soil_lat, soil_long)
        dist.append(val)

    df['Distance'] = dist
    closest = df.nsmallest(1, 'Distance')
    close = closest[['Soil Type', 'Ground Water Depth', 'Foundation Type']].copy()
    return close

