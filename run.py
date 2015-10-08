from flask import Flask, request
from flask.ext.sqlalchemy import SQLAlchemy
import sqlite3
import sys
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)


class Restaurant(db.Model):
	__tablename__ = "restaurant"
	restaurantID = db.Column(db.Integer, primary_key=True)
	restaurantname = db.Column(db.String(50))
	localization = db.Column(db.String(50))
	managerusername = db.Column(db.String(50), unique=True)
	classification = db.Column(db.Integer)

	def __init__(self, restaurantname, localization, managerusername, classification):
		self.restaurantname = restaurantname
		self.localization = localization
		self.managerusername = managerusername
		self.classification = classification

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
		
		restaurants = Restaurant.query.filter_by(localization=path).all()
		menus = db.session.query(Meal.name, Meal.price, Menu.restaurantID).select_from(Meal).join(Menu).all()
		response = json.loads('{"Restaurants":  [ ]}')
		
		for rest in restaurants:
			menu = []
			for item in menus:
				if rest.restaurantID == item.restaurantID:
					menu.append({ "item" : item.name, "price": item.price})
			response["Restaurants"].append({"Name" : rest.restaurantname, "ProviderID": rest.restaurantID,"Menu": menu})
		return json.dumps(response)

	else:
		return "Invalid request"


@app.route('/replenishstock', methods=['POST'])
def Reservations():


	#RECEBE INFO DO MANAGER APP
	data =  request.get_data()
	data = json.loads(data)

	username = data['username']
	rest = Restaurant.query.filter_by(managerusername=username).first()


	if(rest.restaurantID == None ):
		return json.dumps({"404" : "Manager username not found"})
	else:
		menu = data['menu']
		mealid = 4
		for item in menu:
			meal = Meal(item['name'], item['price'])
			mealID = db.session.query(Meal).count()
			menu = Menu(rest.restaurantID, mealID)
			db.session.add(meal)
			db.session.add(menu)
			db.session.commit()
	return json.dumps({"200" : "OK"})



if __name__ == '__main__':
	db.create_all()
	#insert
	r1 = Restaurant('restaurant 1', 'Aveiro', 'dave1', 1)
	r2 = Restaurant('restaurant 2', 'Aveiro', 'dave2', 1)
	r3 = Restaurant('restaurant 3', 'Aveiro', 'dave3', 1)
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


	app.run(host='0.0.0.0',port=80)


