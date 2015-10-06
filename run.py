import sqlite3
import sys
import json
from flask import Flask, request

app = Flask(__name__)

@app.route('/localization/<path:path>', methods=['GET'])
def Localidade(path):
	if request.method == 'GET':
		restaurants = ConnectDB('SELECT RestaurantID,Name From Restaurant where Localization=\'' + path + '\';',2)
		menus = ConnectDB('SELECT * from Meal LEFT OUTER JOIN Menu on Meal.MealID=Menu.MealID', 2)

		resposta = json.loads('{"Restaurants":  [ ]}')
		for rest in restaurants:
			menu = []
			for item in menus:
				if rest[0] == item[3]:
					menu.append({ "item" : item[0], "price": item[2]})
			print menu
			resposta["Restaurants"].append({"Name" : rest[1], "ProviderID": rest[0],"Menu": menu})	
		return json.dumps(resposta)
	else:
		return "Invalid request"


@app.route('/replenishstock', methods=['GET'])
def Reservations():
	return "FODASSE SUIL CARALHO P*QUE PUTA DE CHATO"






def ConnectDB(query, op):
	try:
		print "Connecting to bd"
		con = sqlite3.connect('database.db')
		cur = con.cursor()
		cur.execute(query)
		if op == 1:
			data = cur.fetchone()
		else:
			data = cur.fetchall()
	except sqlite3.Error, e:
		print "Error on the database! "
		sys.exit(1)
	if con:
		con.close()
	return data



if __name__ == '__main__':
    app.run(host='0.0.0.0',port=80)

