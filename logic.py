#this file contains calculations and handling of stuff


def results(req):
    # fetch action from json
    action = req.get('queryResult').get('parameters').get("pizza")

    # return a fulfillment response
    return {'fulfillmentText': u'La pizza qui vous intéresse est : '+str(action)}