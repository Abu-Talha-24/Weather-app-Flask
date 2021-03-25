from flask import Flask, render_template, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import sys
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///weather.db'
db = SQLAlchemy(app)
app.secret_key = "super secret key"

class City(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    def __repr__(self):
        return f"<City {repr(self.name)}>"


db.create_all()


def get_daytime(time, response):
    """
    :param time: timestamp in unix seconds
    :param response: response from weather api
    :return: str day/evening-morning/night
    """
    hr_gap = 1
    if response['sys']['sunrise'] < time <= response['sys']['sunset'] - 3600 * hr_gap:
        return "day"
    # if hr_gap before and after sunrise or hr_gap before after sunset
    elif response['sys']['sunrise'] - 3600 * hr_gap < time < response['sys']['sunrise'] + 3600 * hr_gap or \
            response['sys']['sunset'] - 3600 * hr_gap < time < response['sys']['sunset'] + 3600 * hr_gap:
        return "evening-morning"
    else:
        return "night"


def call_weather_api(city, url, key, id, units="metric"):
    """

    :param id:
    :param city: city name
    :param url: url of weather api site
    :param key: API key
    :param units: metric/imperial
    :return: dict{city:response}
             with response
             condition: weather state
             temp: temperature
             time_now: current time UTC
             time_of_day: day state
    """
    params = {'q': city, 'appid': key, 'units': units}
    r = requests.get(url, params=params)
    resp = r.json()
    if not r.raise_for_status():
        time_now = int(datetime.now(tz=timezone.utc).timestamp())
        time_of_day = get_daytime(time_now, resp)
        return {resp['name']: {'condition': resp['weather'][0]['main'],
                               'temp': str(resp['main']['temp']),
                               'time_now': time_now, 'time_of_day': time_of_day, 'id': id}}


@app.route('/', methods=['GET', 'POST'])
def add_city():
    try:
        weather_info = {}
        api_key = '8051410ef2db58c4bf0e4aabc64d6479'
        weather_endpoint = "https://api.openweathermap.org/data/2.5/weather"

        if request.method == 'GET':
            for city in City.query.all():
                app.logger.info(str(city.name))
                weather_info.update(call_weather_api(city.name, weather_endpoint, api_key, id=city.id))
            return render_template('index.html', weather=weather_info)

        if request.method == 'POST':
            city = request.form['city_name']
            r = requests.get(f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid=8051410ef2db58c4bf0e4aabc64d6479')
            resp = r.json()
            already_in = False
            for x in City.query.all():
                if city == x.name:
                    already_in = True
            if already_in:
                flash("The city has already been added to the list!")
                return redirect('/')
            elif resp['cod'] != "404":
                new_city = City(name=city)
                db.session.add(new_city)
                db.session.commit()
                return redirect('/')
            else:
                flash("The city doesn't exist!")
                return redirect('/')


    except requests.HTTPError as e:
        app.logger.error(str(e))
        # return "Invalid request, city name must be valid and exist!"
        flash("The city doesn't exist!")
        return redirect('/')
    except requests.RequestException as e:
        app.logger.error(str(e))
        return "Unable to connect to Weather API site, please try later!"
    except FileNotFoundError as e:
        app.logger.error(str(e))
        return "Error occurred while processing, API unavailable"


@app.route('/delete/<city_id>', methods=['GET', 'POST'])
def delete(city_id):
    city = City.query.filter_by(id=city_id).first()
    db.session.delete(city)
    db.session.commit()
    return redirect('/')


# don't change the following way to run flask:
if __name__ == '__main__':
    if len(sys.argv) > 1:
        arg_host, arg_port = sys.argv[1].split(':')
        app.run(host=arg_host, port=arg_port)
    else:
        app.run(debug=True)
