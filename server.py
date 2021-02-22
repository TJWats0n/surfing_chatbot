# import flask dependencies
from flask import Flask, request, make_response, jsonify
from logic import results

# initialize the flask app
app = Flask(__name__)

# default route
@app.route('/')
def hello_world():
    return 'Hello World!'

# function for responses


# create a route for webhook
@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    req = request.get_json(force=True)
    resp = results(req)
    return make_response(jsonify(resp))



# run the app
if __name__ == '__main__':
   app.run(debug=True)