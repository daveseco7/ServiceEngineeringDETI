from flask import Flask, request, render_template, url_for, session, redirect
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
import datetime
import sqlite3
import sys
import json
import requests
from multiprocessing import Process

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
	date = db.Column(db.Integer)
	meal = db.Column(db.String(50))
	image = db.Column(db.String(250), nullable=True)


	def __init__(self, name, price, date, meal,image):
		self.name = name
		self.price =  price
		self.date = date
		self.meal = meal
		self.image = image

class Menu(db.Model):
	__tablename__ = "menu"
	menuID = db.Column(db.Integer, primary_key=True)
	restaurantID = db.Column(db.Integer, db.ForeignKey("restaurant.restaurantID"))
	restaurant = db.relationship(Restaurant)
	mealID = db.Column(db.Integer, db.ForeignKey("meal.mealID"))
	meal = db.relationship(Meal)

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

@app.route('/restaurants', methods=['POST'])
def getRestaurants():
	
	#recebe dados da manager app
	data =  request.get_data()
	data = json.loads(data)

	#Token check
	response = json.dumps({"token": data["token"]})
	url = "http://idp.moreirahelder.com/api/getuser"  
	headers = {'Content-Type': 'application/json'}	
	r = requests.post(url, data=response, headers=headers)
	response = json.loads(r.text)
	

	if response["result"] == "error":
		print "invalid token"
		return json.dumps({"200" : "INVALID TOKEN"})

	username = response["username"]
	rest = Restaurant.query.filter_by(managerusername=username).all()

	dic = {"restaurants" : []}
	for i in rest:
		dic["restaurants"].append({"name" : i.restaurantname, "id":i.restaurantID})

	return json.dumps(dic)



@app.route('/localization/<path:path>/<meal>/<date>', methods=['GET']) 
@app.route('/localization/<path:path>/<meal>', methods=['GET'])
@app.route('/localization/<path:path>', methods=['GET'])
def Localidade(path, meal=None, date=None):

	if request.method == 'GET':
		if meal and date:
			time = int(datetime.datetime.strptime(date, '%d-%m-%Y').strftime("%s"))
			return getLocalidade(path, meal, time)
		elif meal and not date:
			return getLocalidade(path,meal,None)
		else:
			return getLocalidade(path, None, None)

	else:
		return "Invalid request"


@app.route('/replenishstock', methods=['POST'])
def replenishstock():

	#recebe
	# {
	#     "info": [
	#         {
	#             "token": "eyJpZCI6M30.9II7kKlKmIfoVmu4PatRT_pdrHJcDB8jvnF8ogWEOU4",
	#             "providerID": 1
	#         }
	#     ],
	#     "menu": [
	#         {
	#             "price": 15,
	#             "name": "asd",
	#             "quantity": 66,
	#             "date": "26/11/2015",
	#             "url": "",
	# 			  "meal":"dinner"
	#         }
	#     ]
	# }



	#recebe dados da manager app
	data =  request.get_data()
	data = json.loads(data)

	#Token check
	response = json.dumps({"token": data["info"][0]["token"]})	
	url = "http://idp.moreirahelder.com/api/getuser"            #URL DO HELDER
	headers = {'Content-Type': 'application/json'}				#content type
	r = requests.post(url, data=response, headers=headers) 		#efetua o request
	response = json.loads(r.text)
	
	if response["result"] == "error":
		print "invalid token"
		return json.dumps({"200" : "INVALID TOKEN"})
	
	data["info"][0]["username"] = response['username']
	for item in data["menu"]:
		item["date"] = int(datetime.datetime.strptime(item["date"], '%d/%m/%Y').strftime("%s"))

	data = restock(data)
	print data
	if data == None:
		print "Manager not found"
		return json.dumps({"200" : "INVALID ARGUMENTS (DATE, RESTAURANT, MANAGER)"})
	else:
		#Enviar dados para REST do manel
		url = "http://ogaviao.ddns.net:80/replenishstock"               	#URL DO MANEL
		#headers = {'Content-Type': 'application/json'}						#content type
		#r = requests.post(url, data=data, headers=headers) 	#efetua o request
		return json.dumps({"200" : "OK"})


@app.route('/doreservation', methods=['POST'])
def doreservation():

	#recebe
	#{
    	#"city": "Aveiro",
    	#"restaurant": "restaunrant1",
    	#"meal": "peixe",
    	#"quantity": "2",
    	#"timestamp": "22/11/2015:18:00"
    	#"token":"asdasd"
	#}
	
	print "doreservation"
	#recebe dados da reservation app do user
	data =  request.get_data()
	data =json.loads(data)

	print data
	
	#Token check
	response = json.dumps({"token": data["token"]})
	url = "http://idp.moreirahelder.com/api/getuser"            											#URL DO HELDER
	headers = {'Content-Type': 'application/json'}															#content type
	r = requests.post(url, data=response, headers=headers) 														#efetua o request
	response = json.loads(r.text)

	if response["result"] == "error":
                print "invalid token"
		return json.dumps({"200" : "INVALID TOKEN"})
	else:
		data["username"] = response['username']
		time = int(datetime.datetime.strptime(data['timestamp'], '%d/%m/%Y:%H:%M').strftime("%s"))
		data= json.dumps({"username": response["username"], "city": data["city"],"restaurant":data["restaurant"],"meal":data["meal"],"quantity":data["quantity"],"timestamp":time, "clientID": response["user_id"]})
		data = json.loads(data)
		data= doReserve(data)
		data = json.loads(data)

		if data == None:
			print "not found"
			return json.dumps({"200" : "RESTAURANT NOT FOUND"})
		
		else:
			response = json.dumps(data)
			#Enviar dados para REST do manel
			url = "http://ogaviao.ddns.net:80/doreservation"            	    #URL DO MANEL
			headers = {'Content-Type': 'application/json'}						#content type
			r = requests.post(url, data=response, headers=headers) 	    		#efetua o request
			return json.dumps({"200" : "oK"})


	#envia
	#{
	#"username":dave,
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
	print number
	requestID = str(data['requestid'])

	#verificar 
	sms = sms.split('#')

	if sms[2] == "city":
		print "na city"

		def proc1(localidade, requestID):
			print "inside thread 1"
			response = ""
			data = getLocalidade(localidade)
			data = json.loads(data)
			for rest in data['Restaurants']:
				response += "RESTAURANT: \"" + rest['Name'] + "\""
				for menu in rest['Menu']:
					response += " MENU: " + menu['item'] + " PRICE: " +  str(menu['price']) + " "
				response += "\n"
			response = json.dumps({"body" : response , "status": 200})
			url = "http://es2015sms.heldermoreira.pt/SMSgwServices/smsmessaging/outbound/"+ requestID +"/response/"    			
			headers = {'Content-Type': 'application/json'}								
			r = requests.post(url, data=response, headers=headers)
			print "end thread 1"
			return json.dumps({"200" : "OK"})


		t = Process(target=proc1, args=(sms[3], requestID))
		t.start()
		return json.dumps({"200" : "OK"})


	elif sms[2] == 'add':
		print "add"

		def proc2(number, requestID, sms):
			print "inside thread 2"
			#Username check
			response = json.dumps({"phone":number})
			url = "http://idp.moreirahelder.com/api/getuser"            											#URL DO HELDER
			headers = {'Content-Type': 'application/json'}															#content type
			r = requests.post(url, data=response, headers=headers) 														#efetua o request
			response = json.loads(r.text)

			if response['result'] == "error":
				SMSresponse = json.dumps({"body" : "Number not registred!" , "status": 200})
				url = "http://es2015sms.heldermoreira.pt/SMSgwServices/smsmessaging/outbound/"+ requestID +"/response/"
				headers = {'Content-Type': 'application/json'}
				r = requests.post(url, data=SMSresponse, headers=headers)
				return json.dumps({"200" : "PHONE NUMBER NOT REGISTED"})

			username = response['username']
			data = json.dumps({"info":[{"username": username}],"menu":[]})
			data = json.loads(data)

			i=4
			while i <= len(sms)-3:
				data["menu"].append({"name": sms[i],"price": int(sms[i+1]), "quantity":int(sms[i+2])})
				i= i+3

			data = restock(data)
			if data == None:
				SMSresponse = json.dumps({"body" : "Manager not found" , "status": 200})
				url = "http://es2015sms.heldermoreira.pt/SMSgwServices/smsmessaging/outbound/"+ requestID +"/response/"  
				headers = {'Content-Type': 'application/json'}
				r = requests.post(url, data=SMSresponse, headers=headers) 	
				return json.dumps({"200" : "MANAGER NOT FOUND"})

			print "sending"
			response = data
			print response
			#Enviar dados para REST do manel
			url = "http://ogaviao.ddns.net:80/replenishstock"  
			headers = {'Content-Type': 'application/json'}		
			r = requests.post(url, data=response, headers=headers) 


			SMSresponse = json.dumps({"body" : "Menu added!" , "status": 200})
			url = "http://es2015sms.heldermoreira.pt/SMSgwServices/smsmessaging/outbound/"+ requestID +"/response/"    					
			headers = {'Content-Type': 'application/json'}																
			r = requests.post(url, data=SMSresponse, headers=headers)
			print "end thread 2" 														
			return json.dumps({"200" : "OK"})


		t = Process(target=proc2, args=(number, requestID,sms))
		t.start()
		return json.dumps({"200" : "OK"})

	elif sms[2] == 'reservation':
		print "reservation"

		def proc3(number, requestID,sms):

			print "inside thread 3"
			#Username check
			response = json.dumps({"phone":number})
			url = "http://idp.moreirahelder.com/api/getuser"            											#URL DO HELDER
			headers = {'Content-Type': 'application/json'}															#content type
			r = requests.post(url, data=response, headers=headers) 														#efetua o request
			response = json.loads(r.text)

			if response['result'] == "error":
				SMSresponse = json.dumps({"body" : "Number not registred!" , "status": 200})
				url = "http://es2015sms.heldermoreira.pt/SMSgwServices/smsmessaging/outbound/"+ requestID +"/response/"
				headers = {'Content-Type': 'application/json'}
				r = requests.post(url, data=SMSresponse, headers=headers)
				return json.dumps({"200" : "PHONE NUMBER NOT REGISTED"})

			username = response['username']
			
			time = int(datetime.datetime.strptime(sms[7], '%d/%m/%Y:%H:%M').strftime("%s"))
			data = json.dumps({"username":username,"city":sms[3],"restaurant":sms[4],"meal":sms[5],"quantity":int(sms[6]),"timestamp":time, "clientID":int(response['user_id'])})
			data =json.loads(data)
			response = doReserve(data)
			print response

			if response == None:
				SMSresponse = json.dumps({"body" : "Invalid items for reservation!" , "status": 404})
				url = "http://es2015sms.heldermoreira.pt/SMSgwServices/smsmessaging/outbound/"+ requestID +"/response/"
	 			headers = {'Content-Type': 'application/json'}	
	 			r = requests.post(url, data=SMSresponse, headers=headers) 	
	 			return json.dumps({"200" : "INVALID ITEMS FOR RESERVATION!"})			

	 		#Do a reservation
			print "sending"
			url = "http://ogaviao.ddns.net:80/doreservation"            	    
			headers = {'Content-Type': 'application/json'}							
			r = requests.post(url, data=response, headers=headers) 	    

			SMSresponse = json.dumps({"body" : "Reservation done!" , "status": 200})
			url = "http://es2015sms.heldermoreira.pt/SMSgwServices/smsmessaging/outbound/"+ requestID +"/response/"
			headers = {'Content-Type': 'application/json'}																			
			r = requests.post(url, data=SMSresponse, headers=headers) 																		
			return json.dumps({"200" : "OK"})


		t = Process(target=proc3, args=(number, requestID,sms))
		t.start()
		return json.dumps({"200" : "OK"})


	else:

		SMSresponse = json.dumps({"body" : "Not acceptable!" , "status": 406})
		url = "http://es2015sms.heldermoreira.pt/SMSgwServices/smsmessaging/outbound/"+ requestID +"/response/"
		headers = {'Content-Type': 'application/json'}																									#content type
		r = requests.post(url, data=SMSresponse, headers=headers) 																						#efetua o request
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

def getLocalidade(city, meal, date):

	currentTime = int(datetime.datetime.now().strftime("%s"))
	city = city.lower()
	restaurants = Restaurant.query.filter_by(localization=city).all()
	menus = db.session.query( Meal.name, Meal.price, Meal.mealID, Meal.meal, Meal.date, Menu.restaurantID).select_from(Meal).join(Menu).join(Restaurant).filter(Meal.date>currentTime).all()	
	response = json.loads('{"Restaurants":  [ ]}')


	if date:
		if meal:
			print "date and meal"
			if meal == "lunch":
				for rest in restaurants:
					menu = []
					for item in menus:
						if rest.restaurantID == item.restaurantID and item.meal == "lunch" and item.date == int(date):
							menu.append({ "item" : item.name, "price": item.price, "itemID": item.mealID})
					response["Restaurants"].append({"Name" : rest.restaurantname, "ProviderID": rest.restaurantID,"Menu": menu})
				return json.dumps(response)

			elif meal == "dinner":
				for rest in restaurants:
					menu = []
					for item in menus:
						if rest.restaurantID == item.restaurantID and item.meal == "dinner"  and item.date == int(date):
							menu.append({ "item" : item.name, "price": item.price, "itemID": item.mealID})
					response["Restaurants"].append({"Name" : rest.restaurantname, "ProviderID": rest.restaurantID,"Menu": menu})
				return json.dumps(response)

			else:
				return json.dumps({"200":"INVALID MEAL OPTION"})
	else:
		if meal:
			print "no date but meal"
			if meal == "lunch":
				for rest in restaurants:
					menu = []
					for item in menus:
						if rest.restaurantID == item.restaurantID and item.meal == "lunch":
							menu.append({ "item" : item.name, "price": item.price, "itemID": item.mealID})
					response["Restaurants"].append({"Name" : rest.restaurantname, "ProviderID": rest.restaurantID,"Menu": menu})
				return json.dumps(response)

			elif meal == "dinner":
				for rest in restaurants:
					menu = []
					for item in menus:
						if rest.restaurantID == item.restaurantID and item.meal == "dinner":
							menu.append({ "item" : item.name, "price": item.price, "itemID": item.mealID})
					response["Restaurants"].append({"Name" : rest.restaurantname, "ProviderID": rest.restaurantID,"Menu": menu})
				return json.dumps(response)

			else:
				return json.dumps({"200":"INVALID MEAL OPTION"})
		else:
			print "localization"
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
		providerID = info['providerID']

	rest = Restaurant.query.filter_by(managerusername=username, restaurantID=providerID).first()	

	#Guarda dados na base de dados do main service
	if rest == None:
		return None

	else:
		url = None
		menu = data['menu']
		for item in menu:
			#if  int(item['date']) < int(datetime.datetime.now().strftime("%s")):
			#	print "Menu expiration date invalid"
			#	return None
			if item['url']:
				url = item['url']

			meal = Meal(item['name'], item['price'], item['date'], item['meal'],url)
			mealID = db.session.query(Meal).count()
			menu = Menu(rest.restaurantID, mealID+1)
			db.session.add(meal)
			db.session.add(menu)
			db.session.commit()
			item['itemID'] = int(mealID)

		return json.dumps(data)


def doReserve(data):

	city = data['city'].lower()
	meal=data['meal']
	restaurant=data['restaurant']
	quantity = data['quantity']
	timestamp = data['timestamp']
	clientID = data['clientID']
	username = data['username']

	itemID = db.session.query( Meal.mealID ).select_from(Meal).filter_by(name=meal).join(Menu).join(Restaurant).filter_by(localization=city).filter_by(restaurantname=restaurant).first()	
	print itemID	
	if itemID == None:
		return None
	else:
		return json.dumps({"username":username,"itemID":int(itemID[0])-1, "quantity":int(quantity),"clientID":int(clientID), "timestamp": int(timestamp)})





if __name__ == '__main__':
	db.create_all()
	#insert
	#r1 = Restaurant('restaurant 1', 'aveiro', 'dave1')
	#r2 = Restaurant('restaurant 2', 'aveiro', 'dave2')
	#r3 = Restaurant('restaurant 3', 'aveiro', 'dave3')
	#m1 = Meal('peixe',13)
	#m2 = Meal('Atum em lata',14)
	#men1 = Menu(1,1)
	#men2 = Menu(2,2)
	#db.session.add(r1)
	#db.session.add(r2)
	#db.session.add(r3)
	#db.session.add(m1)
	#db.session.add(m2)
	#db.session.add(men1)
	#db.session.add(men2)
	#db.session.commit()

	print "a enviar dados"
	#startSMSservice()
	#setREGEXtoSMS()
	app.run(host='0.0.0.0',port=80)

