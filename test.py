from flask import Flask, request
import json

app = Flask(__name__)

@app.route('/', methods=['POST'])
def hello_world():
	print "asasdad"
	data =  request.get_data()
	print "asd"
	data = json.loads(data)
	print data

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=8500)