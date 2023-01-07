from geopy.geocoders import Nominatim


def locate(address):
    geolocator = Nominatim(user_agent="pyweatherfetch")
    location = geolocator.geocode(address)
    if location == None:
        raise ValueError("Could not find location of address")
    return (location.latitude, location.longitude)

