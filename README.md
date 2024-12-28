# Weather Application

A Python command-line application that provides comprehensive weather information using the NOAA Weather API and US Census Geocoder API.

## Features

- **Current Weather Conditions**: Get detailed current weather including temperature, wind, and forecast
- **Extended Forecast**: View 7-day weather forecast
- **Hourly Forecast**: See detailed hourly weather predictions
- **Nearby Stations**: Get weather data from up to 4 nearest weather stations
- **Active Alerts**: View any active weather alerts for the location
- **Address History**: Maintains a list of previously searched addresses
- **Google Maps Integration**: Provides Google Maps links for locations
- **Unit Conversions**: Automatically converts between metric and imperial units

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

Follow the on-screen prompts to:
1. Enter an address or select from previous addresses
2. View current weather conditions
3. Choose from additional options:
   - Detailed conditions
   - Extended forecast
   - Hourly forecast
   - Nearby station weather
   - Active alerts
   - Change location
   - Exit

## API Keys

This application uses:
- US Census Geocoder API (no key required)
- NOAA Weather API (no key required)

## File Structure

```
weather/
├── weather.py          # Main application code
├── README.md           # This documentation
├── requirements.txt    # Python dependencies
├── .gitignore          # Git ignore file
└── addresses.txt       # Stores previously searched addresses
```

## Contributing

Contributions are welcome! Please open an issue or pull request.

## License

MIT License