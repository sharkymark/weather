import requests
import json
from urllib.parse import quote
from halo import Halo
from datetime import datetime
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

ADDRESS_FILE = "addresses.txt"
CENSUS_API_BASE_URL = "https://nominatim.openstreetmap.org/search"
CENSUS_API_KEY = os.getenv("CENSUS_API_KEY")

def notify_api_key_status():
    """Notify if a US Census API key is found."""
    if CENSUS_API_KEY:
        print("\nUS Census API key found and will be used for geocoding API calls.")
    else:
        print("\nNo Census API key found. Geocoding will proceed without it and with rate limits.")

def notify_chrome_missing():
    print("Google Chrome is not installed on your computer. Please download and install it to use the browser feature.")

def load_addresses():
    """Loads previously entered addresses from a file."""
    if os.path.exists(ADDRESS_FILE):
        with open(ADDRESS_FILE, "r") as f:
            return [line.strip() for line in f]
    return []

def save_addresses(addresses):
    """Saves entered addresses to a file."""
    with open(ADDRESS_FILE, "w") as f:
        for address in addresses:
            f.write(address + "\n")

def geocode_address(address):
    """
    Geocodes an address using the Nominatim Geocoder API.

    URLs:
    https://nominatim.openstreetmap.org/search

    Args:
      address: The street address to geocode.

    Returns:
      A tuple containing (latitude, longitude) or None if geocoding fails.
    """
    params = {
        "q": address,
        "format": "json",
        "limit": 1
    }

    spinner = Halo(text='Geocoding address...', spinner='dots')
    try:
        spinner.start()
        headers = {
        'User-Agent': 'Goose-Weather-App/1.0'
    }
        response = requests.get(CENSUS_API_BASE_URL, params=params, headers=headers, verify=False)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        if data:
            latitude = data[0]['lat']
            longitude = data[0]['lon']
            spinner.succeed("Address geocoded successfully.")
            return float(latitude), float(longitude), address
        else:
            spinner.fail("Address could not be matched.")
            return None, None, None
    except requests.exceptions.RequestException as e:
        spinner.fail(f"Error during Nominatim API request: {e}")
        return None, None, None
    finally:
        spinner.stop()

def generate_google_maps_url(latitude, longitude, label):
    """
    Generates a Google Maps URL for the given coordinates.

    Args:
        latitude: The latitude of the location.
        longitude: The longitude of the location.
        label: Label for the place on google maps

    Returns:
        A string containing the Google Maps URL.
    """

    if label == "":
        return f"https://www.google.com/maps/search/{latitude},{longitude}/{latitude},{longitude},15z?t=s"
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
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        spinner.succeed("County and state received successfully")
        return data['County']['name']+ "-" +data['State']['name']
    except Exception as e:
        spinner.fail(f"Error getting county and state: {e}")
        return None
    finally:
        spinner.stop()

def get_city_state_from_latlon(latitude, longitude):
    """
    Gets city from latitude and longitude using US Census API.

    Args:
        latitude: The latitude of the location.
        longitude: The longitude of the location.

    Returns:
        city and state as string or None if not found.

    Example:
    https://geocoding.geo.census.gov/geocoder/geographies/coordinates?x=-156.05056&y=19.74083&benchmark=Public_AR_Current&vintage=Current_Current&format=json

    """
    spinner = Halo(text='Reverse geocoding lat lon for city and state...', spinner='dots')
    try:
        spinner.start()
        url = f"https://geocoding.geo.census.gov/geocoder/geographies/coordinates?x={longitude}&y={latitude}&benchmark=Public_AR_Current&vintage=Current_Current&format=json"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        try:
            city = data['result']['geographies']['Incorporated Places'][0]['BASENAME']
        except (KeyError, IndexError):
            city = None
        try:
            state = data['result']['geographies']['States'][0]['BASENAME']
        except (KeyError, IndexError):
            state = None
        try:
            city_state = data['result']['geographies']['Urban Areas'][0]['BASENAME']
        except (KeyError, IndexError):
            city_state = None
        try:
            county_city = data['result']['geographies']['County Subdivisions'][0]['BASENAME']
        except (KeyError, IndexError):
            county_city = None

        if city_state:
            spinner.succeed("City and state received successfully")
            return city_state
        if city and state:  # Check if city and state are not empty
            spinner.succeed("City and state received successfully")
            return city + "-" + state
        if county_city:
            spinner.succeed("City and state received successfully")
            return county_city + "-" + state
        else:
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

def print_zillow(lat,lon, browser):

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

    '''
    '''
    # Get city and state and generate Zillow URL
    city_state = get_city_state_from_latlon(lat, lon)
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


def print_station_forecasts(station_weather, browser=False):
    if station_weather:
        print("\n\nAirport Weather Conditions:\n")

        for station in station_weather:
            print("-" * 20)
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
            print_zillow(station['latitude'], station['longitude'], browser)

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
        with open('airports.txt', 'r') as file:
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
        print_station_forecasts(station_weather, browser=args.browser)
    except Exception as e:
        print(f"Error getting airport weather data: {e}")
        return None

def address_menu(args):
    try:
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
            address = input("\nEnter a street address: ")

        latitude, longitude, matched_address = geocode_address(address)

        if latitude is None or longitude is None:
            print("\nAddress not found. Please try again.\n")
            main()  # Reshow the main menu
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

                    latitude, longitude, matched_address = geocode_address(address)
                    if latitude is None or longitude is None:
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
    # Check if airports_download.csv exists
    if not os.path.exists('airports_download.csv'):
        print("Airport database not found. Downloading...")
        airport_download(args, print_results=False)  # Include args here

    # Load airport data
    airports_df = pd.read_csv('airports_download.csv')

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
                print_station_forecasts(station_weather, browser=args.browser)

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
            with open('airports_download.csv', 'wb') as file:
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
                filtered_airports_df.to_csv('airports_download.csv', index=False)
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

            random_airports_tuples = list(zip(random_airports['station_id'], airports_df['name']))
            station_weather = get_station_weather(random_airports_tuples)
            print_station_forecasts(station_weather, browser=args.browser)


def main():


    parser = argparse.ArgumentParser(description="Weather App using US Census & NOAA APIs")
    parser.add_argument('--browser', action='store_true',
                       help='Open weather station URLs in Chrome browser (macOS only)')
    args = parser.parse_args()

    print("Welcome to the Weather App!")
    print("This app uses the US Census & NOAA APIs")

    # Check if --browser is enabled on a non-macOS platform
    if args.browser and platform.system() != 'Darwin':
        print("\nNote: The --browser option is only supported on macOS. This option will be ignored.")
        args.browser = False

    notify_api_key_status()

    try:
        while True:
            try:
                print("\nMain Menu:")
                print("1. Get specific address weather")
                print("2. Get airport weather")
                print("3. Download random airports & get weather")
                print("4. Search airports")
                print("5. Exit")
                choice = input("Enter your choice (1-5): ")
                print("\n")
                if choice == '1':
                    address_menu(args)
                elif choice == '2':
                    airports_menu(args)
                elif choice == '3':
                    airport_download(args, print_results=True)  # Ensure args is passed here
                elif choice == '4':
                    airport_search(args)
                elif choice == '5':
                    print("\nExiting the program... Goodbye!")
                    break
                else:
                    print("Invalid choice. Please enter a number between 1 and 5.")
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
