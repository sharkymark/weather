"""
Helper functions for printing station weather information.
These are used across multiple modules in the weather application.
"""

import subprocess
import webbrowser

def notify_chrome_missing():
    """Notify user that Chrome is not installed."""
    print("Google Chrome is not installed on your computer. Please download and install it to use the browser feature.")

def print_nearest_station_weather(stations, args, location_description=None):
    """
    Print weather information for the nearest stations.
    
    Args:
        stations: List of station dictionaries containing weather information
        args: Command line arguments with browser preferences
        location_description: Optional description of the location (e.g., "tide station Example Bay")
        
    Returns:
        None
    """
    if not stations:
        print("Failed to retrieve weather for nearest stations.")
        return
    
    # Print location context if provided
    if location_description:
        print(f"\nShowing weather stations near {location_description}:")
    
    print("\n")
    for station in stations:
        print(f"Station Name: {station['name']}")
        print(f"Station ID: {station['station_id']}")
        print(f"Temperature: {station['temperature']} {station['temperature_unit']}")
        print(f"Wind Speed: {station['wind_speed']}")
        print(f"Wind Direction: {station['wind_direction']}")
        print(f"Google Maps URL for station: {station['address_map_url']}")
        print("-" * 20)

        # Open browser if requested
        if args.browser:
            chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))

            chrome = webbrowser.get('chrome')
            if chrome:
                subprocess.run([chrome_path, station['address_map_url']], stdout=subprocess.DEVNULL)
            else:
                notify_chrome_missing()
