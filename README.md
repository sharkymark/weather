# Weather Application

A Python command-line application that provides comprehensive weather information using the NOAA Weather API and Nominatim Geocoder API. (Note: The application can also use the US Census Geocoder API for geocoding if desired.)

## Features

- **Address Lookup**: Enter an address to get weather data
  - **Current Weather Conditions**: Get detailed current weather including temperature, wind, and forecast
  - **Extended Forecast**: View 7-day weather forecast
  - **Hourly Forecast**: See detailed hourly weather predictions
  - **Nearby Stations**: Get weather data from up to 4 nearest weather stations
  - **Active Alerts**: View any active weather alerts for the location
  - **Address History**: Maintains a list of previously searched addresses
  - **Google Maps Integration**: Provides Google Maps links for locations
  - **Zillow URL Integration**: Provides Zillow link to zip code of address
  - **Unit Conversions**: Automatically converts between metric and imperial units
  - **Airport Weather**: Get weather data for a specific airport
  - **File loading**: Load and save address history to a file
- **Airport Weather Lookup**
  - **Load airport codes from a file**
  - **Get weather data for a specific airports marked with T boolean in file**
- **Airport List Download and Random Weather Lookup**
  - **Download airport codes**: from a [GitHub repository](https://davidmegginson.github.io/ourairports-data/airports.csv)\*\*
  - **Create random list**: of 2 airport codes\*\*
  - **Get weather data**: for a specific airports marked with T boolean in file\*\*
- **Airport Filter**
  - **Filter airports**: by code, name, state and municipality\*\*
  - **Zillow URL Integration**: Provides Zillow link to county and state of airport
  - **Download airport codes**: if not resident locally from a [GitHub repository](https://davidmegginson.github.io/ourairports-data/airports.csv)\*\*
- **Open Chrome browser**: to view Google Maps location, Zillow, and FlightTrader24 of airport
  - **Optional**: to enable this feature, pass `python3 weather.py --browser` flag when starting the app

> Note: The API endpoints are free to use, but please be mindful of the usage limits. If you exceed the limits, you may be temporarily blocked from making requests. Use a VPN to get around this if you are blocked.

## Requirements

- Python 3.8+
- Required packages (see requirements.txt)

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/sharkymark/weather.git
   cd weather
   ```

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the application:

```bash
python weather.py
```

To automatically open a Chrome web browser for weather, Google Maps, Flight, Zillow links (macOS and Chrome only):

```bash
python weather.py --browser
```

Follow the on-screen prompts to:

1. Enter an address or select from previous addresses
   1. View current weather conditions
   2. Choose from additional options:
      - Detailed conditions
      - Extended forecast
      - Hourly forecast
      - Nearby station weather
      - Active alerts
      - Change location
      - Return to main menu
2. Get airport weather data from file
3. Download airport codes and get weather data for random airports
4. Prompt user to filter airports by code, name, state and municipality
5. Exit the application

## APIs

This application uses:

- Nominatim Geocoder and Reverse Geocoder API
- NOAA Weather API (no key required)

If you want to use the US Census Geocoder API, use the argument `--census` when running the application. This will use the US Census Geocoder API for geocoding instead of Nominatim.

## Environment Variables

- `CENSUS_API_KEY` (optional): API key for the US Census Geocoder API. If provided, it will be used for geocoding requests to improve reliability and avoid rate limits. Set this variable in your environment before running the application.

### Example

```bash
export CENSUS_API_KEY=your_api_key_here
python weather.py
```

If the API key is not set, the application will notify you and proceed without it.

## File Structure

```
weather/
├── weather.py             # Main application code
├── README.md              # This documentation
├── requirements.txt       # Python dependencies
├── .gitignore             # Git ignore file
└── addresses.txt          # Stores previously searched addresses
└── airports.txt           # Stores airport codes for nearby stations
└── airports_dowload.csv   # Stores airport codes for random weather lookup
```

## Resources

- [NOAA Weather API Documentation](https://www.weather.gov/documentation/services-web-api)

- [Nominatim Geocoder API Documentation](https://nominatim.org/release-docs/develop/api/Search/)

- [US Census Geocoder API Documentation](https://www.census.gov/data/developers/data-sets/Geocoding-services.html)

- [pytest Documentation](https://docs.pytest.org/en/stable/)

- [Airport Codes CSV](https://davidmegginson.github.io/ourairports-data/)

## Contributing

Contributions are welcome! Please open an issue or pull request.

## License

MIT License
