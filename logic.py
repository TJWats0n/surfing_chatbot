#this file contains calculations and handling of stuff
import pandas as pd

def results(req):
    # fetch intent from json
    intent = req.get('queryResult').get('intent').get('displayName')
    if intent == 'buy':
        return buy(req)
    else:
        return conditions(req)

def calc_vol_len(height, weight, exp):
    print('calculating volume and length')
    #use formula from: https://www.surfnation.com.au/pages/how-to-choose-the-right-surfboard
    #(ability & weight) * age constant * Fitness

    if exp <= 3:
        exp = 'beginner'
    elif exp > 3 & exp <=7:
        exp = 'intermediate'
    else:
        exp = 'advanced'

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
    return (volume, length)


def infer_name(spot):
    return 0
    #some string matching logic

def sanity_checks(height=100, weight=80, max_price=150, spot='le petit minou', exp=1):
    print('checking sanity')
    # sanity checks: returns 0 is everything is good, Error message for respective parameters
    if height > 230 or height < 100:
        return {'fullfillmentText': 'Your height needs to be between 100-230cm. Please try again.'}

    if weight < 35 or weight > 150:
        return {'fullfillmentText': 'Your weight needs to be between 35-150kg. Please try again.'}

    if max_price < 100:
        return {'fullfillmentText': 'We are sorry - there is no board available for your budget.'}

    if exp < 0 or exp > 10:
        return {'fullfillmentText': 'Your experience level is out of range. Please choose a value between'
                                     '0-10 where 0 is beginner and 10 is advanced'}

    surfspots = pd.read_csv('surfspots.csv', delimiter=';')
    if spot.lower() not in surfspots.name.to_list():
        infer_name(spot)
        return {'fullfillmentText': 'Unfortunately your surfspot is not available yet. You can add it by typing "add surfspot".'}

    print('sanity checks were successful')
    return 0


def buy(req):
    height = req.get('queryResult').get('parameters').get('height').get('amount') #cm
    weight = req.get('queryResult').get('parameters').get('weight').get('amount') #kg
    exp = int(req.get('queryResult').get('parameters').get('experience')) #1-10
    max_price = int(req.get('queryResult').get('parameters').get('max_price')) #€

    sanity = sanity_checks(height=height, weight=weight, max_price=max_price, exp=exp)
    if sanity != 0:
        return sanity

    volume, length = calc_vol_len(height, weight, exp)

    #query database with ranges for these values (+ price)

    return {'fulfillmentText': u'Here is a list of surfboards:'}

def conditions(req):
    return 0
