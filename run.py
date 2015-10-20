from flask import Flask, request, render_template, url_for
from flask.ext.sqlalchemy import SQLAlchemy
import sqlite3
import sys
import json
import requests

app = Flask(__name__, template_folder='templates')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)

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
	data = restock(data)

	if data == None:
		return json.dumps({"404" : "Manager username not found"})
	else:
		
		#Enviar dados para REST do manel
		url = "http://ogaviao.ddns.net:80/replenishstock"               #URL DO MANEL
		headers = {'Content-Type': 'application/json'}					#content type
		r = requests.post(url, data=json.dumps(data), headers=headers) 	#efetua o request
		return json.dumps({"200" : "OK"})


@app.route('/doreservation')
def doreservation():

	#recebe dados da reservation app do user
	data =  request.get_data()
	data = json.loads(data)

	#Enviar dados para REST do manel
	url = "http://ogaviao.ddns.net:80/doreservation"            	    #URL DO MANEL
	headers = {'Content-Type': 'application/json'}						#content type
	r = requests.post(url, data=json.dumps(data), headers=headers) 	    #efetua o request
	return json.dumps({"200" : "OK"})


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
		return getLocalidade(sms[4])

	elif sms[2] == 'add':
		print "add"
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
			url = "http://ogaviao.ddns.net:80/replenishstock"               #URL DO MANEL
			headers = {'Content-Type': 'application/json'}					#content type
			r = requests.post(url, data=json.dumps(data), headers=headers) 	#efetua o request
			return json.dumps({"200" : "OK"})

	elif sms[2] == 'reservation':
		print "reserv"

	else:
		return json.dumps({"406" : "Not acceptable"})







@app.route('/signup')
def signup():

    # read the posted values from the UI
    name =  request.args.get('inputName')
    localization = request.args.get('localization')
    username = request.args.get('username')

    if name and localization and username:
    	rest = Restaurant(name, localization, username)
    	db.session.add(rest)
    	db.session.commit()
    	return render_template('accepted.html')
    else:
    	return render_template('error.html')


@app.route('/')
def home():
	return render_template('index.html')


def startSMSservice():
	data = json.dumps({"serviceurl" : "http://46.101.14.39:80/getSMS", "name":"ComposerDave"})
	url = "http://es2015sms.heldermoreira.pt:8080/SMSgwServices/smsmessaging/subscrive/service"            	#URL DO LUIS
	headers = {'Content-Type': 'application/json'}						#content type
	r = requests.put(url, data=data, headers=headers) 	#efetua o request
	print json.loads(data)

def setREGEXtoSMS():

	data = json.dumps({"url" : "http://46.101.14.39:80/getSMS", "rules": [ { "regex":"#1tapmeal#city#.*"}, {"regex":"#1tapmeal#add#.*"} ,{"regex":"#1tapmeal#reservation#.*"}] })
	url = "http://es2015sms.heldermoreira.pt:8080/SMSgwServices/smsmessaging/subscrive/service/rule"            	#URL DO LUIS
	headers = {'Content-Type': 'application/json'}						#content type
	r = requests.put(url, data=data, headers=headers) 	#efetua o request
	print json.loads(data)

def getLocalidade(city):
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



if __name__ == '__main__':
	db.create_all()
	#insert
	r1 = Restaurant('restaurant 1', 'Aveiro', 'dave1')
	r2 = Restaurant('restaurant 2', 'Aveiro', 'dave2')
	r3 = Restaurant('restaurant 3', 'Aveiro', 'dave3')
	m1 = Meal('Arroz com frango',13)
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



