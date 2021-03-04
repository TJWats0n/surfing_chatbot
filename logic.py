#this file contains calculations and handling of stuff
import pandas as pd
import requests
from APIKEY import Key
import arrow

def results(req):
    #this function distributes request to respective function based on intent
    intent = req.get('queryResult').get('intent').get('displayName')
    if intent == 'buy':
        return buy(req)
    elif intent == 'check_conditions':
        return conditions(req)
    elif intent == 'add_spot':
        return add_spot(req)

def calc_vol_len(height, weight, exp):
    print('calculating volume and length')
    #use formula from: https://www.surfnation.com.au/pages/how-to-choose-the-right-surfboard
    #(ability & weight) * age constant * Fitness

    #approximated factors from table Buyers guide volume table
    ability_factor = {'beginner': 0.69, 'intermediate': 0.55, 'advanced': 0.43}

    #assumption: fitness is linear with experience
    fitness_factor = {'beginner': 1.2, 'intermediate': 1.1, 'advanced': 1.05}

    age = 1.04 #for now generic addition - could be implemented as another parameter
    volume = (weight*ability_factor[exp]) * age * fitness_factor[exp]

    #taken from: https://www.degree33surfboards.com/blogs/gettin-pitted/14071121-what-size-of-surfboard-should-i-get
    length_factor = {'beginner': 90, 'intermediate': 60, 'advanced': 20}
    length = height + length_factor[exp]

    print('volume and length are known')
    return volume, length


def infer_name(spot):
    return 0
    #some string matching logic


def sanity_checks(height=100, weight=80, max_price=150, spot='le petit minou', exp=1):
    print('checking sanity')
    # sanity checks: returns 0 is everything is good, Error message for respective parameters
    if height > 230 or height < 100:
        return {'fulfillmentText': u'Your height needs to be between 100-230cm. Please try again.'}

    if weight < 35 or weight > 150:
        return {'fulfillmentText': u'Your weight needs to be between 35-150kg. Please try again.'}

    if max_price < 100:
        return {'fulfillmentText': u'We are sorry - there is no board available for your budget.'}

    if exp != 'beginner' and exp != 'advanced' and exp != 'intermediate':
        return {'fulfillmentText': u'We couldn\'t resolve your experience level. Please stay in the range of 0-10.'}

    surfspots = pd.read_csv('surfspots.csv')
    if spot.lower() not in surfspots['name'].tolist():
        infer_name(spot)
        return {'fulfillmentText': u'Unfortunately your surfspot is not available yet. You can add it by typing "add surfspot".'}

    print('sanity checks were successful')
    return 0

def get_forecast(lat, lon, hours):
    print('getting forecast from API...')

    #get forecast for next 4 hours
    start = arrow.now().floor('hour')
    start = start.shift(hours=1)
    end = arrow.now().shift(hours=hours).floor('hour')

    response = requests.get(
        'https://api.stormglass.io/v2/weather/point',
        params={
            'lat': lat,
            'lng': lon,
            'start': start.to('UTC').timestamp,  # Convert to UTC timestamp
            'end': end.to('UTC').timestamp,
            # specify parameters https://docs.stormglass.io/#/sources
            'params': 'swellPeriod,windDirection,windSpeed,waveHeight',
        },
        headers={
            'Authorization': Key.api_key
        }
    )
    print('forecast received')
    return response.json()

def get_factors(swell_period, wave_height, wind_direction, wind_speed, spot_direction):

    swell_period_avg = sum(swell_period)/len(swell_period) #seconds
    wave_height_avg = sum(wave_height)/len(wave_height) #significant height in meters
    wind_direction_avg = sum(wind_direction)/len(wind_direction) #360 degrees, 0 = north
    wind_speed_avg = sum(wind_speed)/len(wind_speed) #meters/second

    if spot_direction > 339:
        end = spot_direction + 20 - 359
    else:
        end = spot_direction + 20

    if spot_direction < 20:
        start = spot_direction - 20 + 360
    else:
        start = spot_direction - 20

    end = end-start if (end - start)>0 else end-start+360
    mid = wind_direction_avg - start if (wind_direction_avg - start) > 0 else wind_direction_avg - start + 360

    # if wind from land -> flatter waves -> larger board
    if mid < end: #windirection lies within offshore (from land to sea) angle range of spot
        wind_direction_factor = 0.05
    else: wind_direction_factor = 0 #does not

    #factor wind direction by intensity of wind
    if wind_speed_avg < 3: #~11kmh
        wind_speed_factor = 0
    elif wind_speed_avg < 8:#~29kmh
        wind_speed_factor = 0.5
    else:
        wind_speed_factor = 1.0

    if swell_period_avg < 8:
        swell_period_factor = 0.05
    else:
        swell_period_factor = 0

    if wave_height_avg < 1.4:
        wave_height_factor = 0.05
    else:
        wave_height_factor = 0
    return wind_direction_factor, wind_speed_factor, swell_period_factor, wave_height_factor

def buy(req):
    height = req.get('queryResult').get('parameters').get('height').get('amount') #cm
    weight = req.get('queryResult').get('parameters').get('weight').get('amount') #kg
    exp = req.get('queryResult').get('parameters').get('experience') #beginner, intermediate or advanced
    max_price = int(req.get('queryResult').get('parameters').get('max_price')) #€

    sanity = sanity_checks(height=height, weight=weight, max_price=max_price, exp=exp)
    if sanity != 0:
        return sanity

    volume, length = calc_vol_len(height, weight, exp)

    #query database with ranges for these values (+ price)

    return {'fulfillmentText': u'Here is a list of surfboards:'}

def conditions(req):
    height = req.get('queryResult').get('parameters').get('height').get('amount')  # cm
    weight = req.get('queryResult').get('parameters').get('weight').get('amount')  # kg
    exp = req.get('queryResult').get('parameters').get('experience') #beginner, intermediate or advanced
    spot = str(req.get('queryResult').get('parameters').get('location'))

    sanity = sanity_checks(height=height, weight=weight, exp=exp, spot=spot)
    if sanity != 0:
        return sanity

    surfspots = pd.read_csv('surfspots.csv')
    surfspots = surfspots[surfspots['name']==spot]

    print('getting forecast for spot')
    lat = float(surfspots.iloc[0]['lat'])
    lon = float(surfspots.iloc[0]['lon'])
    hours = 4 #how far to scout into future
    forecast = get_forecast(lat, lon, hours)

    print('calculate boardsize for conditions')
    source = 'noaa' #several sources are offered for the values we need - checking with windguru noaa has the closest results

    swell_period, wave_height, wind_direction, wind_speed = [], [], [], []
    for entry in range(hours-1):
        swell_period.append(forecast['hours'][entry]['swellPeriod'][source])
        wave_height.append(forecast['hours'][entry]['waveHeight'][source])
        wind_direction.append(forecast['hours'][entry]['windDirection'][source])
        wind_speed.append(forecast['hours'][entry]['windSpeed'][source])

    offshore_direction = surfspots.iloc[0]['offshore_direction']
    wind_direction_factor, wind_speed_factor, swell_period_factor, wave_height_factor \
        = get_factors(swell_period, wave_height, wind_direction, wind_speed, offshore_direction)

    volume, length = calc_vol_len(height, weight, exp)
    #max 15% increase possible
    new_vol = volume * ((wind_direction_factor * wind_speed_factor) + wave_height_factor + swell_period_factor + 1)
    new_length = length
    foot = new_length//30.48
    inch = (new_length%30.48)/2.54
    return {'fulfillmentText': u'Take a {:.0f}\'{:.0f} board with about {:.0f}l volume for today\'s conditions. Bon surf!'.format(foot, inch, new_vol)}

def add_spot(req):
    #get, lat, lon, offshore_direction
    name = req.get('queryResult').get('parameters').get('name')
    lat = float(req.get('queryResult').get('parameters').get('lat'))
    lon = float(req.get('queryResult').get('parameters').get('lon'))
    offshore = int(req.get('queryResult').get('parameters').get('offshore'))

    surfspots = pd.read_csv('surfspots.csv')
    if name in surfspots['name'].tolist():
        return {'fulfillmentText': u'This place was already added before. Ask for the conditions at this place.'}
    new_spot = pd.DataFrame({'name': [name.lower()], 'lon': [lon], 'lat': [lat], 'offshore_direction': [offshore]})
    surfspots = surfspots.append(new_spot)
    surfspots.to_csv('surfspots.csv', index=False)
    return {'fulfillmentText': u'Your spot was successfully added. You can now ask for board recommendations in current conditions for this spot.'}

if __name__ == '__main__':
    conditions('test')
