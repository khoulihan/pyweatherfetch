import json
import hashlib
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import urllib3
from . import _config as config


# TODO: These icons require a nerd font - may need a way to detect that, or
# allow alternatives to be specified.
_icons = {
    '01d': '',
    '01n': '',
    '02d': '',
    '02n': '',
    '03d': '',
    '03n': '',
    '04d': '',
    '04n': '',
    '09d': '',
    '09n': '',
    '10d': '',
    '10n': '',
    '11d': '',
    '11n': '',
    '13d': '',
    '13n': '',
    '50d': '',
    '50n': '',
}


_icon_colours = {
    '01d': '#e5c07b',
    '01n': '#34e2e2',
    '02d': '#e5c07b',
    '02n': '#34e2e2',
    '03d': '#eea825',
    '03n': '#56b6c2',
    '04d': '#abb2bf',
    '04n': '#6f737b',
    '09d': '#abb2bf',
    '09n': '#6f737b',
    '10d': '#abb2bf',
    '10n': '#6f737b',
    '11d': '#e06c75',
    '11n': '#e05661',
    '13d': '#f2f2f2',
    '13n': '#abb2bf',
    '50d': '#abb2bf',
    '50n': '#6f737b',
}


def get_weather(latitude, longitude, units):
    data = _get_cached(latitude, longitude, units)
    if data == None:
        data = _get_fresh(latitude, longitude, units)
    if data == None:
        raise APIError("Failed to retrieve weather data from API", None)
    return _filter_data(data)


def _filter_data(data):
    filtered = {}

    main = data['main']
    filtered['calculated_at'] = datetime.fromtimestamp(data['dt'], timezone.utc)
    filtered['temperature'] = Decimal(main['temp']).quantize(Decimal('.0'))
    filtered['feels_like'] = Decimal(main['feels_like']).quantize(Decimal('.0'))
    filtered['pressure'] = main['pressure']
    filtered['humidity'] = main['humidity']

    # weather is a list - what if there is more than one?
    # According to the docs the first one in the list is primary.
    weather = data['weather'][0]
    filtered['icon'] = _icons[weather['icon']]
    filtered['icon_colour'] = _icon_colours[weather['icon']]

    # Is the wind section guaranteed to be present?
    # Rain, snow etc. are apparently not.
    wind = data['wind']
    filtered['wind'] = {
        'speed': Decimal(wind['speed']).quantize(Decimal('.00')),
        'direction': _interpret_direction(wind['deg'])
    }
    
    tz = timezone(timedelta(seconds=data['timezone']))
    sys = data['sys']
    filtered['sunrise'] = datetime.fromtimestamp(
        sys['sunrise'],
        timezone.utc
    ).astimezone(tz)
    filtered['sunset'] = datetime.fromtimestamp(
        sys['sunset'],
        timezone.utc
    ).astimezone(tz)

    return filtered


def _interpret_direction(degrees):
    # Interpret the degrees value into a cardinal direction.
    # http://snowfence.umn.edu/Components/winddirectionanddegrees.htm

    # Lower bound, upper bound, direction
    cardinals = (
        (348.75, 11.25, 'N'),
        (11.25, 33.75, 'NNE'),
        (33.75, 56.25, 'NE'),
        (56.25, 78.75, 'ENE'),
        (78.75, 101.25, 'E'),
        (101.25, 123.75, 'ESE'),
        (123.75, 146.25, 'SE'),
        (146.25, 168.75, 'SSE'),
        (168.75, 191.25, 'S'),
        (191.25, 213.75, 'SSW'),
        (213.75, 236.25, 'SW'),
        (236.25, 258.75, 'WSW'),
        (258.75, 281.25, 'W'),
        (281.25, 303.75, 'WNW'),
        (303.75, 326.25, 'NW'),
        (326.25, 348.75, 'NNW'),
    )
    candidate = None
    for c in cardinals:
        # Because of the rollover at N, we have to consider this looser
        # criteria first.
        if degrees >= c[0] or degrees < c[1]:
            if not candidate:
                candidate = c
            else:
                # If between the two bounds then c is a better match than
                # previous candidate
                if degrees >= c[0] and degrees < c[1]:
                    return c[2]
    if candidate != None:
        return candidate[2]
    return None


def _get_cache_hash(latitude, longitude, units):
    sha = hashlib.sha1()
    sha.update(str(latitude).encode())
    sha.update(str(longitude).encode())
    sha.update(units.encode())
    return sha.hexdigest()


def _get_cached(latitude, longitude, units):
    hash = _get_cache_hash(latitude, longitude, units)
    cache_duration = config.get_cache_duration()
    cache_location = config.get_cache_directory() / f'last_response_{hash}.json'
    
    if not cache_location.exists():
        return None

    mtime = datetime.fromtimestamp(
        cache_location.stat().st_mtime,
        timezone.utc
    )
    curtime = datetime.now(timezone.utc)

    if curtime - mtime >  timedelta(minutes=cache_duration):
        return None

    return json.load(open(cache_location))
    

def _get_fresh(latitude, longitude, units):
    api_key = config.get_api_key()
    http = urllib3.PoolManager()
    response = http.request(
        'GET',
        f'https://api.openweathermap.org/data/2.5/weather?lat={latitude}&lon={longitude}&appid={api_key}&units={units}'
    )
    if response.status != 200:
        raise APIError(
            f"Received error response from API: {response.status}",
            response.data
        )
    data = json.loads(response.data)
    _cache_response(data, latitude, longitude, units)
    return data


def _cache_response(data, latitude, longitude, units):
    hash = _get_cache_hash(latitude, longitude, units)
    cache_location = config.get_cache_directory() / f'last_response_{hash}.json'
    json.dump(data, open(cache_location, 'w'))


class APIError(Exception):
    
    def __init__(self, message, data):
        super().__init__(message)
        self.data = data

