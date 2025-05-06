import pytest
import os
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, call # Added patch, MagicMock, call
import argparse # Added for creating mock args
import pandas as pd # Added for airport_download test

# Add the src directory to the Python path
# This allows us to import modules from the src directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Import functions from weather.py
from weather import (
    format_time,
    convert_kmh_to_mph,
    convert_temperature,
    generate_google_maps_url,
    generate_zillow_urls,
    generate_flightradar24_url,
    load_addresses,
    save_addresses,
    DATA_DIR,
    ADDRESS_FILE,
    AIRPORTS_DOWNLOAD_CSV, # Added for airport_download test
    geocode_address,       # Function to test
    get_current_conditions, # Function to test
    get_active_alerts,     # Function to test
    airport_download       # Function to test
)

# Import mocks
from tests.mocks import (
    mock_requests_get,
    MOCK_NOMINATIM_GEOCODE_SUCCESS,
    MOCK_CENSUS_GEOCODE_SUCCESS,
    MOCK_NOAA_POINTS_SUCCESS,
    MOCK_NOAA_FORECAST_SUCCESS,
    MOCK_NOAA_ALERTS_SUCCESS,
    MOCK_NOAA_ALERTS_EMPTY,
    mock_urlopen_airport_data,
    MOCK_AIRPORTS_CSV_CONTENT,
    MOCK_STATION_WEATHER_RESULTS
)

# Test for format_time
def test_format_time():
    # Example ISO time string (UTC)
    iso_time_utc = "2023-10-26T14:30:00Z"
    # Expected format for America/New_York (EDT during this date, but pytz handles DST)
    # Let's make it timezone aware for comparison
    dt_obj = datetime.fromisoformat(iso_time_utc.replace('Z', '+00:00'))
    # For 2023-10-26, New York is in EDT (UTC-4)
    # So 14:30 UTC should be 10:30 AM EDT
    expected_time_edt = "10:30 AM EDT" 
    # For a winter date, e.g., 2023-01-26T14:30:00Z (EST, UTC-5)
    iso_time_utc_winter = "2023-01-26T14:30:00Z"
    # So 14:30 UTC should be 09:30 AM EST
    expected_time_est = "09:30 AM EST"

    assert format_time(iso_time_utc) == expected_time_edt
    assert format_time(iso_time_utc_winter) == expected_time_est

# Test for convert_kmh_to_mph
def test_convert_kmh_to_mph():
    assert convert_kmh_to_mph(100) == 62.14  # 100 km/h is approx 62.1371 mph
    assert convert_kmh_to_mph(0) == 0.0
    assert convert_kmh_to_mph(None) is None
    assert convert_kmh_to_mph(50.5) == 31.38 # 50.5 km/h is approx 31.3794355 mph

# Test for convert_temperature
def test_convert_temperature():
    # Test with valid Celsius temperature
    celsius_data_1 = {'value': 0, 'unitCode': 'degC'}
    expected_fahrenheit_1 = {'value': 32.0, 'unitCode': 'F'}
    assert convert_temperature(celsius_data_1) == expected_fahrenheit_1

    celsius_data_2 = {'value': 100, 'unitCode': 'degC'}
    expected_fahrenheit_2 = {'value': 212.0, 'unitCode': 'F'}
    assert convert_temperature(celsius_data_2) == expected_fahrenheit_2

    celsius_data_3 = {'value': -10, 'unitCode': 'degC'}
    expected_fahrenheit_3 = {'value': 14.0, 'unitCode': 'F'}
    assert convert_temperature(celsius_data_3) == expected_fahrenheit_3
    
    celsius_data_4 = {'value': 25.5, 'unitCode': 'degC'}
    expected_fahrenheit_4 = {'value': 77.9, 'unitCode': 'F'} # 25.5 * 9/5 + 32 = 77.9
    assert convert_temperature(celsius_data_4) == expected_fahrenheit_4

    # Test with None value
    celsius_data_none = {'value': None, 'unitCode': 'degC'}
    expected_fahrenheit_none = {'value': None, 'unitCode': ''}
    assert convert_temperature(celsius_data_none) == expected_fahrenheit_none
    
    # Test with empty dictionary
    celsius_data_empty = {}
    expected_fahrenheit_empty = {'value': None, 'unitCode': ''} # Function adds these keys
    assert convert_temperature(celsius_data_empty) == expected_fahrenheit_empty


# Test for generate_google_maps_url
def test_generate_google_maps_url():
    lat, lon = 34.0522, -118.2437
    label = "Los Angeles, CA"
    expected_url_with_label = "https://www.google.com/maps/place/Los%20Angeles%2C%20CA"
    assert generate_google_maps_url(lat, lon, label) == expected_url_with_label

    expected_url_without_label = f"https://www.google.com/maps/search/{lat},{lon}/{lat},{lon},15z?t=s"
    assert generate_google_maps_url(lat, lon, "") == expected_url_without_label

# Test for generate_zillow_urls
def test_generate_zillow_urls():
    arg_zip = "90210"
    expected_url_zip = "https://www.zillow.com/homes/for_sale/90210"
    assert generate_zillow_urls(arg_zip) == expected_url_zip

    arg_city_state = "Beverly Hills-CA"
    expected_url_city_state = "https://www.zillow.com/homes/for_sale/Beverly+Hills-CA"
    assert generate_zillow_urls(arg_city_state) == expected_url_city_state

# Test for generate_flightradar24_url
def test_generate_flightradar24_url():
    station_id = "KLAX"
    expected_url = "https://www.flightradar24.com/airport/KLAX"
    assert generate_flightradar24_url(station_id) == expected_url

# Tests for load_addresses and save_addresses
def test_load_and_save_addresses(tmp_path, monkeypatch): # Add monkeypatch here
    # Override DATA_DIR and ADDRESS_FILE for testing purposes
    # This is a bit tricky as they are global in weather.py
    # A better approach would be to pass them as arguments or use a config object
    # For now, we'll work with the global by ensuring the test file is in the right place
    
    # This test verifies file operations that depend on DATA_DIR and ADDRESS_FILE globals.
    # It uses monkeypatch.chdir to ensure that relative paths are resolved within tmp_path.
    
    # Import weather module locally to access its globals if needed for setup,
    # but the functions load_addresses and save_addresses will use the module's own globals.
    import weather

    # Define the expected path for the data subdirectory within tmp_path
    # weather.DATA_DIR is "data", weather.ADDRESS_FILE is "addresses.txt"
    data_subdir_in_tmp = tmp_path / weather.DATA_DIR
    data_subdir_in_tmp.mkdir() # Create "data" subdirectory in tmp_path

    # Change current working directory to tmp_path for the scope of this test
    # This makes os.path.join(weather.DATA_DIR, weather.ADDRESS_FILE) resolve to
    # tmp_path / "data" / "addresses.txt"
    monkeypatch.chdir(tmp_path)

    # Test load_addresses when file (tmp_path/data/addresses.txt) doesn't exist
    assert load_addresses() == []

    # Test save_addresses and then load_addresses
    addresses_to_save = ["123 Main St, Anytown, USA", "456 Oak Ave, Otherville, USA"]
    save_addresses(addresses_to_save) # Should write to tmp_path/data/addresses.txt

    expected_file_path = data_subdir_in_tmp / weather.ADDRESS_FILE
    assert expected_file_path.exists()
    
    loaded_addresses = load_addresses() # Should read from tmp_path/data/addresses.txt
    assert loaded_addresses == addresses_to_save

    # Test saving empty list (should effectively clear the file or write nothing)
    save_addresses([])
    assert load_addresses() == [] # Or check if file is empty

    # monkeypatch.chdir is automatically undone after the test.
    # No need to manually restore weather.DATA_DIR or weather.ADDRESS_FILE
    # as we are testing their default behavior in a controlled CWD.

def test_load_addresses_file_not_found(monkeypatch, tmp_path):
    # Ensure DATA_DIR points to a temporary directory for this test
    # and ADDRESS_FILE is a file that won't exist initially.
    import weather # Import here to ensure monkeypatch targets the correct module instance
    
    # Store original values from the imported weather module
    original_data_dir = weather.DATA_DIR
    original_address_file = weather.ADDRESS_FILE

    # Use tmp_path for DATA_DIR
    test_data_dir_name = "test_data_load" 
    # weather.py expects DATA_DIR to be the *name* of the data directory,
    # and it constructs the path like os.path.join(DATA_DIR, ADDRESS_FILE)
    # So, we need to set weather.DATA_DIR to this name, and ensure our
    # actual file operations happen within tmp_path.
    # For load_addresses, it constructs `full_address_path = os.path.join(DATA_DIR, ADDRESS_FILE)`
    # So, if DATA_DIR is `tmp_path / "data"`, then `full_address_path` will be `tmp_path / "data" / "addresses.txt"`

    import weather
    # We want load_addresses to look inside tmp_path for a "data" subdir
    # So, we set weather.DATA_DIR to be just "data"
    # and then ensure that the current working directory for the test
    # effectively makes os.path.join("data", "addresses.txt") resolve within tmp_path.
    # This is tricky because load_addresses uses global DATA_DIR.
    # The previous test modified weather.DATA_DIR directly. Let's refine that.

    # Create a temporary data directory *inside* tmp_path
    temp_data_root = tmp_path / "project_root"
    temp_data_root.mkdir()
    
    # Monkeypatch os.path.join to control where it looks for DATA_DIR
    # Or, more simply, monkeypatch the globals directly in the imported module.
    monkeypatch.setattr(weather, "DATA_DIR", str(temp_data_root)) # DATA_DIR is now an absolute path for the test
    monkeypatch.setattr(weather, "ADDRESS_FILE", "non_existent_addresses.txt")

    assert load_addresses() == []

    # Restore original values (monkeypatch does this automatically for its changes)
    # But if we manually changed them like in the previous test, we'd need to restore.
    # For this test, monkeypatch handles cleanup of weather.DATA_DIR and weather.ADDRESS_FILE
    # However, it's good practice to ensure they are reset if other tests depend on original values.
    # This is complex due to Python's module caching.
    # A better long-term solution is to refactor weather.py to not rely on module-level globals for paths.
    # For now, we rely on monkeypatch's scope.
    # monkeypatch.setattr correctly restored the original values of weather.DATA_DIR and weather.ADDRESS_FILE.

# Note: Testing functions that make API calls (like geocode_address, _fetch_noaa_data, etc.)
# would require mocking the `requests.get` calls using `pytest-mock` or `unittest.mock`.
# This is a good next step for more comprehensive tests.


# --- Tests for API calling functions using mocks ---

@patch('weather.requests.get', side_effect=mock_requests_get) # Changed src.weather to weather
def test_geocode_address_nominatim_success(mock_get):
    """Test geocode_address with Nominatim successfully."""
    address = "123 Main St"
    expected_lat = float(MOCK_NOMINATIM_GEOCODE_SUCCESS[0]['lat'])
    expected_lon = float(MOCK_NOMINATIM_GEOCODE_SUCCESS[0]['lon'])
    
    lat, lon, matched_address = geocode_address(address, use_census_api=False)
    
    assert lat == expected_lat
    assert lon == expected_lon
    assert matched_address == address # Nominatim mock returns original address for simplicity here
    mock_get.assert_called_once()
    assert "nominatim.openstreetmap.org/search" in mock_get.call_args[0][0]

@patch('weather.requests.get', side_effect=mock_requests_get) # Changed src.weather to weather
def test_geocode_address_census_success(mock_get):
    """Test geocode_address with US Census API successfully."""
    address = "1600 Pennsylvania Ave NW" # Address used in mock
    expected_lat = MOCK_CENSUS_GEOCODE_SUCCESS['result']['addressMatches'][0]['coordinates']['y']
    expected_lon = MOCK_CENSUS_GEOCODE_SUCCESS['result']['addressMatches'][0]['coordinates']['x']
    expected_matched_address = MOCK_CENSUS_GEOCODE_SUCCESS['result']['addressMatches'][0]['matchedAddress']

    lat, lon, matched_address = geocode_address(address, use_census_api=True)

    assert lat == expected_lat
    assert lon == expected_lon
    assert matched_address == expected_matched_address
    mock_get.assert_called_once()
    assert "geocoding.geo.census.gov/geocoder/locations/onelineaddress" in mock_get.call_args[0][0]

@patch('weather.requests.get', side_effect=mock_requests_get) # Changed src.weather to weather
def test_get_current_conditions_success(mock_get):
    """Test get_current_conditions successfully fetches and processes data."""
    lat, lon = 38.895037, -77.036543 # Example coordinates
    
    conditions = get_current_conditions(lat, lon)
    
    expected_period = MOCK_NOAA_FORECAST_SUCCESS['properties']['periods'][0]
    assert conditions is not None
    assert conditions['name'] == expected_period['name']
    assert conditions['temperature'] == expected_period['temperature']
    
    # Check that requests.get was called twice (once for points, once for forecast)
    assert mock_get.call_count == 2
    # First call for points
    assert f"api.weather.gov/points/{lat},{lon}" in mock_get.call_args_list[0][0][0]
    # Second call for forecast (URL comes from the first call's mock response)
    expected_forecast_url = MOCK_NOAA_POINTS_SUCCESS['properties']['forecast']
    assert expected_forecast_url == mock_get.call_args_list[1][0][0]

@patch('weather.requests.get', side_effect=mock_requests_get) # Changed src.weather to weather
def test_get_active_alerts_success(mock_get):
    """Test get_active_alerts successfully fetches alerts."""
    lat, lon = 38.895037, -77.036543
    
    alerts = get_active_alerts(lat, lon)
    
    assert alerts is not None
    assert len(alerts) == len(MOCK_NOAA_ALERTS_SUCCESS['features'])
    assert alerts[0]['properties']['headline'] == MOCK_NOAA_ALERTS_SUCCESS['features'][0]['properties']['headline']
    mock_get.assert_called_once()
    assert f"api.weather.gov/alerts/active?point={lat},{lon}" in mock_get.call_args[0][0]

@patch('weather.requests.get', side_effect=mock_requests_get) # Changed src.weather to weather
def test_get_active_alerts_no_alerts(mock_get):
    """Test get_active_alerts when no alerts are present."""
    lat, lon = 39.0, -77.0 # Different coords to potentially trigger different mock if needed

    # Temporarily adjust mock_requests_get to return empty alerts for this specific call
    # This is a bit more complex; for now, let's assume mock_requests_get can be configured
    # or we add a specific URL pattern for empty alerts in mocks.py.
    # For simplicity, let's assume the default mock_requests_get is modified or a new one is used.
    # A better way: have mock_requests_get check args and return MOCK_NOAA_ALERTS_EMPTY for specific params.
    # For this example, we'll rely on a general mock. If MOCK_NOAA_ALERTS_EMPTY was the default:
    
    # To make this test specific for empty alerts, we'd ideally configure mock_requests_get
    # or use a different side_effect for this test.
    # For now, let's assume MOCK_NOAA_ALERTS_EMPTY is returned by a specific condition in mock_requests_get
    # (e.g. based on lat/lon if we made mock_requests_get that sophisticated)
    # Or, more simply, patch it to return the empty list directly for this test:
    # The mock_requests_get function is now configured to return MOCK_NOAA_ALERTS_EMPTY
    # for the specific coordinates used in this test (39.0, -77.0).
    
    alerts = get_active_alerts(lat, lon)
    
    assert alerts == [] # Expect an empty list
    mock_get.assert_called_once()


@patch('weather.print_station_forecasts') # Changed src.weather to weather
@patch('weather.get_station_weather') # Changed src.weather to weather
@patch('pandas.DataFrame.sample') # Mock random sampling
@patch('urllib.request.urlopen') # Mock file download
@patch('builtins.input', return_value='1') # Mock user input for scheduled service
def test_airport_download_success(mock_input, mock_urlopen, mock_df_sample, mock_get_station_weather, mock_print_forecasts, tmp_path, monkeypatch):
    """Test airport_download function successfully downloads, processes, and calls sub-functions."""
    
    # Setup mock args
    mock_args = argparse.Namespace(browser=False, census=False)

    # Configure mocks
    mock_urlopen.side_effect = mock_urlopen_airport_data # From tests.mocks
    
    # Create a deterministic sample to be returned by df.sample()
    # This should match the structure of what df.sample() returns (a DataFrame)
    # The MOCK_AIRPORTS_CSV_CONTENT has KLAX and KJFK as first two valid entries.
    # Let's assume these are picked after filtering.
    # The 'ident' and 'name' columns are used.
    sample_data = {'ident': ['KLAX', 'KJFK'], 'name': ['Los Angeles International Airport', 'John F Kennedy International Airport']}
    mock_df_sample.return_value = pd.DataFrame(sample_data)

    mock_get_station_weather.return_value = MOCK_STATION_WEATHER_RESULTS # From tests.mocks

    # Monkeypatch DATA_DIR to use tmp_path
    # weather.py uses DATA_DIR as a relative path component.
    # We need to ensure the current working directory is such that DATA_DIR resolves within tmp_path,
    # or set DATA_DIR to an absolute path within tmp_path.
    # The function airport_download constructs path: os.path.join(DATA_DIR, AIRPORTS_DOWNLOAD_CSV)
    
    # Option 1: Change CWD (as in test_load_and_save_addresses)
    # monkeypatch.chdir(tmp_path)
    # data_dir_in_tmp = tmp_path / DATA_DIR 
    # data_dir_in_tmp.mkdir(exist_ok=True)
    # expected_csv_path = data_dir_in_tmp / AIRPORTS_DOWNLOAD_CSV

    # Option 2: Monkeypatch weather.DATA_DIR to be an absolute path for the test
    # This is often cleaner if the code uses DATA_DIR directly without os.getcwd() context.
    # weather.py's airport_download uses `os.path.join(DATA_DIR, AIRPORTS_DOWNLOAD_CSV)`
    # If DATA_DIR is "data", it resolves relative to CWD.
    # Let's use chdir to be consistent with other tests.
    
    original_cwd = os.getcwd()
    monkeypatch.chdir(tmp_path)
    
    # Ensure the "data" subdirectory exists in tmp_path, as airport_download expects it
    data_dir_path = tmp_path / "data" # weather.DATA_DIR is "data"
    data_dir_path.mkdir(parents=True, exist_ok=True)
    
    # Path where the downloaded CSV will be saved by airport_download
    expected_csv_path = data_dir_path / AIRPORTS_DOWNLOAD_CSV

    # Call the function to test
    airport_download(mock_args, print_results=True)

    # Assertions
    mock_input.assert_called_once() # Called for "scheduled service"
    mock_urlopen.assert_called_once() # Called to download CSV
    assert "davidmegginson.github.io/ourairports-data/airports.csv" in mock_urlopen.call_args[0][0]
    
    assert expected_csv_path.exists() # Check if CSV was "downloaded" (written by mock)
    
    mock_df_sample.assert_called_once() # Called on the filtered DataFrame
    # Assert that get_station_weather was called with the data from the sample
    # The sample returns KLAX and KJFK.
    # get_station_weather expects a list of tuples: [(station_id, name), ...]
    expected_station_data_arg = [('KLAX', 'Los Angeles International Airport'), ('KJFK', 'John F Kennedy International Airport')]
    mock_get_station_weather.assert_called_once_with(expected_station_data_arg)
    
    mock_print_forecasts.assert_called_once_with(MOCK_STATION_WEATHER_RESULTS, browser=False, census=False)

    # Restore CWD
    monkeypatch.chdir(original_cwd)
