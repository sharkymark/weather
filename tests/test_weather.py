import pytest
import os
import sys
from datetime import datetime, timezone, timedelta

# Add the src directory to the Python path
# This allows us to import modules from the src directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

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
    ADDRESS_FILE
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
    # To be absolutely safe, one might reload the module or pass paths explicitly.

    # Reset to original values after test to avoid interference
    # This is crucial if not using monkeypatch for all global changes.
    weather.DATA_DIR = original_data_dir
    weather.ADDRESS_FILE = original_address_file

# Note: Testing functions that make API calls (like geocode_address, _fetch_noaa_data, etc.)
# would require mocking the `requests.get` calls using `pytest-mock` or `unittest.mock`.
# This is a good next step for more comprehensive tests.
