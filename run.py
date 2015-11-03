from flask import Flask, request, render_template, url_for, session, redirect
from flask.ext.sqlalchemy import SQLAlchemy
import datetime
import sqlite3
import sys
import json
import requests

app = Flask(__name__, template_folder='templates')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)

app.secret_key = '1tapmeal'
authentication_server = 'http://idp.moreirahelder.com'
token_validation_server = 'http://idp.moreirahelder.com/api/getuser'
my_server = 'http://46.101.14.39:80/auth_callback'


class Restaurant(db.Model):
	__tablename__ = "restaurant"
	restaurantID = db.Column(db.Integer, primary_key=True)
	restaurantname = db.Column(db.String(50))
	localization = db.Column(db.String(50))
	managerusername = db.Column(db.String(50))
	classification = db.Column(db.Integer)

	def __init__(self, restaurantname, localization, managerusername):
		self.restaurantname = restaurantname
		self.localization = localization
		self.managerusername = managerusername

class Meal(db.Model):
	__tablename__ = "meal"
	mealID = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(50))
	price = db.Column(db.Float)

	def __init__(self, name, price):
		self.name = name
		self.price =  price

class Menu(db.Model):
	__tablename__ = "menu"
	menuID = db.Column(db.Integer, primary_key=True)
	restaurantID = db.Column(db.Integer, db.ForeignKey("restaurant.restaurantID"))
	mealID = db.Column(db.Integer, db.ForeignKey("meal.mealID"))

	def __init__(self, restaurantID, mealID):
		self.mealID = mealID
		self.restaurantID = restaurantID


def validate_token(token):
	if not token:
		return None
	headers = {'Content-type': 'application/json'}
	data = {'token': token} 
	response = requests.post(token_validation_server, json.dumps(data), headers=headers)
	data = json.loads(response.text)
	if data['result'] == "success":
		return (data['user_id'], data['username'])
	return None

@app.route("/auth_callback")
def auth_callback():
	token = request.args.get('access_token', None)
	if token:
		session['access_token'] = token
	return redirect('/')


@app.route('/localization/<path:path>', methods=['GET'])
def Localidade(path):
	
	if request.method == 'GET':
		return getLocalidade(path)
	else:
		return "Invalid request"


@app.route('/replenishstock', methods=['POST'])
def replenishstock():

	#recebe dados da manager app
	data =  request.get_data()
	data = json.loads(data)

	#Token check
	response = json.dumps({"token": data["info"][0]["token"]})
	url = "http://idp.moreirahelder.com/api/getuser"            											#URL DO HELDER
	headers = {'Content-Type': 'application/json'}															#content type
	r = requests.post(url, data=response, headers=headers) 														#efetua o request
	response = json.loads(r.text)

	if  response["username"] !=  data["info"][0]["username"]:
		return json.dumps({"404" : "Invalid Username!"})
	else:
		data = restock(data)
		if data == None:
			return json.dumps({"404" : "Manager username not found"})
		else:
			#Enviar dados para REST do manel
			url = "http://ogaviao.ddns.net:80/replenishstock"               #URL DO MANEL
			headers = {'Content-Type': 'application/json'}					#content type
			r = requests.post(url, data=json.dumps(data), headers=headers) 	#efetua o request
			return json.dumps({"200" : "OK"})


@app.route('/doreservation', methods=['POST'])
def doreservation():

	#recebe
	#{
    #"username": "dave1",
    #"city": "Aveiro",
    #"restaurnt": "restaunrant1",
    #"meal": "peixe",
    #"quantity": "2",
    #"hora": "1445556339"
    #"token":"asdasd"
	#}


	#recebe dados da reservation app do user
	data =  request.get_data()
	data =json.loads(data)
	
	#Token check
	response = json.dumps({"token": data["token"]})
	url = "http://idp.moreirahelder.com/api/getuser"            											#URL DO HELDER
	headers = {'Content-Type': 'application/json'}															#content type
	r = requests.post(url, data=response, headers=headers) 														#efetua o request
	response = json.loads(r.text)

	if  response["username"] !=  data["username"]:
		return json.dumps({"404" : "Invalid Username!"})
	else:
		time = int(datetime.datetime.strptime(data['timestamp'], '%d/%m/%Y:%H:%M').strftime("%s"))
		data = json.dumps({"username":data["username"], "city": data["city"],"restaurant":data["restaurant"],"meal":data["meal"],"quantity":data["quantity"],"timestamp":time, "clientID": response["user_id"]})
		data = json.loads(data)
		data= doReserve(data)

		if data == None:
			return json.dumps({"404" : "Manager username not found"})
		else:

			print data
			#Enviar dados para REST do manel
			url = "http://ogaviao.ddns.net:80/doreservation"            	    #URL DO MANEL
			headers = {'Content-Type': 'application/json'}						#content type
			r = requests.post(url, data=data, headers=headers) 	    #efetua o request
			return json.dumps({"200" : "OK"})


	#envia
	#{
	#"itemID": 8,
	#"quantity": 2,
	#"clientID": 12,
    #"timestamp": 1445556339
	#}	



@app.route('/getSMS', methods=['POST'])
def getSMS():
	#receber
	data = request.get_data()
	data = json.loads(data)

	sms = data['body']
	number = data['senderAddress']

	#verificar 
	sms = sms.split('#')

	if sms[2] == "city":
		print "get"
		return getLocalidade(sms[3])

	elif sms[2] == 'add':
		print "add"

		#Username check
		data = json.dumps({"phone":number})
		url = "http://idp.moreirahelder.com/api/getuser"            											#URL DO HELDER
		headers = {'Content-Type': 'application/json'}															#content type
		r = requests.post(url, data=data, headers=headers) 														#efetua o request
		response = json.loads(r.text)

		if response['result'] == "error":
			return json.dumps({"404" : "Number not registred"})
		else:
			if  response['usename'] != sms[3]:
				return json.dumps({"404" : "Invalid Username!"})

			else:
				data = json.dumps({"info":[{"username": sms[3]}],"menu":[]})
				data = json.loads(data)

				i=5
				while i <= len(sms)-3:
					data["menu"].append({"name": sms[i],"price": sms[i+1], "quantity": sms[i+2]})
					i= i+3
				
				data = restock(data)
				if data == None:
					print "error"
					return json.dumps({"404" : "Manager username not found"})
				else:
					print "sending"
					#Enviar dados para REST do manel
					url = "http://ogaviao.ddns.net:80/replenishstock"               						#URL DO MANEL
					headers = {'Content-Type': 'application/json'}											#content type
					r = requests.post(url, data=json.dumps(data), headers=headers) 							#efetua o request
					return json.dumps({"200" : "OK"})


	elif sms[2] == 'reservation':
		#1tapmeal#reservation#dave1#aveiro#restaurant 1#peixe#5#12:00
			
		#Username check
		data = json.dumps({"phone":number})
		url = "http://idp.moreirahelder.com/api/getuser"            											#URL DO HELDER
		headers = {'Content-Type': 'application/json'}															#content type
		r = requests.post(url, data=data, headers=headers) 														#efetua o request
		response = json.loads(r.text)
	
		if response['result'] == "error":
			return json.dumps({"404" : "Number not registred"})
		else:
			if  response['username'] != sms[3]:
				return json.dumps({"404" : "Invalid Username!"})

			else:
				time = time = int(datetime.datetime.strptime(sms[8], '%d/%m/%Y:%H:%M').strftime("%s")) 
				data = json.dumps({"username":sms[3],"city":sms[4],"restaurant":sms[5],"meal":sms[6],"quantity":sms[7],"timestamp":time, "clientID":response['user_id']})
				data =json.loads(data)
				response = doReserve(data)

				if response == None:
					return json.dumps({"404" : "Invalid items for reservation!"})
				

				#Do a reservation
				print "sending"
				url = "http://ogaviao.ddns.net:80/doreservation"            	    		#URL DO MANEL
				headers = {'Content-Type': 'application/json'}								#content type
				r = requests.post(url, data=response, headers=headers) 	    	#efetua o request
				return json.dumps({"200" : "OK"})
	else:
		return json.dumps({"406" : "Not acceptable"})


@app.route('/signup')
def signup():

    # read the posted values from the UI
    name =  request.args.get('inputName')
    localization = request.args.get('localization').lower()
    username = session['username']

    if name and localization and username:
    	rest = Restaurant(name, localization, username)
    	db.session.add(rest)
    	db.session.commit()
    	return render_template('accepted.html')
    else:
    	return render_template('error.html')


@app.route('/')
def home():
	token = session.get('access_token', None)
	user = validate_token(token)
	if user:
		session['username']=user[1]
		session['user_id']=user[0]
		return render_template('index.html')
	return redirect(authentication_server+"?next="+my_server)


def startSMSservice():
	data = json.dumps({"serviceurl" : "http://46.101.14.39:80/getSMS", "name":"ComposerDave"})
	url = "http://es2015sms.heldermoreira.pt:8080/SMSgwServices/smsmessaging/subscrive/service"            	#URL DO LUIS
	headers = {'Content-Type': 'application/json'}															#content type
	r = requests.put(url, data=data, headers=headers) 														#efetua o request
	print json.loads(data)

def setREGEXtoSMS():

	data = json.dumps({"url" : "http://46.101.14.39:80/getSMS", "rules": [ { "regex":"#1tapmeal#city#.*"}, {"regex":"#1tapmeal#add#.*"} ,{"regex":"#1tapmeal#reservation#.*"}] })
	url = "http://es2015sms.heldermoreira.pt:8080/SMSgwServices/smsmessaging/subscrive/service/rule"            	#URL DO LUIS
	headers = {'Content-Type': 'application/json'}																	#content type
	r = requests.put(url, data=data, headers=headers) 																#efetua o request
	print json.loads(data)

def getLocalidade(city):
	city = city.lower()
	restaurants = Restaurant.query.filter_by(localization=city).all()
	menus = db.session.query(Meal.name, Meal.price, Meal.mealID, Menu.restaurantID).select_from(Meal).join(Menu).all()
	response = json.loads('{"Restaurants":  [ ]}')
	for rest in restaurants:
		menu = []
		for item in menus:
			if rest.restaurantID == item.restaurantID:
				menu.append({ "item" : item.name, "price": item.price, "itemID": item.mealID})
		response["Restaurants"].append({"Name" : rest.restaurantname, "ProviderID": rest.restaurantID,"Menu": menu})
	return json.dumps(response)

def restock(data):

	for info in data['info']:
		username = info['username']
	
	rest = Restaurant.query.filter_by(managerusername=username).first()
	
	#Guarda dados na base de dados do main service
	if(rest.restaurantID == None ):
		return none
	else:
		menu = data['menu']
		for item in menu:
			meal = Meal(item['name'], item['price'])
			mealID = db.session.query(Meal).count()
			menu = Menu(rest.restaurantID, mealID)
			db.session.add(meal)
			db.session.add(menu)
			db.session.commit()
			item['itemID'] = mealID

		data['info'].append({"providerID":rest.restaurantID})
	return data


def doReserve(data):

	print "doreserve"

	city = data['city'].lower()
	meal=data['meal']
	restaurant=data['restaurant']
	quantity = data['quantity']
	timestamp = data['timestamp']
	clientID = data['clientID']

	print "aqui"

	itemID = db.session.query( Meal.mealID ).select_from(Meal).filter_by(name=meal).join(Menu).join(Restaurant).filter_by(localization=city).filter_by(restaurantname=restaurant).first()
	
	if itemID == None:
		return json.dumps({"404":"None existing request on DB"})
	else:
		return json.dumps({"itemID":2, "quantity":int(quantity),"clientID":int(clientID), "timestamp": int(timestamp)})





if __name__ == '__main__':
	db.create_all()
	#insert
	r1 = Restaurant('restaurant 1', 'aveiro', 'dave1')
	r2 = Restaurant('restaurant 2', 'aveiro', 'dave2')
	r3 = Restaurant('restaurant 3', 'aveiro', 'dave3')
	m1 = Meal('peixe',13)
	m2 = Meal('Atum em lata',14)
	men1 = Menu(1,1)
	men2 = Menu(2,2)
	db.session.add(r1)
	db.session.add(r2)
	db.session.add(r3)
	db.session.add(m1)
	db.session.add(m2)
	db.session.add(men1)
	db.session.add(men2)
	db.session.commit()

	print "a enviar dados"
	startSMSservice()
	setREGEXtoSMS()
	app.run(host='0.0.0.0',port=80)



