from ctypes import ArgumentError
from pathlib import Path
import click
from ._location import locate
from ._openweathermap import get_weather, APIError
from . import _config as config


@click.group()
def _cli():
    pass


@_cli.command()
@click.option('--longitude')
@click.option('--latitude')
@click.option('--address')
@click.option('--location', envvar="WF_LOCATION")
@click.option('--template')
@click.option('--units', default='metric')
@click.option('--out', type=click.Path(path_type=Path))
def fetch(longitude, latitude, address, location, template, units, out):

    if location != None:
        try:
            (latitude, longitude) = config.get_named_location(location)
        except ArgumentError:
            click.echo("The specified location was not found.")
            return 1

    if address != None:
        try:
            (latitude, longitude) = locate(address)
        except ValueError:
            click.echo("Location could not be determined from the provided address")
            return 1
    
    if _location_partially_specified(location, address, latitude, longitude):
        click.echo("Both longitude and latitude options are required if either is specified")
        return 1

    if latitude == None:
        # No location was specified - use default if there is one.
        default_location = config.get_default_location()
        if default_location != None:
            try:
                (latitude, longitude) = config.get_named_location(
                    default_location
                )
            except ArgumentError:
                # Shouldn't happen because the default should be cleared
                # if the location it refers to is deleted
                click.echo("The default location no longer exists.")
                return 1

    if config.get_api_key() == None:
        click.echo("API key for OpenWeatherMap.org has not been set.")
        return 1

    weather = None
    try:
        weather = get_weather(latitude, longitude, units)
    except APIError:
        click.echo("Failed to retrieve weather data from the API.")
        return 1
    
    formatted = None
    try:
        formatted = _apply_template(weather, template)
    except ArgumentError as e:
        click.echo(e.args[0])
        return 1

    try:
        _output(formatted, out)
    except IOError:
        click.echo("Failed to write output file.")
        return 1

    return 0


def _location_partially_specified(location, address, latitude, longitude):
    if address != None or location != None:
        return False
    return (
        (latitude == None and longitude != None) or
        (longitude == None and latitude != None)
    )


def _apply_template(weather, template_name):
    subs = (
        ('icon', weather['icon']),
        ('icon_colour', weather['icon_colour']),
        ('temperature', weather['temperature']),
        ('feels_like', weather['feels_like']),
        ('calculated_at', weather['calculated_at']),
        ('pressure', weather['pressure']),
        ('humidity', weather['humidity']),
        ('sunrise', weather['sunrise'].strftime('%H:%M')),
        ('sunset', weather['sunset'].strftime('%H:%M')),
        ('wind_speed', weather['wind']['speed']),
        ('wind_direction', weather['wind']['direction']),
    )
    if template_name == None:
        template_name = config.get_default_template()
    if template_name == None:
        # TODO: Default output should include the specified units.
        template = "|temperature|"
    else:
        template = config.get_template(template_name)
        if template == None:
            raise ArgumentError("Specified template does not exist.")
    formatted = template
    for sub in subs:
        formatted = formatted.replace(f'|{sub[0]}|', str(sub[1]))
    return formatted


def _output(formatted, out):
    if not out:
        click.echo(formatted)
        return

    with open(out.expanduser().resolve(), 'w') as f:
        f.write(formatted)


@_cli.command(help="Save a named location")
@click.option('--longitude')
@click.option('--latitude')
@click.option('--address')
@click.argument('name')
def save_location(longitude, latitude, address, name):
    if address != None:
        try:
            (latitude, longitude) = locate(address)
        except ValueError:
            click.echo("Location could not be determined from the provided address")
            return
    
    if _location_partially_specified(None, address, latitude, longitude):
        click.echo("Both longitude and latitude options are required if either is specified")
        return

    if latitude == None:
        # No location was specified
        click.echo("No location information was specified. Use `--address` or `--latitude` and `--longitude`.")
        return
    
    config.save_named_location(name, latitude, longitude)
    click.echo("Location saved.")


@_cli.command(help="Delete a named location")
@click.argument('name')
def delete_location(name):
    try:
        config.delete_location(name)
    except ArgumentError:
        click.echo("Location not found.")
        return
    except KeyError:
        click.echo("Location not found.")
        return
    click.echo("Location deleted.")



@_cli.command(help="Set the default location")
@click.argument("name")
def set_default_location(name):
    config.set_default_location(name)
    click.echo("Default location set.")


@_cli.command(help="Set the default template")
@click.argument("name")
def set_default_template(name):
    config.set_default_template(name)
    click.echo("Default template set.")


@_cli.command(help="Set OpenWeatherMap API key")
@click.argument("key")
def set_key(key):
    config.set_api_key(key)
    click.echo("API key set.")


@_cli.command(help="Set default units")
@click.argument("units")
def set_units(units):
    if units not in config.valid_units:
        click.echo(
            f"Invalid units. Specify one of {', '.join(config.valid_units)}"
        )
        return
    config.set_units(units)
    click.echo("Default units set.")


@_cli.command(help="Save a named output template")
@click.argument('name')
@click.argument('template')
def save_template(name, template):
    config.save_template(name, template)
    click.echo("Template saved")


@_cli.command(help="Delete a named template")
@click.argument('name')
def delete_template(name):
    try:
        config.delete_template(name)
    except ArgumentError:
        click.echo("Template not found.")
        return
    except KeyError:
        click.echo("Template not found.")
        return
    click.echo("Template deleted.")


@_cli.command(help="Set the cache time")
@click.argument('duration', type=int)
def set_cache(duration: int):
   config.set_cache_duration(duration)
   click.echo("Cache duration set.")


def main():
    _cli()

