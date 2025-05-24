import requests
import json
from urllib.parse import quote
from halo import Halo
from datetime import datetime, timedelta
import pytz
import os
import pandas as pd
import random
import ssl
import certifi
import urllib.request
import io
import webbrowser
import subprocess
from urllib.parse import quote_plus
import argparse
import platform
import math

DATA_DIR = "data"
ADDRESS_FILE = "addresses.txt"
AIRPORTS_FILE = "airports.txt"
AIRPORTS_DOWNLOAD_CSV = "airports_download.csv"
NOMINATIM_API_BASE_URL = "https://nominatim.openstreetmap.org/search"
CENSUS_API_BASE_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
CENSUS_API_KEY = os.getenv("CENSUS_API_KEY")
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
CENSUS_REVERSE_URL = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"

def notify_api_key_status(args):
    """Notify if a US Census API key is found."""
    if args.census:
        if CENSUS_API_KEY:
            print("\nUS Census API key found and will be used larger rate limits.")
        else:
            print("\nNo Census API key found. Geocoding will proceed without it and with rate limits.")

def notify_chrome_missing():
    print("Google Chrome is not installed on your computer. Please download and install it to use the browser feature.")

def load_addresses():
    """Loads previously entered addresses from a file."""
    full_address_path = os.path.join(DATA_DIR, ADDRESS_FILE)
    if os.path.exists(full_address_path):
        with open(full_address_path, "r") as f:
            return [line.strip() for line in f]
    return []

def save_addresses(addresses):
    """Saves entered addresses to a file."""
    full_address_path = os.path.join(DATA_DIR, ADDRESS_FILE)
    with open(full_address_path, "w") as f:
        for address in addresses:
            f.write(address.upper() + "\n")

def geocode_address(address, geocoder="census"):
    """
    Geocodes an address using either Nominatim or US Census Geocoder API.

    Args:
      address: The street address to geocode.
      geocoder: 'census' or 'nominatim'

    Returns:
      A tuple containing (latitude, longitude, matched_address) or (None, None, None) if geocoding fails.
    """
    headers = {
        'User-Agent': 'Weather-App/1.0'
    }
    timeout = 1
    if geocoder == "census":
        benchmark = "Public_AR_Current"
        api_base_url = CENSUS_API_BASE_URL
        params = {
            "address": address,
            "benchmark": benchmark,
            "format": "json"
        }
        if CENSUS_API_KEY:
            params["key"] = CENSUS_API_KEY
        api_name = "Census"
    else:
        api_base_url = NOMINATIM_API_BASE_URL
        params = {
            "q": address,
            "format": "json",
            "limit": 1
        }
        api_name = "Nominatim"

    spinner = Halo(text=f'Geocoding address using {api_name}...', spinner='dots')
    spinner.start()
    try:
        response = requests.get(api_base_url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        if geocoder == "census":
            if data.get('result', {}).get('addressMatches'):
                match = data['result']['addressMatches'][0]
                latitude = match['coordinates']['y']
                longitude = match['coordinates']['x']
                matched_address = match['matchedAddress']
                spinner.succeed("Address geocoded successfully.")
                return float(latitude), float(longitude), matched_address
            else:
                spinner.fail("Address could not be matched.")
                return None, None, None
        else:
            if data:
                latitude = data[0]['lat']
                longitude = data[0]['lon']
                spinner.succeed("Address geocoded successfully.")
                return float(latitude), float(longitude), address
            else:
                spinner.fail("Address could not be matched.")
                return None, None, None
    except requests.exceptions.RequestException as e:
        spinner.fail(f"Error during {api_name} API request: {e}")
        return None, None, None
    finally:
        spinner.stop()

def generate_google_maps_url(latitude, longitude, label, zoom=15):
    """
    Generates a Google Maps URL for the given coordinates.

    Args:
        latitude: The latitude of the location.
        longitude: The longitude of the location.
        label: Label for the place on google maps
        zoom: The zoom level for the map (default is 15).
    Example:
        https://www.google.com/maps/place/-56.4944,147.5272/@-56.4944,147.5272,5z/
        f"https://www.google.com/maps/search/{latitude},{longitude}/{latitude},{longitude},{zoom}z?t=s"
    Returns:
        A string containing the Google Maps URL.
    """

    if label == "":
        return f"https://www.google.com/maps/place/{latitude},{longitude}/@{latitude},{longitude},{zoom}z?t=s"
    else:
        return f"https://www.google.com/maps/place/{quote(label)}"


def get_county_state_from_latlon(latitude, longitude):
    """
    Gets county and state from latitude and longitude using FCC API.

    Args:
        latitude: The latitude of the location.
        longitude: The longitude of the location.

    Returns:
        county and state as string or None if not found.
    """
    spinner = Halo(text='Reverse geocoding lat lon for county and state...', spinner='dots')
    try:
        spinner.start()
        url = f"https://geo.fcc.gov/api/census/block/find?latitude={latitude}&longitude={longitude}&format=json"
        response = requests.get(url,timeout=1)
        response.raise_for_status()
        data = response.json()
        spinner.succeed("County and state received successfully")
        return data['County']['name']+ "-" +data['State']['name']
    except Exception as e:
        spinner.fail(f"Error getting county and state: {e}")
        return None
    finally:
        spinner.stop()

def get_city_state_from_latlon(latitude, longitude, use_census_api=False):
    """
    Gets city from latitude and longitude using Nominatim API by default, US Census API if census is set.

    Args:
        latitude: The latitude of the location.
        longitude: The longitude of the location.
        use_census_api: use census api

    Returns:
        city and state as string or None if not found.
    """
    spinner = Halo(text='Reverse geocoding lat lon for city and state...', spinner='dots')
    try:
        spinner.start()
        headers = {
            'User-Agent': 'Weather-App/1.0'
        }
        
        if use_census_api:
            url = f"{CENSUS_REVERSE_URL}?x={longitude}&y={latitude}&benchmark=Public_AR_Current&vintage=Current_Current&format=json"
            response = requests.get(url, timeout=1, headers=headers)
            response.raise_for_status()
            data = response.json()

            try:
                city = data['result']['geographies']['Incorporated Places'][0]['BASENAME']
            except (KeyError, IndexError, TypeError):
                city = None
            try:
                state = data['result']['geographies']['States'][0]['BASENAME']
            except (KeyError, IndexError, TypeError):
                state = None
            try: 
                city_state = data['result']['geographies']['Urban Areas'][0]['BASENAME']
            except (KeyError, IndexError, TypeError):
                city_state = None
            try:
                county_city = data['result']['geographies']['County Subdivisions'][0]['BASENAME']
            except (KeyError, IndexError, TypeError):
                county_city = None

            if city_state:
                spinner.succeed("City and state received successfully")
                return city_state
            if city and state:
                spinner.succeed("City and state received successfully")
                return city + "-" + state
            if county_city and state:
                spinner.succeed("City and state received successfully")
                return county_city + "-" + state
            spinner.fail("No city and state found for these coordinates")
            return None
        else:
            url = f"{NOMINATIM_REVERSE_URL}?format=jsonv2&lat={latitude}&lon={longitude}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            if not isinstance(data, dict) or 'address' not in data:
                spinner.fail("Invalid response data format")
                return None

            try:
                city = data['address'].get('city') or data['address'].get('town') or data['address'].get('village')
                state = data['address'].get('state')
            except (KeyError, TypeError, AttributeError):
                spinner.fail("Error extracting city/state from response")
                return None

            if city and state:
                city_state = f"{city}-{state}"
                spinner.succeed("City and state received successfully")
                return city_state
            spinner.fail("No city and state found for these coordinates")
            return None
    except Exception as e:
        spinner.fail(f"Error getting city and state: {e}")
        return None
    finally:
        spinner.stop()

def generate_zillow_urls(arg):
    """
    Generates Zillow URLs for sale and rent listings.

    Args:
        county+state or city+state: to search.

    Returns:
        Tuple of (sale_url, rent_url)
    """
    encoded_arg = quote_plus(arg)
    zillow_url = f"https://www.zillow.com/homes/for_sale/{encoded_arg}"
    return zillow_url

def generate_flightradar24_url(station_id):
    """
    Generates a Flightradar24 URL for the given station ID.
    Args:
        station_id: The station ID of the location.
    Returns:
        A string containing the Flightradar24 URL.
    """
    return f"https://www.flightradar24.com/airport/{station_id}"

def _fetch_noaa_data(latitude, longitude, endpoint):
    """
    Fetches data from the NOAA API.

    Args:
        latitude: The latitude of the location.
        longitude: The longitude of the location.
        endpoint: The specific NOAA API endpoint (e.g., 'forecast', 'forecastHourly').

    Returns:
        A dictionary or list containing the API response, or None if the API call fails.
    """
    spinner = Halo(text=f'Fetching data from NOAA API...', spinner='dots')
    try:
        spinner.start()
        point_url = f"https://api.weather.gov/points/{latitude},{longitude}"
        point_response = requests.get(point_url)
        point_response.raise_for_status()
        point_data = point_response.json()

        forecast_url = point_data['properties'][endpoint]
        forecast_response = requests.get(forecast_url)
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()
        spinner.succeed(f"Data fetched successfully from NOAA API.")
        return forecast_data['properties']['periods'] if endpoint in ['forecast', 'forecastHourly'] else forecast_data['properties']
    except requests.exceptions.RequestException as e:
        spinner.fail(f"Error during NOAA API request: {e}")
        return None
    finally:
        spinner.stop()

def get_current_conditions(latitude, longitude):
    """
    Fetches current weather conditions from the NOAA API.

    Args:
        latitude: The latitude of the location.
        longitude: The longitude of the location.

    Returns:
        A dictionary containing the current weather conditions, or None if the API call fails.
    """
    forecast_data = _fetch_noaa_data(latitude, longitude, 'forecast')
    return forecast_data[0] if forecast_data else None

def get_extended_forecast(latitude, longitude):
    """
    Fetches extended weather forecast from the NOAA API.

    Args:
        latitude: The latitude of the location.
        longitude: The longitude of the location.

    Returns:
        A list of dictionaries containing the extended weather forecast, or None if the API call fails.
    """
    data = _fetch_noaa_data(latitude, longitude, 'forecast')
    return data if data else None

def get_short_conditions(latitude, longitude):
    """
    Fetches brief weather conditions from the NOAA API.

    Args:
        latitude: The latitude of the location.
        longitude: The longitude of the location.

    Returns:
        A dictionary containing the detailed weather conditions, or None if the API call fails.
    """
    data = _fetch_noaa_data(latitude, longitude, 'forecast')
    return data[0] if data else None



def format_time(iso_time):
    """
    Formats an ISO time string to a more user-friendly format with timezone.

    Args:
        iso_time: An ISO formatted time string.

    Returns:
        A formatted time string with timezone (e.g., "10:00 AM EDT").
    """
    utc_time = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
    eastern_tz = pytz.timezone('America/New_York')
    eastern_time = utc_time.astimezone(eastern_tz)
    return eastern_time.strftime("%I:%M %p %Z")

def convert_to_local_time(timestamp_ms=None, dt=None):
    """
    Converts a timestamp (in milliseconds since epoch) or datetime object to the user's local time.
    
    Args:
        timestamp_ms: Timestamp in milliseconds since epoch (USGS format).
        dt: A datetime object to convert (alternative to timestamp_ms).
        
    Returns:
        A formatted string with the local time and date.
    """
    if timestamp_ms is not None:
        # Convert milliseconds to seconds for datetime.fromtimestamp
        dt = datetime.fromtimestamp(timestamp_ms / 1000)
    
    # Get the local timezone
    local_timezone = datetime.now().astimezone().tzinfo
    
    # Convert to local time
    local_time = dt.replace(tzinfo=pytz.UTC).astimezone(local_timezone)
    
    # Format with date and time
    return local_time.strftime("%Y-%m-%d %I:%M:%S %p %Z")

def convert_kmh_to_mph(kmh):
    """
    Converts kilometers per hour to miles per hour.

    Args:
        kmh: Speed in kilometers per hour.

    Returns:
        Speed in miles per hour.
    """
    if kmh is None:
        return None
    return round(kmh * 0.621371, 2)

def convert_temperature(celsius_temperature_data):
    """
    Converts a Celsius temperature value to Fahrenheit.

    Args:
        celsius_temperature_ A dictionary containing the temperature value and unitCode in Celsius.

    Returns:
        A dictionary containing the temperature value in Fahrenheit and the updated unitCode.
    """
    if celsius_temperature_data and celsius_temperature_data.get('value') is not None:
        value = celsius_temperature_data['value']
        celsius_temperature_data['value'] = round(value * 9/5 + 32, 2)  # Convert Celsius to Fahrenheit
        celsius_temperature_data['unitCode'] = 'F'  # Update unit code to Fahrenheit
    else:
        celsius_temperature_data['value'] = None
        celsius_temperature_data['unitCode'] = ""
    return celsius_temperature_data

def get_nearest_stations(latitude, longitude):
    """
    Fetches weather conditions for the 4 nearest weather stations from the NOAA API.

    Args:
        latitude: The latitude of the location.
        longitude: The longitude of the location.

    Returns:
        A list of dictionaries containing the weather conditions for the nearest stations, or None if the API call fails.
    """

    spinner = Halo(text='Fetching nearest stations...', spinner='dots')
    try:
        spinner.start()
        # NOAA API requires coordinates to be in a specific format
        stations_url = f"https://api.weather.gov/points/{latitude},{longitude}/stations"
        stations_response = requests.get(stations_url)
        stations_response.raise_for_status()
        stations_data = stations_response.json()

        stations = stations_data['features'][:4]

        station_forecasts = []
        for station in stations:
            station_id = station['properties']['stationIdentifier']
            observation_url = f"https://api.weather.gov/stations/{station_id}/observations/latest"
            observation_response = requests.get(observation_url)
            observation_response.raise_for_status()
            observation_data = observation_response.json()

            if observation_data is not None:  # Check if observation_data is not None
                temperature = observation_data['properties']['temperature']
                if temperature:
                    temperature = convert_temperature(temperature)
                    temperature_value = temperature['value']
                    temperature_unit = temperature['unitCode']
                else:
                    temperature_value = None
                    temperature_unit = None

                wind_speed = observation_data['properties']['windSpeed']
                wind_speed_value = convert_kmh_to_mph(wind_speed['value'])
                wind_speed_unit = "mph"  # Assuming mph is the target unit for conversion

                wind_direction = observation_data['properties']['windDirection']
                wind_direction_value = wind_direction['value'] if wind_direction else None

                latitude = station['geometry']['coordinates'][1]
                longitude = station['geometry']['coordinates'][0]
                address_map_url = generate_google_maps_url(latitude, longitude, "")

                station_forecasts.append({
                    'name': station['properties']['name'],
                    'station_id': station_id,
                    'address_map_url': address_map_url,
                    'temperature': f"{temperature_value}" if temperature_value is not None else None,
                    'temperature_unit': temperature_unit,
                    'wind_speed': f"{wind_speed_value} {wind_speed_unit}" if wind_speed_value is not None else None,
                    'wind_direction': wind_direction_value
                })
            else:
                # Handle the case where observation data is None, e.g., by skipping the station
                print(f"Could not retrieve observation data for station: {station['properties']['name']}")

        spinner.succeed("Weather for nearest stations fetched successfully.")
        return station_forecasts
    except requests.exceptions.RequestException as e:
        spinner.fail(f"Error during NOAA API request: {e}")
        return None
    finally:
        spinner.stop()

def get_hourly_forecast(latitude, longitude):
    """
    Fetches hourly weather forecast from the NOAA API.

    Args:
        latitude: The latitude of the location.
        longitude: The longitude of the location.

    Returns:
        A list of dictionaries containing the hourly weather forecast, or None if the API call fails.
    """
    return _fetch_noaa_data(latitude, longitude, 'forecastHourly')

def get_active_alerts(latitude, longitude):
    """
    Fetches active weather alerts from the NOAA API.

    Args:
        latitude: The latitude of the location.
        longitude: The longitude of the location.

    Returns:
        A list of dictionaries containing active alerts, or None if the API call fails.
    """
    spinner = Halo(text='Fetching active weather alerts...', spinner='dots')
    try:
        spinner.start()
        alerts_url = f"https://api.weather.gov/alerts/active?point={latitude},{longitude}"
        response = requests.get(alerts_url)
        response.raise_for_status()
        alerts_data = response.json()
        spinner.succeed("Active weather alerts fetched successfully.")
        return alerts_data['features']
    except requests.exceptions.RequestException as e:
        spinner.fail(f"Error during NOAA API request for alerts: {e}")
        return None
    finally:
        spinner.stop()

def get_station_weather(station_data):
    """
    Fetches weather conditions for the specified airports from the NOAA API.

    Args:
        station_data: A list of tuples containing the airport code and name.

    Returns:
        A list of dictionaries containing the weather conditions for the specified airports.
    """
    station_weather = []

    for station_id, name in station_data:
        station_payload = {'station_id': station_id, 'labelled_name': name}

        spinner = Halo(text=f'Fetching metadata for station {station_id}...', spinner='dots')
        spinner.start()
        # Fetch station metadata
        try:
            station_url = f"https://api.weather.gov/stations/{station_id}"
            station_response = requests.get(station_url)
            station_response.raise_for_status()
            station_data = station_response.json()

            station_payload['station_name'] = station_data['properties']['name']
            station_payload['timezone'] = station_data['properties']['timeZone']
            station_payload['latitude'] = station_data['geometry']['coordinates'][1]
            station_payload['longitude'] = station_data['geometry']['coordinates'][0]
            spinner.succeed(f"Metadata fetched for station {station_id}.")
        except Exception as e:
            spinner.fail(f"Failed to fetch metadata for station {station_id}: {e}")
            continue  # Skip to the next station
        finally:
            spinner.stop()

        # Fetch observation data
        spinner = Halo(text=f'Fetching observation data for station {station_id}...', spinner='dots')
        spinner.start()        #
        try:
            observation_url = f"https://api.weather.gov/stations/{station_id}/observations/latest"
            observation_response = requests.get(observation_url)
            observation_response.raise_for_status()
            observation_data = observation_response.json()

            temperature = observation_data['properties']['temperature']
            if temperature:
                temperature = convert_temperature(temperature)
                station_payload['temperature'] = temperature['value']
                station_payload['temperature_unit'] = temperature['unitCode']
            else:
                station_payload['temperature'] = None
                station_payload['temperature_unit'] = None

            wind_speed = observation_data['properties']['windSpeed']
            station_payload['wind_speed'] = f"{convert_kmh_to_mph(wind_speed['value'])} mph" if wind_speed and wind_speed['value'] is not None else None

            wind_direction = observation_data['properties']['windDirection']
            station_payload['wind_direction'] = wind_direction['value'] if wind_direction else None

            station_payload['current_conditions'] = observation_data['properties']['textDescription']
            spinner.succeed(f"Observation data fetched for station {station_id}.")
        except Exception as e:
            spinner.fail(f"Failed to fetch observation data for station {station_id}: {e}")
            station_payload['temperature'] = None
            station_payload['temperature_unit'] = None
            station_payload['wind_speed'] = None
            station_payload['wind_direction'] = None
            station_payload['current_conditions'] = None
        finally:
            spinner.stop()

        # Fetch forecast data
        spinner = Halo(text=f'Fetching forecast data for station {station_id}...', spinner='dots')
        spinner.start()        #
        try:
            if station_payload['latitude'] is not None and station_payload['longitude'] is not None:
                point_url = f"https://api.weather.gov/points/{station_payload['latitude']},{station_payload['longitude']}"
                point_response = requests.get(point_url)
                point_response.raise_for_status()
                point_data = point_response.json()

                forecast_url = point_data['properties']['forecast']
                forecast_response = requests.get(forecast_url)
                forecast_response.raise_for_status()
                forecast_data = forecast_response.json()

                station_payload['forecast'] = forecast_data['properties']['periods'][0]['detailedForecast']
                spinner.succeed(f"Forecast data fetched for station {station_id}.")
            else:
                raise ValueError("Latitude and longitude are missing.")
        except Exception as e:
            spinner.fail(f"Failed to fetch forecast data for station {station_id}: {e}")
            station_payload['forecast'] = None
        finally:
            spinner.stop()

        # Generate URLs
        try:
            if station_payload['latitude'] is not None and station_payload['longitude'] is not None:
                station_payload['address_map_url'] = generate_google_maps_url(
                    station_payload['latitude'], station_payload['longitude'], ""
                )
                station_payload['airports_url'] = generate_flightradar24_url(station_id)
            else:
                station_payload['address_map_url'] = None
                station_payload['airports_url'] = None
        except Exception as e:
            print(f"Failed to generate URLs for station {station_id}: {e}")
            station_payload['address_map_url'] = None
            station_payload['airports_url'] = None

        # Append the station payload to the results
        station_weather.append(station_payload)

    return station_weather

def print_zillow(lat, lon, browser, census):

    # Get county and state and generate Zillow URL
    county_state = get_county_state_from_latlon(lat, lon)
    if county_state:
        zillow_county_state_url = generate_zillow_urls(county_state)
        print(f"\nZillow URL for {county_state}:")
        print(f"{zillow_county_state_url}\n")

        if browser:
            chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))
            chrome = webbrowser.get('chrome')
            if chrome:
                subprocess.run([chrome_path, zillow_county_state_url], stdout=subprocess.DEVNULL)
            else:
                notify_chrome_missing()

    # Get city and state and generate Zillow URL
    city_state = get_city_state_from_latlon(lat, lon, use_census_api=census)
    if city_state:
        zillow_city_state_url = generate_zillow_urls(city_state)
        print(f"\nZillow URL for {city_state}:")
        print(f"{zillow_city_state_url}\n")

        if browser:
            chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))
            chrome = webbrowser.get('chrome')
            if chrome:
                subprocess.run([chrome_path, zillow_city_state_url], stdout=subprocess.DEVNULL)
            else:
                notify_chrome_missing()

def print_station_forecasts(station_weather, browser=False, census=False):
    if station_weather:
        for station in station_weather:
            print(f"\nLatitude: {station['latitude']}, Longitude: {station['longitude']}")
            
        print("\nAirport Weather Conditions:\n")

        for station in station_weather:
            print(f"Station ID: {station['station_id']}")
            print(f"Labeled as: {station['labelled_name']}")
            print(f"Station Name: {station['station_name']}")
            print(f"Temperature: {station['temperature']} {station['temperature_unit']}")
            print(f"Wind Speed: {station['wind_speed']}")
            print(f"Wind Direction: {station['wind_direction']}")
            print("\n")
            print(f"{station['address_map_url']}")
            print(f"{station['airports_url']}")
            print("\n")
            print(f"Current Conditions: {station['current_conditions']}")
            print(f"Forecast: {station['forecast']}")
            print("\n")
            print(f"https://forecast.weather.gov/MapClick.php?lat={station['latitude']}&lon={station['longitude']}")
            print("\n")
            print_zillow(station['latitude'], station['longitude'], browser, census)

            if browser:
                chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))
                chrome = webbrowser.get('chrome')

                if chrome:
                    # Open 7-day NOAA forecast URL
                    forecast_url = f"https://forecast.weather.gov/MapClick.php?lat={station['latitude']}&lon={station['longitude']}"
                    if forecast_url:
                        subprocess.run([chrome_path, forecast_url], stdout=subprocess.DEVNULL)

                    # Open Flightradar24 URL
                    if station['airports_url']:
                        subprocess.run([chrome_path, station['airports_url']], stdout=subprocess.DEVNULL)

                    # Open Google Maps URL
                    if station['address_map_url']:
                        subprocess.run([chrome_path, station['address_map_url']], stdout=subprocess.DEVNULL)
                else:
                    notify_chrome_missing()



    else:
        print("No airport data available to print.")

def airports_menu(args):

    spinner = Halo(text='Reading airport data from file...', spinner='dots')
    spinner.start()
    try:
        full_airports_path = os.path.join(DATA_DIR, AIRPORTS_FILE)
        with open(full_airports_path, 'r') as file:
            station_ids = []
            for line in file:
                line = line.strip()
                parts = line.split(',')
                if len(parts) == 3:
                    airport_code, airport_name, include_in_api  = parts
                    include_in_api = include_in_api.strip().upper() == 'T'
                    station_ids.append({
                        'code': airport_code.strip(),
                        'name': airport_name.strip(),
                        'include_in_api': include_in_api
                    })

        if not station_ids:
            spinner.fail("No airport data found in file. Please add airport codes on new lines in the airports.txt file. e.g., KBZN")
            return None

        spinner.succeed("Airport data read successfully.")

    except FileNotFoundError:
        spinner.fail("Airport data file not found.")
        return None
    finally:
        spinner.stop()

    try:

        spinner = Halo(text='Filtering airports for API calls...', spinner='dots')
        station_data = [(station['code'], station['name']) for station in station_ids if station['include_in_api']]
        if not station_data:
            spinner.fail("No airports are marked for API calls. Please set the third field to 'T' for the airports you want to include.")
            return None
        else:
            spinner.succeed("Airports filtered successfully.")

        station_weather = get_station_weather(station_data)
        spinner.succeed("Airport weather data fetched successfully.")
        print_station_forecasts(station_weather, browser=args.browser, census=args.census)
    except Exception as e:
        print(f"Error getting airport weather data: {e}")
        return None

def address_menu(args):
    try:
        stored_addresses = load_addresses()
        latitude = None
        longitude = None
        matched_address = None

        if stored_addresses:
            # Sort addresses by state code (assumes state code is the second-to-last element in the address)
            sorted_addresses = sorted(stored_addresses, key=lambda addr: addr.split(",")[-2].strip() if len(addr.split(",")) > 1 else "")

            print("\nPreviously entered addresses (sorted by state code):")
            for i, address in enumerate(sorted_addresses):
                print(f"{i + 1}. {address}")
            print("N. Enter a new address")
            print("Q. Return to the previous menu")

            while True:
                try:
                    choice = input("Choose an option: ")
                    if choice.upper() == 'N':
                        address = input("Enter a street address: ")
                        break
                    elif choice.upper() == 'Q':
                        return  # Return to the previous menu
                    elif choice.isdigit() and 1 <= int(choice) <= len(sorted_addresses):
                        address = sorted_addresses[int(choice) - 1]
                        break
                    else:
                        print("Invalid choice. Please try again.")
                except (KeyboardInterrupt, EOFError):
                    print("\n\nExiting the program... Goodbye!")
                    exit(0)
        else:
            address = input("\nEnter a street address: ")

        latitude, longitude, matched_address = geocode_address(address, geocoder=args.geocoder)

        if latitude is None or longitude is None:
            print("\nAddress not found. Please try again.\n")
            return

        if matched_address and matched_address not in stored_addresses:
            stored_addresses.append(matched_address)
            save_addresses(stored_addresses)

        print(f"\nMatched Address: {matched_address}")
        print(f"Latitude: {latitude}, Longitude: {longitude}")
        address_map_url = generate_google_maps_url(latitude, longitude, matched_address)
        print(f"\nGoogle Maps URL for address: {address_map_url}")

        zip_code = matched_address.split(",")[-1].strip() if matched_address else ""
        zillow_url = generate_zillow_urls(zip_code)
        print(f"\nZillow URL: {zillow_url}")

        print("\nGetting forecasted weather conditions...")
        conditions = get_short_conditions(latitude, longitude)
        if conditions:
            print(f"\nHigh Temperature: {conditions['temperature']} {conditions['temperatureUnit']}")
            print(f"Forecasted conditions: {conditions['shortForecast']}")
        else:
            print("\nFailed to retrieve weather conditions.")

        print("\nNOAA forecast webpage for this location:")
        print(f"https://forecast.weather.gov/MapClick.php?lat={latitude}&lon={longitude}")

        if args.browser:
            chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))

            chrome = webbrowser.get('chrome')
            if chrome:
                subprocess.run([chrome_path, zillow_url], stdout=subprocess.DEVNULL)
                subprocess.run([chrome_path, f"https://forecast.weather.gov/MapClick.php?lat={latitude}&lon={longitude}"], stdout=subprocess.DEVNULL)
                subprocess.run([chrome_path, address_map_url], stdout=subprocess.DEVNULL)
            else:
                notify_chrome_missing()

        while True:
            print("\nOptions:")
            print("1. Get Detailed Conditions")
            print("2. Get Extended Forecast")
            print("3. Get Hourly Forecast")
            print("4. Get Weather for Nearest Stations")
            print("5. Get Active Weather Alerts")
            print("6. Get Weather for a Different Location")
            print("7. Return to Main Menu")
            try:
                choice = input("Enter your choice: ")

                if choice == '1':
                    print("\nGetting detailed current conditions...")
                    conditions = get_current_conditions(latitude, longitude)
                    if conditions:
                        print(f"\nCurrent Conditions: {conditions['name']}")
                        print(f"Temperature: {conditions['temperature']} {conditions['temperatureUnit']}")
                        print(f"Short Forecast: {conditions['shortForecast']}")
                        print(f"Wind Speed: {conditions['windSpeed']}")
                        print(f"Wind Direction: {conditions['windDirection']}")
                        value = conditions.get('probabilityOfPrecipitation', {}).get('value')
                        print(f"Precipitation Probability: {value}%") if value is not None else print("Precipitation Probability: N/A")
                        print(f"Detailed forecast: {conditions['detailedForecast']}")
                    else:
                        print("Failed to retrieve current conditions.")
                elif choice == '2':
                    print("Getting extended forecast...")
                    forecast = get_extended_forecast(latitude, longitude)
                    if forecast:
                        for period in forecast:
                            print(f"\nForecast for: {period['name']}")
                            print(f"Temperature: {period['temperature']} {period['temperatureUnit']}")
                            print(f"Detailed Forecast: {period['detailedForecast']}")
                            print("-" * 20)
                    else:
                        print("Failed to retrieve extended forecast.")
                elif choice == '3':
                    print("Getting hourly forecast...")
                    hourly_forecast = get_hourly_forecast(latitude, longitude)
                    if hourly_forecast:
                        for period in hourly_forecast:
                            formatted_time = format_time(period['startTime'])
                            print(f"\nHourly Forecast for: {formatted_time}")
                            print(f"Temperature: {period['temperature']} {period['temperatureUnit']}")
                            print(f"Short Forecast: {period['shortForecast']}")
                            print("-" * 20)
                    else:
                        print("Failed to retrieve hourly forecast.")
                elif choice == '4':
                    print("Getting weather for nearest stations...")
                    stations = get_nearest_stations(latitude, longitude)
                    if stations:
                        print("\n")

                        for station in stations:
                            print(f"Station Name: {station['name']}")
                            print(f"Station ID: {station['station_id']}")
                            print(f"Temperature: {station['temperature']} {station['temperature_unit']}")
                            print(f"Wind Speed: {station['wind_speed']}")
                            print(f"Wind Direction: {station['wind_direction']}")
                            print(f"Google Maps URL for station: {station['address_map_url']}")
                            print("-" * 20)

                            if args.browser:
                                chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                                webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))

                                chrome = webbrowser.get('chrome')
                                if chrome:
                                    subprocess.run([chrome_path, station['address_map_url']], stdout=subprocess.DEVNULL)
                                else:
                                    notify_chrome_missing()
                    else:
                        print("Failed to retrieve weather for nearest stations.")
                elif choice == '5':
                    print("Getting active weather alerts...")
                    alerts = get_active_alerts(latitude, longitude)
                    if alerts:
                        print("\nActive Weather Alerts:")
                        for alert in alerts:
                            props = alert['properties']
                            print(f"Headline: {props['headline']}")
                            print(f"Description: {props['description']}")
                            print(f"Severity: {props['severity']}")
                            print(f"Urgency: {props['urgency']}")
                            print(f"Effective: {format_time(props['effective'])}")
                            print(f"Expires: {format_time(props['expires'])}")
                            print("-" * 70)
                    else:
                        print("No active weather alerts for this location.")
                elif choice == '6':
                    stored_addresses = load_addresses()
                    if stored_addresses:
                        # Sort addresses by state code (assumes state code is the second-to-last element in the address)
                        sorted_addresses = sorted(stored_addresses, key=lambda addr: addr.split(",")[-2].strip() if len(addr.split(",")) > 1 else "")

                        print("\nPreviously entered addresses (sorted by state code):")
                        for i, address in enumerate(sorted_addresses):
                            print(f"{i + 1}. {address}")
                        print("N. Enter a new address")
                        print("Q. Return to the previous menu")

                        while True:
                            try:
                                choice = input("Choose an option: ")
                                if choice.upper() == 'N':
                                    address = input("Enter a street address: ")
                                    break
                                elif choice.upper() == 'Q':
                                    return  # Return to the previous menu
                                elif choice.isdigit() and 1 <= int(choice) <= len(sorted_addresses):
                                    address = sorted_addresses[int(choice) - 1]
                                    break
                                else:
                                    print("Invalid choice. Please try again.")
                            except (KeyboardInterrupt, EOFError):
                                print("\n\nExiting the program... Goodbye!")
                                exit(0)
                    else:
                        address = input("Enter a street address: ")

                    latitude, longitude, matched_address = geocode_address(address, geocoder=args.geocoder)
                    if latitude is None or longitude is None:
                        print("\nAddress not found for the new location. Please try again.\n")
                        continue

                    if matched_address and matched_address not in stored_addresses:
                        stored_addresses.append(matched_address)
                        save_addresses(stored_addresses)

                    print(f"Matched Address: {matched_address}")
                    print(f"Latitude: {latitude}, Longitude: {longitude}")
                    address_map_url = generate_google_maps_url(latitude, longitude, matched_address)
                    print(f"\nGoogle Maps URL for address: {address_map_url}")

                    zip_code = matched_address.split(",")[-1].strip() if matched_address else ""
                    zillow_url = generate_zillow_urls(zip_code)
                    print(f"\nZillow URL: {zillow_url}")

                    print("\nGetting forecasted weather conditions...")
                    conditions = get_short_conditions(latitude, longitude)
                    if conditions:
                        print(f"\nHigh Temperature: {conditions['temperature']} {conditions['temperatureUnit']}")
                        print(f"Forecasted Conditions: {conditions['shortForecast']}")
                    else:
                        print("\nFailed to retrieve weather conditions.")

                    if args.browser:
                        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                        webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))

                        chrome = webbrowser.get('chrome')
                        if chrome:
                            subprocess.run([chrome_path, f"https://forecast.weather.gov/MapClick.php?lat={latitude}&lon={longitude}"], stdout=subprocess.DEVNULL)
                            subprocess.run([chrome_path, address_map_url], stdout=subprocess.DEVNULL)
                            subprocess.run([chrome_path, zillow_url], stdout=subprocess.DEVNULL)
                        else:
                            notify_chrome_missing()
                elif choice == '7':
                    print("\n Returning to main menu...")
                    return
                else:
                    print("Invalid choice. Please try again.")
            except (KeyboardInterrupt, EOFError):
                print("\n\nExiting the program... Goodbye!")
                exit(0)
    except (KeyboardInterrupt, EOFError):
        print("\n\nExiting the program... Goodbye!")
        exit(0)

def airport_search(args):
    """Search airports by wildcard"""
    full_airports_download_path = os.path.join(DATA_DIR, AIRPORTS_DOWNLOAD_CSV)
    # Check if airports_download.csv exists
    if not os.path.exists(full_airports_download_path):
        print("Airport database not found. Downloading...")
        airport_download(args, print_results=False)  # Include args here

    # Load airport data
    airports_df = pd.read_csv(full_airports_download_path)

    # Get search term
    try:
        search_term = input("\nEnter airport code, state, municipality, or name wildcard (use * for any characters): ").strip().upper()
    except (KeyboardInterrupt, EOFError):
        print("\n\nExiting the program... Goodbye!")
        exit(0)

    # Convert wildcard to regex
    search_regex = search_term.replace('*', '.*')

    # Search both code, name, municipality, and state
    matches = airports_df[
        (airports_df['ident'].str.upper().str.contains(search_regex)) |
        (airports_df['name'].str.upper().str.contains(search_regex)) |
        (airports_df['municipality'].str.upper().str.contains(search_regex)) |
        (airports_df['iso_region'].str.upper().str.contains(search_regex))
    ].copy()  # Explicitly create a copy to avoid SettingWithCopyWarning

    if matches.empty:
        print("No matching airports found.")
        return

    # Sort by iso region, then municipality (second value in parentheses)
    matches.sort_values(by=['iso_region', 'municipality', 'name'], ascending=True, inplace=True)

    # Replace NaN values with "N/A" in the relevant columns
    matches.fillna({
        'ident': 'N/A',
        'name': 'N/A',
        'iso_region': 'N/A',
        'municipality': 'N/A'
    }, inplace=True)

    # Let user select
    while True:
        # Display matches with numbers
        print("\nMatching airports: (sorted by iso region, then municipality)")
        for i, (_, row) in enumerate(matches.iterrows()):
            print(f"{i+1}. {row['ident']} - {row['name']} ({row['iso_region']}, {row['municipality']})")

        try:
            choice = input("\nEnter number to select airport (or 'q' to quit): ")
            if choice.lower() == 'q':
                return

            choice = int(choice)
            if 1 <= choice <= len(matches):
                selected = matches.iloc[choice-1]
                station_id = selected['ident']
                name = selected['name']

                # Get weather for selected airport
                station_weather = get_station_weather([(station_id, name)])
                print_station_forecasts(station_weather, browser=args.browser, census=args.census)

                # After showing weather, give options
                while True:
                    print("\nOptions:")
                    print("1. Select another airport from this list")
                    print("2. Search again")
                    print("3. Return to main menu")
                    try:
                        choice = input("Enter your choice: ")

                        if choice == '1':
                            break  # Break out of options menu to show airport list again
                        elif choice == '2':
                            return airport_search(args)  # Start new search
                        elif choice == '3':
                            return  # Return to main menu
                        else:
                            print("Invalid choice. Please try again.")
                    except (KeyboardInterrupt, EOFError):
                        print("\n\nExiting the program... Goodbye!")
                        exit(0)

                # If we broke out of options menu with choice 1, continue outer loop
                continue

            print("Invalid choice. Please try again.")
        except ValueError:
            print("Please enter a valid number or 'q' to quit.")
        except (KeyboardInterrupt, EOFError):
            print("\n\nExiting the program... Goodbye!")
            exit(0)

def airport_download(args, print_results=True):
    """
    download a list of airports
    randomly pick 5 airports
    call the get_station_weather function
    """

    # ask user if they want to filter by scheduled flights
# Ask the user if they want to filter by scheduled service
    while True:
        print("Do you want to filter by airports that provide scheduled service?")
        try:
            filter_by_scheduled = input("Enter 1 for scheduled service, 2 for no: ").strip()

            if filter_by_scheduled in ['1', '2']:
                break
            else:
                print("Invalid input. Please enter 1 or 2.")
        except (KeyboardInterrupt, EOFError):
            print("\n\nExiting the program... Goodbye!")
            exit(0)

    spinner = Halo(text='Downloading airport data from NOAA...', spinner='dots')
    try:
        spinner.start()
        airports_url = "https://davidmegginson.github.io/ourairports-data/airports.csv"

        # Create an SSL context using certifi's CA bundle
        ssl_context = ssl.create_default_context(cafile=certifi.where())

        # Download the CSV file
        with urllib.request.urlopen(airports_url, context=ssl_context) as response:
            csv_content = response.read()
            full_airports_download_path = os.path.join(DATA_DIR, AIRPORTS_DOWNLOAD_CSV)
            with open(full_airports_download_path, 'wb') as file:
                file.write(csv_content)
            airports_df = pd.read_csv(io.StringIO(csv_content.decode('utf-8')))


            filtered_airports_df = airports_df[
                (airports_df['ident'].str.startswith('K') |  # Contiguous US airports
                airports_df['ident'].str.startswith('P') |  # Pacific region (Hawaii, Alaska, Guam, etc.)
                airports_df['ident'].str.startswith('T')) &  # Starts with 'K' which is the prefix for US airports
                (airports_df['ident'].str.len() == 4) &     # Has exactly 4 characters
                (airports_df['ident'].str.isalpha())        # Contains only alphabetic characters
        ]

            # Apply additional filter for scheduled service if the user selected option 1
            if filter_by_scheduled == '1':
                filtered_airports_df = filtered_airports_df[filtered_airports_df['scheduled_service'] == 'yes']

            # Ensure filtered_airports_df is a DataFrame before calling to_csv
            if isinstance(filtered_airports_df, pd.DataFrame):
                full_airports_download_path = os.path.join(DATA_DIR, AIRPORTS_DOWNLOAD_CSV)
                filtered_airports_df.to_csv(full_airports_download_path, index=False)
            else:
                print("Error: filtered_airports_df is not a DataFrame")
        spinner.succeed("Airport data downloaded successfully.")

    except Exception as e:
        spinner.fail(f"Error downloading airport data: {e}")
        return None
    finally:
        spinner.stop()

    if print_results:

        try:
            spinner = Halo(text='Randomly pick 2 airports...', spinner='dots')
            spinner.start()
            random_airports = filtered_airports_df[['ident', 'name']].dropna().sample(n=2)
            random_airports.rename(columns={'ident': 'station_id'}, inplace=True)
        except Exception as e:
            spinner.fail(f"Error randomizing airport data: {e}")
            return None
        finally:
            spinner.stop()

            # Use 'name' from random_airports DataFrame for robustness
            random_airports_tuples = list(zip(random_airports['station_id'], random_airports['name']))
            station_weather = get_station_weather(random_airports_tuples)
            print_station_forecasts(station_weather, browser=args.browser, census=args.census)

def earthquakes_menu(args):
    """
    Displays a menu for fetching and displaying earthquake data.
    """
    try:
        # Main earthquake search loop
        while True:
            # Ask for magnitude
            magnitude_input = input("\nEnter earthquake magnitude to search for (default 5, or range like 3-9): ").strip()
            
            min_magnitude = 5  # Default
            max_magnitude = None
            
            # Parse input for magnitude or range
            if magnitude_input:
                if "-" in magnitude_input:
                    # Range like 3-9
                    try:
                        parts = magnitude_input.split("-")
                        min_magnitude = float(parts[0])
                        max_magnitude = float(parts[1])
                    except (ValueError, IndexError):
                        print("Invalid range format. Using default magnitude 5.")
                        min_magnitude = 5
                        max_magnitude = None
                else:
                    # Single value
                    try:
                        min_magnitude = float(magnitude_input)
                    except ValueError:
                        print("Invalid magnitude. Using default magnitude 5.")
                        min_magnitude = 5
            
            # Ask for time period
            print("\nSelect time period:")
            print("1. Today")
            print("2. Last 24 hours")
            print("3. Last 48 hours (default)")
            print("4. Last week")
            time_choice = input("Enter your choice (1-4): ").strip()
            
            # Set date range based on user choice
            now = datetime.now()
            if time_choice == '1':
                # Today (midnight to now)
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d")
                current_date = now.strftime("%Y-%m-%d")
                time_description = "today"
            elif time_choice == '2':
                # Last 24 hours
                start_date = (now - timedelta(hours=24)).strftime("%Y-%m-%d")
                current_date = now.strftime("%Y-%m-%d")
                time_description = "in the last 24 hours"
            elif time_choice == '4':
                # Last week
                start_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")
                current_date = now.strftime("%Y-%m-%d")
                time_description = "in the last week"
            else:
                # Default to last 48 hours (yesterday to tomorrow)
                start_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
                current_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
                time_description = "in the last 48 hours"
            
            spinner = Halo(text='Getting USGS data...', spinner='dots')
            spinner.start()
            try:
                # Build URL with magnitude parameters
                url = f"https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime={start_date}&endtime={current_date}&minmagnitude={min_magnitude}"
                if max_magnitude is not None:
                    url += f"&maxmagnitude={max_magnitude}"
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                
                if not data.get('features'):
                    if max_magnitude is not None:
                        print(f"\nNo earthquakes between magnitude {min_magnitude} and {max_magnitude} found today.")
                    else:
                        print(f"\nNo earthquakes of magnitude {min_magnitude} or higher found today.")
                    return
                
                if max_magnitude is not None:
                    print(f"\nEarthquakes between magnitude {min_magnitude} and {max_magnitude} today:")
                else:
                    print(f"\nEarthquakes of magnitude {min_magnitude} or higher today:")
                print("-" * 50)
                print(f"\nUSGS URL: {url}\n")
                
                for feature in data['features']:
                    properties = feature['properties']
                    geometry = feature['geometry']
                    magnitude = properties.get('mag', 'N/A')
                    place = properties.get('place', 'N/A')
                    time_ms = properties.get('time', None)
                    updated_ms = properties.get('updated', None)
                    tz_offset_minutes = properties.get('tz', None)  # Timezone offset in minutes from UTC
                    felt_reports = properties.get('felt', 'N/A')  # Number of felt reports
                    alert_level = properties.get('alert', 'N/A')  # Alert level (e.g., "green", "yellow")
                    significance = properties.get('sig', 'N/A')  # Significance of the event
                    event_type = properties.get('type', 'N/A')  # e.g., "earthquake"
                    title = properties.get('title', 'N/A') # Full title of the event

                    lat, lon = geometry['coordinates'][1], geometry['coordinates'][0]

                    # Convert UTC timestamp to user's local time
                    local_time_str = convert_to_local_time(timestamp_ms=time_ms)
                    
                    # Generate Google Maps URL with a more zoomed-out view
                    maps_url = generate_google_maps_url(lat, lon, "", zoom=5)
                    more_info_url = properties.get('url', 'N/A')

                    print(f"Magnitude: {magnitude}")
                    print(f"Place: {place}")
                    print(f"Time: {local_time_str}")
                    print(f"Latitude: {lat}, Longitude: {lon}")
                    print(f"Google Maps URL: {maps_url}")
                    print(f"More Info: {more_info_url}")

                    if args.browser:
                        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                        webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))
                        chrome = webbrowser.get('chrome')
                        if chrome:
                            subprocess.run([chrome_path, maps_url], stdout=subprocess.DEVNULL)
                            if more_info_url != 'N/A':
                                subprocess.run([chrome_path, more_info_url], stdout=subprocess.DEVNULL)
                        else:
                            notify_chrome_missing()
                            
                    print("-" * 50)               
            except Exception as e:
                print(f"\nError getting earthquake data: {e}")
            finally:
                spinner.stop()
        
        # Post-results menu
            print("\nOptions:")
            print("1. Search for earthquakes again")
            print("2. Return to main menu")
            
            post_choice = input("Enter your choice (1-2): ").strip()
            if post_choice == "2":
                break
            elif post_choice == "1":
                continue
            else:
                print("Invalid choice. Returning to main menu.")
                return
    
    except (KeyboardInterrupt, EOFError):
        print("\n\nExiting the program... Goodbye!")
        exit(0)

# Functions for Tides (adapted from user-provided code)

# Robust state extraction, similar to what was developed before,
# as the simple split might be fragile.
def extract_state_for_tides(matched_address_str):
    """Extracts the state from a matched address string for tide station lookup."""
    if not matched_address_str:
        return None
    try:
        parts = matched_address_str.split(',')
        # Iterate from right to left, looking for a 2-char uppercase state code
        for part_idx in range(len(parts) - 1, -1, -1):
            current_part = parts[part_idx].strip()
            # Check if current_part is "ST"
            if len(current_part) == 2 and current_part.isupper():
                return current_part
            # Check if current_part is "ST ZIP" (e.g., "CA 90210")
            # and extract ST part
            if ' ' in current_part:
                state_candidate = current_part.split(' ')[0]
                if len(state_candidate) == 2 and state_candidate.isupper():
                    # Further check if the part after space is numeric (part of ZIP)
                    zip_candidate = current_part.split(' ')[1]
                    if zip_candidate.isdigit():
                        return state_candidate
        return None  # Fallback if no clear state found
    except Exception:
        return None

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the distance between two points on a sphere using the Haversine formula"""
    R = 6371  # Radius of the Earth in kilometers
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    return distance

def noaa_get_nearest_tide_station(latitude, longitude, matched_address_str, args):
    """Find the nearest NOAA tide station using metadata API"""
    spinner = Halo(text='Finding nearest NOAA tide station...', spinner='dots')
    spinner.start()

    state = extract_state_for_tides(matched_address_str)
    if not state:
        spinner.fail(f"Could not determine state from '{matched_address_str}' to find relevant tide stations.")
        return None

    try:
        # Added type=tidepredictions to filter for stations with tide prediction data
        url = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json?type=tidepredictions&format=json"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        state_stations = [station for station in data.get('stations', []) if station.get('state') == state]
        
        if not state_stations:
            spinner.warn(f"No NOAA tide stations with prediction data found in {state}.")
            return None
            
        nearest_station_id = None
        min_distance = float('inf')
        
        for station in state_stations:
            try:
                station_lat = float(station['lat'])
                station_lon = float(station.get('lon', station.get('lng'))) # Handle both 'lon' and 'lng'
                distance = haversine_distance(latitude, longitude, station_lat, station_lon)
                if distance < min_distance:
                    min_distance = distance
                    nearest_station_id = station['id']
            except (ValueError, TypeError, KeyError):
                continue # Skip station if lat/lon is invalid or missing
        
        if nearest_station_id:
            spinner.succeed(f"Found nearest tide station: {nearest_station_id} in {state} ({min_distance:.2f} km away).")
            return nearest_station_id
        else:
            spinner.warn(f"Could not find a suitable tide station in {state} with valid coordinates among those with tide predictions.")
            return None
            
    except requests.exceptions.RequestException as e:
        spinner.fail(f"Error fetching NOAA station data: {e}")
        return None
    except Exception as e:
        spinner.fail(f"An unexpected error occurred while finding nearest station: {e}")
        return None
    finally:
        spinner.stop()

def noaa_get_station_info(station_id, args):
    """Fetch station information from NOAA API for a given station ID"""
    spinner = Halo(text=f'Fetching info for NOAA station {station_id}...', spinner='dots')
    spinner.start()
    try:
        url = f"https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/{station_id}.json?format=json"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        spinner.succeed(f"Station info for {station_id} fetched.")
        return response.json()
    except requests.exceptions.RequestException as e:
        spinner.fail(f"Error fetching station info for {station_id}: {e}")
        return None
    except Exception as e:
        spinner.fail(f"An unexpected error occurred fetching station info for {station_id}: {e}")
        return None
    finally:
        spinner.stop()

def noaa_display_station_info(station_info_data): # Removed args from signature
    """Display NOAA tide station information and return its map URL."""
    if not station_info_data or not station_info_data.get('stations'):
        print("\nNo station information to display.")
        return None

    station = station_info_data['stations'][0] # API returns a list with one station
    print("\nNOAA Tide Station Information:")
    print(f"  Station ID: {station.get('id')}")
    station_name = station.get('name', 'N/A')
    station_state = station.get('state', 'N/A')
    print(f"  Name: {station_name}, {station_state}")
    lat = station.get('lat')
    lon = station.get('lng') 
    print(f"  Coordinates: Lat: {lat}, Lon: {lon}")

    maps_url = None
    if lat and lon:
        maps_url = generate_google_maps_url(lat, lon, "", zoom=15) # Label is empty for coordinate-based marker
        print(f"  Google Maps for station: {maps_url}")
    else:
        print("  (Could not generate Google Maps link for station due to missing coordinates)")
    
    return maps_url # Return the URL (or None), browser opening is handled by caller

def noaa_get_tide_data(station_id, args):
    """Fetch tide data from NOAA API for a given station ID"""
    spinner = Halo(text=f'Fetching tide data for station {station_id}...', spinner='dots')
    spinner.start()
    try:
        today = datetime.today().strftime("%Y%m%d")
        # Get data for today and tomorrow
        tomorrow = (datetime.today() + timedelta(days=1)).strftime("%Y%m%d") 
        
        url = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
        params = {
            "product": "predictions",
            "application": "weather_py_app", # Using a custom application name
            "begin_date": today,
            "end_date": tomorrow,
            "datum": "MLLW", # Mean Lower Low Water
            "station": station_id,
            "time_zone": "lst_ldt", # Local Standard Time / Local Daylight Time
            "units": "english", # Feet
            "interval": "hilo", # High/low tides only
            "format": "json"
        }
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # NOAA API can return 200 OK with an error message in the JSON body
        if "error" in data:
            error_message = data.get("error", {}).get("message", "Unknown API error")
            spinner.fail(f"API error for station {station_id}: {error_message}")
            return None
            
        spinner.succeed(f"Tide data for station {station_id} fetched.")
        return data
    except requests.exceptions.RequestException as e:
        spinner.fail(f"Error fetching tide data for {station_id}: {e}")
        return None
    except Exception as e:
        spinner.fail(f"An unexpected error occurred fetching tide data for {station_id}: {e}")
        return None
    finally:
        spinner.stop()

def noaa_display_tide_data(tide_data):
    """Display tide information"""
    if not tide_data or 'predictions' not in tide_data or not tide_data['predictions']:
        print("\nNo tide predictions available or error in data.")
        # If there was an error, it should have been caught by noaa_get_tide_data
        # This handles cases where predictions list is empty.
        return

    print("\nTide Predictions (Today & Tomorrow):")
    for prediction in tide_data['predictions']:
        try:
            # Time 't' is already in local time (lst_ldt as requested)
            # Format: "YYYY-MM-DD HH:MM"
            time_obj = datetime.strptime(prediction['t'], "%Y-%m-%d %H:%M")
            tide_type = "High Tide" if prediction['type'] == "H" else "Low Tide"
            # Format: 03:30 PM, Monday, May 27, 2024 - High Tide: 5.67 ft
            formatted_time = time_obj.strftime("%I:%M %p, %A, %B %d, %Y")
            print(f"  {formatted_time} - {tide_type}: {prediction['v']} ft")
        except (ValueError, KeyError) as e:
            print(f"  Error parsing prediction data: {prediction}. Error: {e}")

def _handle_tide_logic_for_address(latitude, longitude, matched_address, args):
    """Internal function to handle fetching and displaying tides for a geocoded address."""
    print(f"\n--- Getting Tide Information for: {matched_address} ---")
    print() # Add a newline for separation

    station_id = noaa_get_nearest_tide_station(latitude, longitude, matched_address, args)
    if not station_id:
        return

    station_info = noaa_get_station_info(station_id, args)
    
    station_map_url_to_open = None
    station_name_for_desc = station_id # Default to ID for description

    if station_info:
        # Display station info and get its map URL (without opening it yet)
        station_map_url_to_open = noaa_display_station_info(station_info) # No args passed here
        if station_info.get('stations'):
            station_name_for_desc = station_info['stations'][0].get('name', station_id)
    else:
        print(f"\nCould not retrieve detailed information for station {station_id}.")

    print() 
    tide_data = noaa_get_tide_data(station_id, args)
    if tide_data:
        noaa_display_tide_data(tide_data)
    else:
        print(f"\nCould not retrieve tide predictions for station {station_id}.")

    if args.browser:
        # 1. Open Google Maps for the matched address first
        if latitude is not None and longitude is not None:
            address_map_url = generate_google_maps_url(latitude, longitude, matched_address)
            _open_url_in_browser(address_map_url, args, description=f"Google Maps for address '{matched_address}'")
        
        # 2. Then, open Google Maps for the tide station (if URL is available)
        if station_map_url_to_open:
            _open_url_in_browser(station_map_url_to_open, args, description=f"Google Maps for tide station '{station_name_for_desc}'")

def tides_lookup_new_address(args):
    """Handles tide lookup for a new address."""
    try:
        address_input = input("\nEnter address (street, city, state, zip) or 'Q' to return: ").strip()
        if address_input.lower() == 'q':
            return
        if not address_input:
            print("No address entered.")
            return
    except (KeyboardInterrupt, EOFError):
        print("\n\nOperation cancelled. Returning to Tides Menu.")
        return

    # Spinner logic removed from here as geocode_address handles it
    try:
        latitude, longitude, matched_address = geocode_address(address_input, geocoder=args.geocoder)
        # Assuming geocode_address prints its own success/failure
    except Exception as e:
        # geocode_address should ideally handle its own error printing related to the API call
        # This catch is more for unexpected issues during the call itself, though geocode_address might also raise
        print(f"An unexpected error occurred during geocoding: {e}")
        return

    if latitude is None or longitude is None:
        # Message already printed by geocode_address if it failed to match
        # print("\nAddress not found or geocoding failed. Please try again.")
        return

    print(f"\nMatched Address: {matched_address}")
    print(f"Latitude: {latitude}, Longitude: {longitude}")
    maps_url = generate_google_maps_url(latitude, longitude, matched_address)
    print(f"Google Maps URL: {maps_url}")
    
    # Save address if new and geocoding was successful
    stored_addresses = load_addresses()
    if matched_address and matched_address not in stored_addresses:
        stored_addresses.append(matched_address)
        save_addresses(stored_addresses)
        print(f"(Saved '{matched_address}' to stored addresses.)")

    _handle_tide_logic_for_address(latitude, longitude, matched_address, args)

def tides_select_saved_address(args):
    """Handles tide lookup for a saved address."""
    stored_addresses = load_addresses()
    if not stored_addresses:
        print("\nNo saved addresses found. Please enter a new address first.")
        return

    sorted_addresses = sorted(stored_addresses, key=lambda addr: addr.split(",")[-2].strip() if len(addr.split(",")) > 1 else "")
    print("\nSaved addresses (sorted by state code):")
    for i, addr_str in enumerate(sorted_addresses):
        print(f"{i+1}. {addr_str}")
    print("0. Go back")

    try:
        choice_input = input("\nSelect an address number (or 0 to go back): ").strip()
        choice = int(choice_input)

        if choice == 0:
            return
        if 1 <= choice <= len(sorted_addresses):
            selected_address_str = sorted_addresses[choice-1]
            print(f"\nSelected address: {selected_address_str}")
            print() # Add a newline for separation
            
            # Spinner logic removed from here as geocode_address handles it
            try:
                # Re-geocode to ensure we have lat/lon, though it should be consistent
                latitude, longitude, matched_address = geocode_address(selected_address_str, geocoder=args.geocoder)
                # Assuming geocode_address prints its own success/failure
            except Exception as e:
                # geocode_address should ideally handle its own error printing
                print(f"An unexpected error occurred during geocoding: {e}")
                return

            if latitude is None or longitude is None:
                # Message already printed by geocode_address if it failed
                # print(f"Could not re-geocode saved address: {selected_address_str}")
                return
            
            # Matched address from re-geocoding should ideally be the same as selected_address_str
            # Using the newly geocoded one for consistency in _handle_tide_logic_for_address
            _handle_tide_logic_for_address(latitude, longitude, matched_address, args)
        else:
            print("Invalid selection.")
    except ValueError:
        print("Invalid input. Please enter a number.")
    except (KeyboardInterrupt, EOFError):
        print("\n\nOperation cancelled. Returning to Tides Menu.")
        return

def tides_menu(args):
    """Display and handle tides menu."""
    while True:
        print("\n--- Tides Menu ---")
        print("1. Enter new address for Tides")
        print("2. Select from saved addresses for Tides")
        print("3. Return to Main Menu")
        
        try:
            choice = input("Enter your choice (1-3): ").strip()
            if choice == "1":
                tides_lookup_new_address(args)
            elif choice == "2":
                tides_select_saved_address(args)
            elif choice == "3":
                print("\nReturning to Main Menu...")
                return
            else:
                print("Invalid choice. Please enter 1-3.")
        except (KeyboardInterrupt, EOFError):
            print("\n\nExiting the program... Goodbye!")
            exit(0) # Exit directly as per user's example structure for ^C in sub-menu
        except Exception as e: # Catch any other unexpected errors in this menu
            print(f"An error occurred in the Tides Menu: {e}")
            print("Returning to Main Menu.")
            return

# Utility function to open URL in browser
def _open_url_in_browser(url, args, description="URL"):
    if not args.browser:
        return

    # Ensure the description is user-friendly
    print(f"\nAttempting to open {description} in browser...")
    print(f"URL: {url}")
    try:
        if platform.system() == 'Darwin': # macOS
            chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            if os.path.exists(chrome_path):
                subprocess.run([chrome_path, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            else: 
                webbrowser.open(url) 
                notify_chrome_missing(custom_message="Attempted to open with default browser as Chrome was not found at the standard path.")
        else: # For other OS, use webbrowser.open
            webbrowser.open(url)
    except Exception as e:
        print(f"Could not open browser for {description}: {e}")

def main():


    parser = argparse.ArgumentParser(description="Weather App using US Census & NOAA APIs")
    parser.add_argument('--browser', action='store_true',
                       help='Open weather station URLs in Chrome browser (macOS only)')
    parser.add_argument('--geocoder', choices=['census', 'nominatim'], default='census',
                        help='Choose geocoding service: "census" (default) for US Census API, or "nominatim" for OpenStreetMap Nominatim API')
    # REMOVED API KEY ARGUMENTS AS PER USER REQUEST
    args = parser.parse_args()


    print("Welcome to the Weather App!")
    print("\nThis app uses the following APIs:")

    if args.geocoder == 'census':
        geocode = "US Census"
        use_census = True 
    else:
        geocode = "Nominatim (via OpenCage)" # OpenCage is a common provider for Nominatim
        use_census = False

    print(f"- {geocode} API for geocoding an address")
    print("- NOAA API for weather data (Weather.gov)")
    print("- NOAA API for tide data (TidesandCurrents.noaa.gov)")


    if args.browser and platform.system() != 'Darwin':
        print("\nNote: The --browser option is only supported on macOS. This option will be ignored.")
        args.browser = False

    args.census = use_census 

    # REMOVED API KEY NOTIFICATION AS PER USER REQUEST
    # notify_api_key_status(args) 

    try:
        while True:
            try:
                print("\nMain Menu:")
                print("1. Get specific address weather & more")
                print("2. Get airport weather")
                print("3. Download random airports & get weather")
                print("4. Search airports")
                print("5. Get earthquakes")
                print("6. Get Tides") # New option
                print("7. Exit")      # Adjusted numbering
                choice = input("Enter your choice (1-7): ")
                print("\n")
                if choice == '1':
                    address_menu(args)
                elif choice == '2':
                    airports_menu(args)
                elif choice == '3':
                    airport_download(args, print_results=True)
                elif choice == '4':
                    airport_search(args)
                elif choice == '5':
                    earthquakes_menu(args)
                elif choice == '6': # New Tides Menu
                    tides_menu(args)
                elif choice == '7': # Exit
                    print("\nExiting the program... Goodbye!")
                    break
                else:
                    print("Invalid choice. Please enter a number between 1 and 7.")
            except (KeyboardInterrupt, EOFError):
                print("\n\nExiting the program... Goodbye!")
                exit(0)
    except (KeyboardInterrupt, EOFError):
        print("\n\nExiting the program... Goodbye!")
        exit(0)

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n\nExiting the program... Goodbye!")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
