import requests
import json
from geopy.distance import geodesic
from urllib.parse import quote
from halo import Halo
from datetime import datetime
import pytz
import os

ADDRESS_FILE = "addresses.txt"

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
    Geocodes an address using the US Census Geocoder API.

    Args:
      address: The street address to geocode.

    Returns:
      A tuple containing (latitude, longitude) or None if geocoding fails.
    """
    base_url = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
    params = {
        "address": address,
        "benchmark": "Public_AR_Current",
        "format": "json",
    }
    spinner = Halo(text='Geocoding address...', spinner='dots')
    try:
        spinner.start()
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        if data['result']['addressMatches']:
            match = data['result']['addressMatches'][0]
            latitude = match['coordinates']['y']
            longitude = match['coordinates']['x']
            spinner.succeed("Address geocoded successfully.")
            return float(latitude), float(longitude), match['matchedAddress']
        else:
            spinner.fail("Address could not be matched.")
            return None, None, None
    except requests.exceptions.RequestException as e:
        spinner.fail(f"Error during Census API request: {e}")
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
    return f"https://www.google.com/maps/search/?api=1&query={quote(label)}@{latitude},{longitude}"

def get_current_conditions(latitude, longitude):
    """
    Fetches current weather conditions from the NOAA API.

    Args:
        latitude: The latitude of the location.
        longitude: The longitude of the location.

    Returns:
        A dictionary containing the current weather conditions, or None if the API call fails.
    """
    spinner = Halo(text='Fetching current conditions...', spinner='dots')
    try:
        spinner.start()
        # NOAA API requires coordinates to be in a specific format
        point_url = f"https://api.weather.gov/points/{latitude},{longitude}"
        point_response = requests.get(point_url)
        point_response.raise_for_status()
        point_data = point_response.json()

        forecast_url = point_data['properties']['forecast']
        forecast_response = requests.get(forecast_url)
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()

        current_conditions = forecast_data['properties']['periods'][0]
        spinner.succeed("Current conditions fetched successfully.")
        return current_conditions
    except requests.exceptions.RequestException as e:
        spinner.fail(f"Error during NOAA API request: {e}")
        return None
    finally:
        spinner.stop()

def get_extended_forecast(latitude, longitude):
    """
    Fetches extended weather forecast from the NOAA API.

    Args:
        latitude: The latitude of the location.
        longitude: The longitude of the location.

    Returns:
        A list of dictionaries containing the extended weather forecast, or None if the API call fails.
    """
    spinner = Halo(text='Fetching extended forecast...', spinner='dots')
    try:
        spinner.start()
        # NOAA API requires coordinates to be in a specific format
        point_url = f"https://api.weather.gov/points/{latitude},{longitude}"
        point_response = requests.get(point_url)
        point_response.raise_for_status()
        point_data = point_response.json()

        forecast_url = point_data['properties']['forecast']
        forecast_response = requests.get(forecast_url)
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()

        extended_forecast = forecast_data['properties']['periods']
        spinner.succeed("Extended forecast fetched successfully.")
        return extended_forecast
    except requests.exceptions.RequestException as e:
        spinner.fail(f"Error during NOAA API request: {e}")
        return None
    finally:
        spinner.stop()

def get_detailed_conditions(latitude, longitude):
    """
    Fetches detailed weather conditions from the NOAA API.

    Args:
        latitude: The latitude of the location.
        longitude: The longitude of the location.

    Returns:
        A dictionary containing the detailed weather conditions, or None if the API call fails.
    """
    spinner = Halo(text='Fetching detailed conditions...', spinner='dots')
    try:
        spinner.start()
        # NOAA API requires coordinates to be in a specific format
        point_url = f"https://api.weather.gov/points/{latitude},{longitude}"
        point_response = requests.get(point_url)
        point_response.raise_for_status()
        point_data = point_response.json()

        forecast_url = point_data['properties']['forecast']
        forecast_response = requests.get(forecast_url)
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()

        current_conditions = forecast_data['properties']['periods'][0]
        spinner.succeed("Detailed conditions fetched successfully.")
        return current_conditions
    except requests.exceptions.RequestException as e:
        spinner.fail(f"Error during NOAA API request: {e}")
        return None
    finally:
        spinner.stop()

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
    return round(kmh * 0.621371, 2)

# change this function to just convert the temperature to Fahrenheit. the input will be the value of the temperature

def convert_temperature(data):

    value = data['value']
    data['value'] = round(value * 9/5 + 32, 2)  # Convert Celsius to Fahrenheit
    data['unitCode'] = 'F'  # Update unit code to Fahrenheit
    return data

def get_nearest_stations(latitude, longitude):
    """
    Fetches weather conditions for the 2 nearest weather stations from the NOAA API.

    Args:
        latitude: The latitude of the location.
        longitude: The longitude of the location.

    Returns:
        A list of dictionaries containing the weather conditions for the 2 nearest stations, or None if the API call fails.
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

            temperature = observation_data['properties']['temperature']
            temperature = convert_temperature(observation_data['properties']['temperature']) if temperature else None
            temperature_value = temperature['value'] if temperature else None
            temperature_unit = temperature['unitCode'] if temperature else None

            wind_speed = observation_data['properties']['windSpeed']
            wind_speed_value = convert_kmh_to_mph(wind_speed['value']) if wind_speed else None
            wind_speed_unit = "mph"  # Assuming mph is the target unit for conversion

            wind_direction = observation_data['properties']['windDirection']
            wind_direction_value = wind_direction['value'] if wind_direction else None

            station_forecasts.append({
                'name': station['properties']['name'],
                'temperature': f"{temperature_value}" if temperature_value else None,
                'temperature_unit': temperature_unit,
                'wind_speed': f"{wind_speed_value} {wind_speed_unit}" if wind_speed_value else None,
                'wind_direction': wind_direction_value
            })
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
    spinner = Halo(text='Fetching hourly forecast...', spinner='dots')
    try:
        spinner.start()
        # NOAA API requires coordinates to be in a specific format
        point_url = f"https://api.weather.gov/points/{latitude},{longitude}"
        point_response = requests.get(point_url)
        point_response.raise_for_status()
        point_data = point_response.json()

        forecast_url = point_data['properties']['forecastHourly']
        forecast_response = requests.get(forecast_url)
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()

        hourly_forecast = forecast_data['properties']['periods'][:12]
        spinner.succeed("Hourly forecast fetched successfully.")
        return hourly_forecast
    except requests.exceptions.RequestException as e:
        spinner.fail(f"Error during NOAA API request: {e}")
        return None
    finally:
        spinner.stop()

def main():

    print("Welcome to the Weather App!")
    
    stored_addresses = load_addresses()

    if stored_addresses:
        print("\nPreviously entered addresses:")
        for i, address in enumerate(stored_addresses):
            print(f"{i + 1}. {address}")
        print("N. Enter a new address")

        choice = input("Choose an option: ")
        if choice.upper() == 'N':
            address = input("Enter a street address: ")
        elif choice.isdigit() and 1 <= int(choice) <= len(stored_addresses):
            address = stored_addresses[int(choice) - 1]
        else:
            print("Invalid choice. Please try again.")
            return
    else:
        address = input("\nEnter a street address: ")

    latitude, longitude, matched_address = geocode_address(address)

    if latitude is None or longitude is None:
        return

    if matched_address not in stored_addresses:
        stored_addresses.append(matched_address)
        save_addresses(stored_addresses)

    print(f"\nMatched Address: {matched_address}")
    print(f"Latitude: {latitude}, Longitude: {longitude}")
    address_map_url = generate_google_maps_url(latitude, longitude, matched_address)
    print(f"Google Maps URL for address: {address_map_url}")

    while True:
        print("\nOptions:")
        print("1. Get Current Conditions")
        print("2. Get Extended Forecast")
        print("3. Get Hourly Forecast")
        print("4. Get Detailed Conditions")
        print("5. Get Weather for Nearest Stations")
        print("6. Get Weather for a Different Location")
        print("7. Exit")
        choice = input("Enter your choice: ")

        if choice == '1':
            print("Getting current conditions...")
            conditions = get_current_conditions(latitude, longitude)
            if conditions:
                print(f"\nCurrent Conditions: {conditions['name']}")
                print(f"Temperature: {conditions['temperature']} {conditions['temperatureUnit']}")
                print(f"Short Forecast: {conditions['shortForecast']}")
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
            print("Getting detailed conditions...")
            conditions = get_detailed_conditions(latitude, longitude)
            if conditions:
                print(f"\nCurrent Conditions: {conditions['name']}")
                print(f"Temperature: {conditions['temperature']} {conditions['temperatureUnit']}")
                print(f"Precipitation Probability: {conditions.get('probabilityOfPrecipitation', {}).get('value', 'N/A')}")
                print(f"Wind Speed: {conditions['windSpeed']}")
                print(f"Wind Direction: {conditions['windDirection']}")
                print(f"Relative Humidity: {conditions.get('relativeHumidity', {}).get('value', 'N/A')}")
                print(f"Dewpoint: {conditions.get('dewpoint', {}).get('value', 'N/A')} {conditions.get('dewpoint', {}).get('unitCode', 'N/A')}")
                print(f"Visibility: {conditions.get('visibility', {}).get('value', 'N/A')} {conditions.get('visibility', {}).get('unitCode', 'N/A')}")
                print(f"Wind Gust: {conditions.get('windGust', {}).get('value', 'N/A')} {conditions.get('windGust', {}).get('unitCode', 'N/A')}")
                print(f"Cloud Cover: {conditions.get('cloudCover', {}).get('value', 'N/A')}")
            else:
                print("Failed to retrieve detailed conditions.")
        elif choice == '5':
            print("Getting weather for nearest stations...")
            stations = get_nearest_stations(latitude, longitude)
            if stations:
                print("\n")
                for station in stations:
                    print(f"Station Name: {station['name']}")
                    print(f"Temperature: {station['temperature']} {station['temperature_unit']}")
                    print(f"Wind Speed: {station['wind_speed']}")
                    print(f"Wind Direction: {station['wind_direction']}")
                    print("-" * 20)
            else:
                print("Failed to retrieve weather for nearest stations.")
        elif choice == '6':
            stored_addresses = load_addresses()
            if stored_addresses:
                print("\nPreviously entered addresses:")
                for i, address in enumerate(stored_addresses):
                    print(f"{i + 1}. {address}")
                print("N. Enter a new address")

                choice = input("Choose an option: ")
                if choice.upper() == 'N':
                    address = input("Enter a street address: ")
                elif choice.isdigit() and 1 <= int(choice) <= len(stored_addresses):
                    address = stored_addresses[int(choice) - 1]
                else:
                    print("Invalid choice. Please try again.")
                    continue
            else:
                address = input("Enter a street address: ")

            latitude, longitude, matched_address = geocode_address(address)
            if latitude is None or longitude is None:
                continue

            if matched_address not in stored_addresses:
                stored_addresses.append(matched_address)
                save_addresses(stored_addresses)

            print(f"Matched Address: {matched_address}")
            print(f"Latitude: {latitude}, Longitude: {longitude}")
            address_map_url = generate_google_maps_url(latitude, longitude, matched_address)
            print(f"Google Maps URL for address: {address_map_url}")
        elif choice == '7':
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
