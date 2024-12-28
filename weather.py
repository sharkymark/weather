import requests
import json
from geopy.distance import geodesic
from urllib.parse import quote
from halo import Halo
from datetime import datetime
import pytz
import os

ADDRESS_FILE = "addresses.txt"
CENSUS_API_BASE_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"

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
    params = {
        "address": address,
        "benchmark": "Public_AR_Current",
        "format": "json",
    }
    spinner = Halo(text='Geocoding address...', spinner='dots')
    try:
        spinner.start()
        response = requests.get(CENSUS_API_BASE_URL, params=params)
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

    if label == "":
        return f"https://www.google.com/maps/search/{latitude},{longitude}/{latitude},{longitude},15z?t=s"
    else:
        return f"https://www.google.com/maps/search/?api=1&query={quote(label)}@{latitude},{longitude}"

# end of refactor comments for AI!

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
    return _fetch_noaa_data(latitude, longitude, 'forecast')

def get_short_conditions(latitude, longitude):
    """
    Fetches brief weather conditions from the NOAA API.

    Args:
        latitude: The latitude of the location.
        longitude: The longitude of the location.

    Returns:
        A dictionary containing the detailed weather conditions, or None if the API call fails.
    """
    return _fetch_noaa_data(latitude, longitude, 'forecast')[0]

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
    print(f"\nGoogle Maps URL for address: {address_map_url}")

    print("\nGetting current weather conditions...")
    conditions = get_short_conditions(latitude, longitude)
    if conditions:
        print(f"\nTemperature: {conditions['temperature']} {conditions['temperatureUnit']}")
        print(f"Forecast: {conditions['shortForecast']}")
    else:
        print("\nFailed to retrieve weather conditions.")

    while True:
        print("\nOptions:")
        print("1. Get Detailed Conditions")
        print("2. Get Extended Forecast")
        print("3. Get Hourly Forecast")
        print("4. Get Weather for Nearest Stations")
        print("5. Get Active Weather Alerts")
        print("6. Get Weather for a Different Location")
        print("7. Exit")
        choice = input("Enter your choice: ")

        if choice == '1':
            print("Getting detailed current conditions...")
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
                    # print a Google Maps URL for each station location, and update this file with the URL
                    print(f"Station Name: {station['name']}")
                    print(f"Station ID: {station['station_id']}")
                    print(f"Temperature: {station['temperature']} {station['temperature_unit']}")
                    print(f"Wind Speed: {station['wind_speed']}")
                    print(f"Wind Direction: {station['wind_direction']}")
                    print(f"Google Maps URL for station: {station['address_map_url']}")
                    print("-" * 20)
                    # end of work for AI!
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
            print(f"\nGoogle Maps URL for address: {address_map_url}")

            print("\nGetting current weather conditions...")
            conditions = get_short_conditions(latitude, longitude)
            if conditions:
                print(f"\nTemperature: {conditions['temperature']} {conditions['temperatureUnit']}")
                print(f"Forecast: {conditions['shortForecast']}")
            else:
                print("\nFailed to retrieve weather conditions.")

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
        elif choice == '7':
            print("\nExiting the program...")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
