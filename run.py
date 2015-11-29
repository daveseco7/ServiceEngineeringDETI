from flask import Flask, request, render_template, url_for, session, redirect
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy import func 
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
	classification = db.Column(db.Float)
	coordenates = db.Column(db.String(50))

	def __init__(self, restaurantname, localization, managerusername, coordenates):
		self.restaurantname = restaurantname
		self.localization = localization
		self.managerusername = managerusername
		self.classification = 0.0
		self.coordenates = coordenates

class Reviews(db.Model):
	__tablename__ = "reviews"
	reviewID = db.Column(db.Integer, primary_key=True)
	restaurantID = db.Column(db.Integer, db.ForeignKey("restaurant.restaurantID"))
	restaurant = db.relationship(Restaurant)
	userID = db.Column(db.Integer)
	review = db.Column(db.Integer)

	def __init__(self, restaurantID, userID, review):
		self.restaurantID = restaurantID
		self.userID = userID
		self.review = review


class Meal(db.Model):
	__tablename__ = "meal"
	mealID = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(50))
	price = db.Column(db.Float)
	date = db.Column(db.Integer)
	meal = db.Column(db.String(50))
	image = db.Column(db.String(), nullable=True)

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


@app.route('/reservationsByUser', methods=['POST'])
def getReservations():

	data = request.get_data()
	data = json.loads(data)

	#Token check
	response = json.dumps({"token": data["token"]})
	url = "http://idp.moreirahelder.com/api/getuser"            								#URL DO HELDER
	headers = {'Content-Type': 'application/json'}												#content type
	r = requests.post(url, data=response, headers=headers) 										#efetua o request
	response = json.loads(r.text)

	if response["result"] == "error":
		print "invalid token"
		return json.dumps({"200" : "INVALID TOKEN"})
	else:
		username = response['username']
		url = "http://ogaviao.ddns.net:80/userresv/"+username     	#URL DO MANEL
		r = requests.get(url) 										#efetua o request
		data = json.loads(r.text)

		currentTime = int(datetime.datetime.now().strftime("%s")) -24*60*60

		response = {}
		menu = []
		for reserv in data["reservations"]:
			if 	currentTime < int(reserv["timestamp"]):
				info = Meal.query.filter((Meal.mealID-1) == int(reserv["itemID"])).all()
				for i in info:
					dateString = datetime.datetime.fromtimestamp(int(reserv["timestamp"])).strftime('%d/%m/%Y %H:%M')
					menu.append({ "item" : i.name, "price": i.price, "itemID": i.mealID, "meal": i.meal, "date":i.date, "url" : i.image,"reserved":reserv["quantity"], "reservation_date": dateString})
	
		response["reservations"] = menu
		return json.dumps(response)



@app.route('/review', methods=['POST'])
def setReview():
	#recebe
	#{
	#"restaurantID": 1,
	#"review" : 3 ,
	#"token":"asdasdads"
	#}

	data = request.get_data()
	data = json.loads(data)

	#Token check
	response = json.dumps({"token": data["token"]})
	url = "http://idp.moreirahelder.com/api/getuser"            								#URL DO HELDER
	headers = {'Content-Type': 'application/json'}												#content type
	r = requests.post(url, data=response, headers=headers) 										#efetua o request
	response = json.loads(r.text)

	if response["result"] == "error":
		print "invalid token"
		return json.dumps({"200" : "INVALID TOKEN"})
	else:
		username = response['username']
		user_id = response['user_id']

	history = Reviews.query.filter_by(userID=user_id, restaurantID = data["restaurantID"]).first()

	if history != []:
		print "a actualizar"
		print int(data["review"])
		history.review = int(data["review"])
		db.session.commit()

	else:
		review = Reviews(data["restaurantID"], user_id, data["review"])
		db.session.add(review)
		db.session.commit()

	result = db.session.query(func.avg(Reviews.review)).first()
	rest = Restaurant.query.filter_by(restaurantID = data["restaurantID"]).first()
	rest.classification = float(result[0])
	db.session.commit()
	return json.dumps({"classification" : float(result[0])})



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
		dic["restaurants"].append({"name" : i.restaurantname, "id":i.restaurantID, "classification" : i.classification})

	return json.dumps(dic)


@app.route('/getReservations/<restaurantID>', methods=['GET'])
def reservs(restaurantID):
	
	#Enviar dados para REST do manel
	url = "http://ogaviao.ddns.net:80/reservationsnumber/"+restaurantID 	#URL DO MANEL
	r = requests.get(url) 	    											#efetua o request
	data = json.loads(r.text)
	
	response = {}
	menu = []
	for item in data["reservated"]:
		info = Meal.query.filter((Meal.mealID-1) == int(item["itemID"])).all()
		for i in info:
			menu.append({ "item" : i.name, "price": i.price, "itemID": i.mealID, "meal": i.meal, "date":i.date, "url" : i.image,"reserved":item["quantity"]})
	
	response["Menus"] = menu
	return json.dumps(response)


@app.route('/getReservationsByDate', methods=['POST'])
def reservsDate():

	data =  request.get_data()
	data = json.loads(data)

	response = json.dumps({"date":data["date"]})
	url = "http://ogaviao.ddns.net:80/dayreserv/"+ str(data["restaurantID"]) 	#URL DO MANEL
	headers = {'Content-Type': 'application/json'}								#content type
	r = requests.post(url, data=response, headers=headers) 						#efetua o request
	data = json.loads(r.text)

	print data

	response = {}
	menu = []
	for item in data["reservated"]:
		i = Meal.query.filter((Meal.mealID-1) == int(item["itemID"])).first()
		reservs = []
		for reserv in item["reservations"]:
			dateString = datetime.datetime.fromtimestamp(int(reserv["timestamp"])).strftime('%d/%m/%Y %H:%M')
			reservs.append({"username": reserv["username"], "reserved_quantity":reserv["quantity"], "reservation_date": dateString})
		menu.append({ "item" : i.name, "price": i.price, "itemID": int(i.mealID)-1, "meal": i.meal, "date":i.date, "url" : i.image, "reservations":reservs})
	
	response["Menus"] = menu
	return json.dumps(response)


@app.route('/getMenus', methods=['POST'])
def getMenus():

	data =  request.get_data()
	data = json.loads(data)

	dateString = data["date"]

	data["date"] = int(datetime.datetime.strptime(data["date"], '%d/%m/%Y').strftime("%s"))
	menus = db.session.query( Meal.name, Meal.price, Meal.mealID, Meal.meal, Meal.date, Meal.image, Menu.restaurantID).select_from(Meal).join(Menu).join(Restaurant).filter(Restaurant.restaurantID == int(data["restaurantID"])).filter(Meal.date == data["date"]).all()	

	response = {}
	menu = []
	for item in menus:
		menu.append({ "item" : item.name, "price": item.price, "itemID": item.mealID, "meal": item.meal, "date":dateString, "url": item.image})

	response["Menus"] = menu
	return json.dumps(response)


@app.route('/addRestaurant', methods=['POST'])
def addRestaurant():
	#recebe dados da manager app
	data =  request.get_data()
	data = json.loads(data)

	#Token check
	response = json.dumps({"token": data["token"]})	
	url = "http://idp.moreirahelder.com/api/getuser"            #URL DO HELDER
	headers = {'Content-Type': 'application/json'}				#content type
	r = requests.post(url, data=response, headers=headers) 		#efetua o request
	response = json.loads(r.text)
	
	if response["result"] == "error":
		print "invalid token"
		return json.dumps({"200" : "INVALID TOKEN"})

	rest = Restaurant(data['name'], data['localization'], response["username"])
	db.session.add(rest)
	db.session.commit()
	return json.dumps({"200" : "RESTAURANT ADDED"})

@app.route('/localization/<path:path>/<meal>/<date>', methods=['GET']) 
@app.route('/localization/<path:path>/<meal>', methods=['GET'])
@app.route('/localization/<path:path>', methods=['GET'])
def Localidade(path, meal=None, date=None):

	if request.method == 'GET':
		if meal and date:
			return getLocalidade(path, meal, date)
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
		headers = {'Content-Type': 'application/json'}						#content type
		r = requests.post(url, data=data, headers=headers) 	#efetua o request
		return json.dumps({"200" : "OK"})


@app.route('/doreservation', methods=['POST'])
def doreservation():

	#recebe
	# {
 	#    	"restaurantID":1,
 	#    	"itemID":1,
 	#    	"quantity": "1",
 	#    	"date": "27/11/2015:18:00",
 	#    	"token":"joxNDQ4NTU3MjY0fQ.eyJpZCI6OX0.7KceZlUzkvRpOg-eQE23hj9IButnULTnQ07wVHr4H8Q"
	# }

	print "doreservation"
	#recebe dados da reservation app do user
	data = request.get_data()
	data = json.loads(data)

	#Token check
	response = json.dumps({"token": data["token"]})
	url = "http://idp.moreirahelder.com/api/getuser"            								#URL DO HELDER
	headers = {'Content-Type': 'application/json'}												#content type
	r = requests.post(url, data=response, headers=headers) 										#efetua o request
	response = json.loads(r.text)

	if response["result"] == "error":
		print "invalid token"
		return json.dumps({"200" : "INVALID TOKEN"})
	else:
		data["username"] = response['username']
		time = int(datetime.datetime.strptime(data['date'], '%d/%m/%Y:%H:%M').strftime("%s"))
		data= json.dumps({"username": response["username"], "itemID":int(data["itemID"])-1,"quantity":int(data["quantity"]),"timestamp":int(time), "clientID": int(response["user_id"])})
		response = json.loads(data)
		response = json.dumps(response)

		#Enviar dados para REST do manel
		url = "http://ogaviao.ddns.net:80/doreservation"            	    #URL DO MANEL
		headers = {'Content-Type': 'application/json'}						#content type
		r = requests.post(url, data=response, headers=headers) 	    	#efetua o request

		response = json.loads(r.text)
		if response == "200 Invalid stock":
			return json.dumps({"200" : "INVALID STOCK"})
		print response
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
	requestID = str(data['requestid'])

	#verificar 
	sms = sms.split('#')

	if sms[2] == "city":
		print "na city"

		def proc1(localidade, requestID, meal=None, date=None):
			print "inside thread 1"
			response = ""

			if meal and date:
				print date
				data = getLocalidade(localidade, meal,date)
			if meal and not date:
				data = getLocalidade(localidade, meal,None)
				print data
			if not meal and not date:
				data = getLocalidade(localidade, None, None)

			data = json.loads(data)
			print data

			for rest in data['Restaurants']:
				response += "RESTAURANT: \"" + rest['Name'] + "\""
				for menu in rest['Menu']:
					response += " MENU: " + menu['item'] + " PRICE: " +  str(menu['price']) + " MEAL: " + str(menu['meal']) + " DATE: " + datetime.datetime.fromtimestamp(int(menu['date'])).strftime('%d-%m-%Y')
				response += "\n"

			response = json.dumps({"body" : response , "status": 200})
			url = "http://es2015sms.heldermoreira.pt/SMSgwServices/smsmessaging/outbound/"+ requestID +"/response/"    			
			headers = {'Content-Type': 'application/json'}								
			r = requests.post(url, data=response, headers=headers)
			print "end thread 1"
			return json.dumps({"200" : "OK"})

		if len(sms) == 5:
			t = Process(target=proc1, args=(sms[3], requestID, sms[4], None))
		elif len(sms) == 6:
			t = Process(target=proc1, args=(sms[3], requestID, sms[4], sms[5]))
		else:
			t = Process(target=proc1, args=(sms[3], requestID, None, None))

		t.start()
		return json.dumps({"200" : "OK"})

	elif sms[2] == 'add':
		print "add"
		#{
		#"body":"#1tapmeal#add#menu#peixe#10#20#dinner#27-11-2015#carne#12#35#lunch#27-11-2015",
		#"senderAddress":"111111111",
		#"requestid":50
		#}

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
				data["menu"].append({"name": sms[i],"price": int(sms[i+1]), "quantity":int(sms[i+2]), "meal":sms[i+3], "url" : None, "date": int(datetime.datetime.strptime(sms[i+4], '%d-%m-%Y').strftime("%s"))})
				i= i+5

			rest = Restaurant.query.filter_by(managerusername=username).first()
			data["info"][0]["providerID"] = int(rest.restaurantID)

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

	elif sms[2] == 'list':
		def proc4(number, requestID, date=None):
			print "inside thread 4"

			response = json.dumps({"phone":number})
			url = "http://idp.moreirahelder.com/api/getuser"            			#URL DO HELDER
			headers = {'Content-Type': 'application/json'}							#content type
			r = requests.post(url, data=response, headers=headers) 					#efetua o request
			response = json.loads(r.text)

			if response['result'] == "error":
				SMSresponse = json.dumps({"body" : "Number not registred!" , "status": 200})
				url = "http://es2015sms.heldermoreira.pt/SMSgwServices/smsmessaging/outbound/"+ requestID +"/response/"
				headers = {'Content-Type': 'application/json'}
				r = requests.post(url, data=SMSresponse, headers=headers)
				return json.dumps({"200" : "PHONE NUMBER NOT REGISTED"})

			username = response['username']



			if date:
				info = Restaurant.query.filter(Restaurant.managerusername ==username).first()
				if info.restaurantID == None:
					print "MANAGER NOT FOUND"
					SMSresponse = json.dumps({"body" : "Manager not found" , "status": 200})
					url = "http://es2015sms.heldermoreira.pt/SMSgwServices/smsmessaging/outbound/"+ requestID +"/response/"  
					headers = {'Content-Type': 'application/json'}
					r = requests.post(url, data=SMSresponse, headers=headers) 	
					return json.dumps({"200" : "MANAGER NOT FOUND"})


				response = json.dumps({"restaurantID":info.restaurantID,"date":sms[4]})
				url = "http://46.101.14.39/getReservationsByDate" 							#URL DO MANEL
				headers = {'Content-Type': 'application/json'}								#content type
				r = requests.post(url, data=response, headers=headers) 						#efetua o request
				
				data = json.loads(r.text)
				response = ""
				for item in data["Menus"]:
					response += "Meal: " + item["item"]
					for resev in item["reservations"]:
						response += " User: " + resev["username"] + " Quantity: " + str(resev["reserved_quantity"])
					response += "\n" 

				if response == "":
					response = "No reservations avaiable"

				SMSresponse = json.dumps({"body" : response , "status": 200})
				url = "http://es2015sms.heldermoreira.pt/SMSgwServices/smsmessaging/outbound/"+ requestID +"/response/"
				headers = {'Content-Type': 'application/json'}																			
				r = requests.post(url, data=SMSresponse, headers=headers)
				print "end thread 4" 																		
				return json.dumps({"200" : "OK"})	



			else:
				print "no date"
				info = Restaurant.query.filter(Restaurant.managerusername == username).first()
				if info.restaurantID == None:
					print "MANAGER NOT FOUND"
					SMSresponse = json.dumps({"body" : "Manager not found" , "status": 200})
					url = "http://es2015sms.heldermoreira.pt/SMSgwServices/smsmessaging/outbound/"+ requestID +"/response/"  
					headers = {'Content-Type': 'application/json'}
					r = requests.post(url, data=SMSresponse, headers=headers) 	
					return json.dumps({"200" : "MANAGER NOT FOUND"})
					

				url = "http://46.101.14.39/getReservations/" + str(info.restaurantID)
				r = requests.get(url)

				menus = json.loads(r.text)
				response = ""
				for item in menus["Menus"]:
					response += "Meal: " + item["item"] + " reserved: " + str(item["reserved"]) + "\n"


				if response == "":
					response = "No reservations avaiable"
				SMSresponse = json.dumps({"body" : response , "status": 200})
				url = "http://es2015sms.heldermoreira.pt/SMSgwServices/smsmessaging/outbound/"+ requestID +"/response/"
				headers = {'Content-Type': 'application/json'}																			
				r = requests.post(url, data=SMSresponse, headers=headers)
				print "end thread 4" 																		
				return json.dumps({"200" : "OK"})	
		

		if len(sms) > 4:
			t = Process(target=proc4, args=(number, requestID, sms[4]))

		else:
			t = Process(target=proc4, args=(number, requestID, None))


		t.start()
		return json.dumps({"200" : "OK"})
	
	elif sms[2] == 'help':
		def proc5(number, requestID):
			print "inside thread 5"
			help = "To get avaiable restaurants and menus type: #1tapmeal#city#<CITYNAME>\n \
					To add a meal to your menu type: #1tapmeal#add#menu#<MEALNAME>#<PRICE>#<QUANTITY>#<MEALTYPE>#<DATE DD/MM/YYYY> \n \
					To make a reservation type: #1tapmeal#reservation#<CITY>#<RESTAURANT>#<MEALNAME>#<QUANTITY>#<DATE DD/MM/YYYY:HH:MM> \n \
					To list all valid reservations type: #1tapmeal#list \
					To list all valid reservations for a certain day type: #1tapmeal#list#date#<DATE DD/MM/YYYY> "

			SMSresponse = json.dumps({"body" : help , "status": 200})
			url = "http://es2015sms.heldermoreira.pt/SMSgwServices/smsmessaging/outbound/"+ requestID +"/response/"
			headers = {'Content-Type': 'application/json'}																			
			r = requests.post(url, data=SMSresponse, headers=headers)
			print "end thread 5" 																		
			return json.dumps({"200" : "OK"})		


		t = Process(target=proc5, args=(number, requestID))
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
    coordenates = request.args.get('coordenates')
    print coordenates
    username = session['username']

    if name and localization and username and coordenates:
    	rest = Restaurant(name, localization, username, coordenates)
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

	currentTime = int(datetime.datetime.now().strftime("%s")) -24*60*60
	city = city.lower()
	restaurants = Restaurant.query.filter_by(localization=city).all()
	menus = db.session.query( Meal.name, Meal.price, Meal.mealID, Meal.meal, Meal.date, Meal.image, Menu.restaurantID).select_from(Meal).join(Menu).join(Restaurant).filter(Meal.date>currentTime).all()	
	response = json.loads('{"Restaurants":  [ ]}')


	if date:
		print date
		date = int(datetime.datetime.strptime(date, '%d-%m-%Y').strftime("%s"))
		print "depois da date"
		if meal:
			print "date and meal"
			if meal == "lunch":
				for rest in restaurants:
					menu = []
					for item in menus:
						if rest.restaurantID == item.restaurantID and item.meal == "lunch" and item.date == int(date):
							dateString = datetime.datetime.fromtimestamp(int(item.date)).strftime('%d/%m/%Y %H:%M')
							menu.append({ "item" : item.name, "price": item.price, "itemID": item.mealID, "meal": item.meal, "date":dateString, "url":item.image})
					response["Restaurants"].append({"Name" : rest.restaurantname, "ProviderID": rest.restaurantID, "classification" :rest.classification, "coordinates": rest.coordenates, "Menu": menu})
				return json.dumps(response)

			elif meal == "dinner":
				for rest in restaurants:
					menu = []
					for item in menus:
						if rest.restaurantID == item.restaurantID and item.meal == "dinner"  and item.date == int(date):
							dateString = datetime.datetime.fromtimestamp(int(item.date)).strftime('%d/%m/%Y %H:%M')
							menu.append({ "item" : item.name, "price": item.price, "itemID": item.mealID, "meal": item.meal, "date":dateString, "url":item.image})
					response["Restaurants"].append({"Name" : rest.restaurantname, "ProviderID": rest.restaurantID,"classification" :rest.classification,"coordinates": rest.coordenates,"Menu": menu})
				return json.dumps(response)

			else:
				return json.dumps({"200":"INVALID MEAL OPTION"})
	else:
		if meal:
			print "no date but meal"
			if meal == "Lunch":
				for rest in restaurants:
					menu = []
					for item in menus:
						if rest.restaurantID == item.restaurantID and item.meal == "Lunch":
							dateString = datetime.datetime.fromtimestamp(int(item.date)).strftime('%d/%m/%Y %H:%M')
							menu.append({ "item" : item.name, "price": item.price, "itemID": item.mealID, "meal": item.meal, "date":dateString, "url":item.image})
					response["Restaurants"].append({"Name" : rest.restaurantname, "ProviderID": rest.restaurantID,"classification" :rest.classification,"coordinates": rest.coordenates,"Menu": menu})
				return json.dumps(response)

			elif meal == "Dinner":
				for rest in restaurants:
					menu = []
					for item in menus:
						if rest.restaurantID == item.restaurantID and item.meal == "Dinner":
							dateString = datetime.datetime.fromtimestamp(int(item.date)).strftime('%d/%m/%Y %H:%M')
							menu.append({ "item" : item.name, "price": item.price, "itemID": item.mealID, "meal": item.meal, "date":dateString, "url":item.image})
					response["Restaurants"].append({"Name" : rest.restaurantname, "ProviderID": rest.restaurantID,"classification" :rest.classification,"coordinates": rest.coordenates,"Menu": menu})
				return json.dumps(response)

			else:
				return json.dumps({"200":"INVALID MEAL OPTION"})
		else:
			print "localization"
			for rest in restaurants:
				menu = []
				for item in menus:
					if rest.restaurantID == item.restaurantID:
						dateString = datetime.datetime.fromtimestamp(int(item.date)).strftime('%d/%m/%Y %H:%M')
						menu.append({ "item" : item.name, "price": item.price, "itemID": item.mealID, "meal": item.meal, "date":dateString, "url":item.image})
				response["Restaurants"].append({"Name" : rest.restaurantname, "ProviderID": rest.restaurantID,"classification" :rest.classification,"coordinates": rest.coordenates,"Menu": menu})
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
			if  int(item['date']) < (int(datetime.datetime.now().strftime("%s")) - 24*60*60):
				print "Menu expiration date invalid"
				return None
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

	if  int(timestamp) < (int(datetime.datetime.now().strftime("%s")) - 24*60*60):
		print "Menu expiration date invalid"
		return None

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

