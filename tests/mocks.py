from unittest.mock import MagicMock
import requests # Ensure requests is imported for exceptions

# --- Mock data for Nominatim API ---
MOCK_NOMINATIM_GEOCODE_SUCCESS = [
    {
        "lat": "34.052235",
        "lon": "-118.243683",
        "display_name": "Los Angeles, Los Angeles County, California, USA"
    }
]

MOCK_NOMINATIM_GEOCODE_EMPTY = []

MOCK_NOMINATIM_REVERSE_GEOCODE_SUCCESS = {
    "address": {
        "city": "Los Angeles",
        "state": "California",
        "country": "United States"
    }
}

MOCK_NOMINATIM_REVERSE_GEOCODE_NO_CITY_STATE = {
    "address": {
        "country": "United States"
    }
}

# --- Mock data for US Census API ---
MOCK_CENSUS_GEOCODE_SUCCESS = {
    "result": {
        "addressMatches": [
            {
                "coordinates": {"x": -77.036543, "y": 38.895037},
                "matchedAddress": "1600 Pennsylvania Ave NW, Washington, DC, 20500"
            }
        ]
    }
}

MOCK_CENSUS_GEOCODE_NO_MATCH = {
    "result": {
        "addressMatches": []
    }
}

MOCK_CENSUS_REVERSE_GEOCODE_SUCCESS = {
    "result": {
        "geographies": {
            "Incorporated Places": [{"BASENAME": "Washington"}],
            "States": [{"BASENAME": "District of Columbia"}]
        }
    }
}

# --- Mock data for NOAA API ---
MOCK_NOAA_POINTS_SUCCESS = {
    "properties": {
        "forecast": "https://api.weather.gov/gridpoints/LWX/96,70/forecast",
        "forecastHourly": "https://api.weather.gov/gridpoints/LWX/96,70/forecast/hourly",
        "observationStations": "https://api.weather.gov/gridpoints/LWX/96,70/stations"
    }
}

MOCK_NOAA_FORECAST_SUCCESS = {
    "properties": {
        "periods": [
            {
                "name": "Today",
                "temperature": 75,
                "temperatureUnit": "F",
                "shortForecast": "Sunny",
                "detailedForecast": "Sunny, with a high near 75.",
                "windSpeed": "5 mph",
                "windDirection": "NW",
                "probabilityOfPrecipitation": {"value": 0}
            },
            {
                "name": "Tonight",
                "temperature": 55,
                "temperatureUnit": "F",
                "shortForecast": "Clear",
                "detailedForecast": "Clear, with a low around 55.",
                "windSpeed": "5 mph",
                "windDirection": "S",
                "probabilityOfPrecipitation": {"value": 0}
            }
        ]
    }
}

MOCK_NOAA_FORECAST_HOURLY_SUCCESS = {
    "properties": {
        "periods": [
            {
                "startTime": "2025-05-06T14:00:00-04:00",
                "temperature": 72,
                "temperatureUnit": "F",
                "shortForecast": "Sunny"
            },
            {
                "startTime": "2025-05-06T15:00:00-04:00",
                "temperature": 73,
                "temperatureUnit": "F",
                "shortForecast": "Mostly Sunny"
            }
        ]
    }
}

MOCK_NOAA_STATIONS_SUCCESS = {
    "features": [
        {
            "properties": {"stationIdentifier": "KDCA", "name": "Reagan National Airport"},
            "geometry": {"coordinates": [-77.0375, 38.8522]}
        },
        {
            "properties": {"stationIdentifier": "KIAD", "name": "Dulles International Airport"},
            "geometry": {"coordinates": [-77.4558, 38.9445]}
        }
    ]
}

MOCK_NOAA_OBSERVATION_SUCCESS_KDCA = {
    "properties": {
        "temperature": {"value": 22.0, "unitCode": "C"}, # Celsius
        "windSpeed": {"value": 10.0}, # km/h
        "windDirection": {"value": 180},
        "textDescription": "Clear"
    }
}

MOCK_NOAA_ALERTS_SUCCESS = {
    "features": [
        {
            "properties": {
                "headline": "Flood Watch in effect",
                "description": "Flooding possible...",
                "severity": "Moderate",
                "urgency": "Expected",
                "effective": "2025-05-06T10:00:00-04:00",
                "expires": "2025-05-07T10:00:00-04:00"
            }
        }
    ]
}

MOCK_NOAA_ALERTS_EMPTY = {"features": []}

MOCK_STATION_WEATHER_RESULTS = [
    {
        'station_id': 'KLAX',
        'labelled_name': 'Los Angeles International Airport',
        'station_name': 'Los Angeles International Airport',
        'temperature': '72.0',
        'temperature_unit': 'F',
        'wind_speed': '5.0 mph',
        'wind_direction': 180,
        'current_conditions': 'Clear',
        'forecast': 'Sunny',
        'latitude': 33.9425,
        'longitude': -118.408,
        'address_map_url': 'https://www.google.com/maps/search/33.9425,-118.408/33.9425,-118.408,15z?t=s',
        'airports_url': 'https://www.flightradar24.com/airport/KLAX'
    },
    {
        'station_id': 'KJFK',
        'labelled_name': 'John F Kennedy International Airport',
        'station_name': 'John F Kennedy International Airport',
        'temperature': '68.0',
        'temperature_unit': 'F',
        'wind_speed': '10.0 mph',
        'wind_direction': 270,
        'current_conditions': 'Cloudy',
        'forecast': 'Chance of Rain',
        'latitude': 40.6398,
        'longitude': -73.7789,
        'address_map_url': 'https://www.google.com/maps/search/40.6398,-73.7789/40.6398,-73.7789,15z?t=s',
        'airports_url': 'https://www.flightradar24.com/airport/KJFK'
    }
]


# --- Mock requests.get function ---
def mock_requests_get(*args, **kwargs):
    """
    A mock for requests.get that returns different responses based on the URL.
    """
    url = args[0]
    params_dict = kwargs.get("params", {}) # Get params dict for easier access
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock() # No error by default

    if "nominatim.openstreetmap.org/search" in url:
        # Check params for a specific test case if needed
        if "q=123+Main+St" in kwargs.get("params", {}).get("q", ""): # Example specific query
             mock_response.json.return_value = MOCK_NOMINATIM_GEOCODE_SUCCESS
        elif "q=Unknown+Address" in kwargs.get("params", {}).get("q", ""):
            mock_response.json.return_value = MOCK_NOMINATIM_GEOCODE_EMPTY
        else:
            mock_response.json.return_value = MOCK_NOMINATIM_GEOCODE_SUCCESS
    elif "nominatim.openstreetmap.org/reverse" in url:
        mock_response.json.return_value = MOCK_NOMINATIM_REVERSE_GEOCODE_SUCCESS
    elif "geocoding.geo.census.gov/geocoder/locations/onelineaddress" in url:
        # Check for specific address and benchmark used in the successful mock
        if params_dict.get("address") == "1600 Pennsylvania Ave NW" and \
           params_dict.get("benchmark") == "Public_AR_Current":
            mock_response.json.return_value = MOCK_CENSUS_GEOCODE_SUCCESS
        else:
            mock_response.json.return_value = MOCK_CENSUS_GEOCODE_NO_MATCH
    elif "geocoding.geo.census.gov/geocoder/geographies/coordinates" in url:
        mock_response.json.return_value = MOCK_CENSUS_REVERSE_GEOCODE_SUCCESS
    elif "api.weather.gov/points/" in url:
        mock_response.json.return_value = MOCK_NOAA_POINTS_SUCCESS
    elif "api.weather.gov/gridpoints/" in url and "/forecast/hourly" in url:
        mock_response.json.return_value = MOCK_NOAA_FORECAST_HOURLY_SUCCESS
    elif "api.weather.gov/gridpoints/" in url and "/forecast" in url:
        mock_response.json.return_value = MOCK_NOAA_FORECAST_SUCCESS
    elif "api.weather.gov/stations/KDCA/observations/latest" in url: # Specific station
        mock_response.json.return_value = MOCK_NOAA_OBSERVATION_SUCCESS_KDCA
    elif "api.weather.gov/stations" in url and "/observations/latest" in url: # Generic station observation
        mock_response.json.return_value = MOCK_NOAA_OBSERVATION_SUCCESS_KDCA # Default to KDCA for simplicity
    elif "api.weather.gov/alerts/active" in url:
        # Specific case for test_get_active_alerts_no_alerts (uses lat, lon = 39.0, -77.0)
        if "point=39.0,-77.0" in url:
            mock_response.json.return_value = MOCK_NOAA_ALERTS_EMPTY
        # Add other specific conditions for alerts if needed for other tests
        # elif "point=some_other_lat,some_other_lon" in url:
        #     mock_response.json.return_value = SOME_OTHER_MOCK_ALERTS
        else: # Default for other alert calls, e.g., test_get_active_alerts_success
            mock_response.json.return_value = MOCK_NOAA_ALERTS_SUCCESS
    else:
        # Default or error case
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Mocked HTTPError")
        mock_response.json.return_value = {"error": "Mocked URL not found"}

    return mock_response

# Mock for urllib.request.urlopen
MOCK_AIRPORTS_CSV_CONTENT = b"""ident,type,name,latitude_deg,longitude_deg,elevation_ft,continent,iso_country,iso_region,municipality,scheduled_service,gps_code,iata_code,local_code,home_link,wikipedia_link,keywords
KLAX,large_airport,Los Angeles International Airport,33.942501,-118.407997,125,NA,US,US-CA,Los Angeles,yes,KLAX,LAX,LAX,,https://en.wikipedia.org/wiki/Los_Angeles_International_Airport,
KJFK,large_airport,John F Kennedy International Airport,40.639801,-73.7789,13,NA,US,US-NY,New York,yes,KJFK,JFK,JFK,,https://en.wikipedia.org/wiki/John_F._Kennedy_International_Airport,
KORD,large_airport,Chicago O'Hare International Airport,41.9786,-87.9048,672,NA,US,US-IL,Chicago,yes,KORD,ORD,ORD,,https://en.wikipedia.org/wiki/O'Hare_International_Airport,
KDEN,large_airport,Denver International Airport,39.861698150634766,-104.6729965209961,5431,NA,US,US-CO,Denver,yes,KDEN,DEN,DEN,,"https://en.wikipedia.org/wiki/Denver_International_Airport",
KSEA,large_airport,Seattle Tacoma International Airport,47.449001,-122.308998,432,NA,US,US-WA,Seattle,yes,KSEA,SEA,SEA,,https://en.wikipedia.org/wiki/Seattle%E2%80%93Tacoma_International_Airport,
PAFA,large_airport,Fairbanks International Airport,64.8151016235,-147.856002808,439,NA,US,US-AK,Fairbanks,yes,PAFA,FAI,FAI,,"https://en.wikipedia.org/wiki/Fairbanks_International_Airport",
PHNL,large_airport,Daniel K Inouye International Airport,21.318681,-157.922428,13,OC,US,US-HI,Honolulu,yes,PHNL,HNL,HNL,,https://en.wikipedia.org/wiki/Daniel_K._Inouye_International_Airport,
TJSJ,large_airport,Luis Munoz Marin International Airport,18.4394,-66.001801,9,NA,PR,PR-U-A,San Juan,yes,TJSJ,SJU,SJU,,https://en.wikipedia.org/wiki/Luis_Mu%C3%B1oz_Mar%C3%ADn_International_Airport,
KBZN,medium_airport,Bozeman Yellowstone International Airport,45.7775001526,-111.153000057,4473,NA,US,US-MT,Bozeman,yes,KBZN,BZN,BZN,,"https://en.wikipedia.org/wiki/Bozeman_Yellowstone_International_Airport",
KXYZ,small_airport,Test Small Airport,34.0000,-118.0000,100,NA,US,US-CA,Testville,no,KXYZ,,,,"",
"""

class MockUrllibResponse:
    def __init__(self, content):
        self.content = content
        self.status = 200
        self.reason = "OK"

    def read(self):
        return self.content

    def getcode(self):
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

def mock_urlopen_airport_data(*args, **kwargs):
    url = args[0]
    if "davidmegginson.github.io/ourairports-data/airports.csv" in url:
        return MockUrllibResponse(MOCK_AIRPORTS_CSV_CONTENT)
    # Fallback for other URLs or raise an error
    # Ensure urllib.error is available if you plan to raise it.
    # For now, this mock only handles the specific airport data URL.
    # import urllib.error # Would be needed here if raising URLError
    raise Exception(f"Mocked urlopen does not handle {url}") # Or a more specific error
