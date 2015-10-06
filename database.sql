PRAGMA encoding="UTF-8";
PRAGMA foreign_keys=ON;

BEGIN TRANSACTION;
CREATE TABLE Restaurant(
RestaurantID 	        INTEGER PRIMARY KEY,
Name		  	    	Varchar(50),
Localization 	        Varchar(50),
Classification			INTEGER);



CREATE TABLE Meal(
Name 		        VARCHAR(50),
MealID				INTEGER PRIMARY KEY,
Price 		        REAL );

CREATE TABLE Menu(
RestaurantID 		        INTEGER,
MealID						INTEGER,
PRIMARY KEY (RestaurantID, MealID) );




INSERT INTO Restaurant (RestaurantID,Name,Localization,Classification ) VALUES (1,'restaurante 1','Aveiro',1);
INSERT INTO Restaurant (RestaurantID,Name,Localization,Classification ) VALUES (2,'restaurante 2','Aveiro',2);
INSERT INTO Restaurant (RestaurantID,Name,Localization,Classification ) VALUES (3,'restaurante 3','Lisboa',3);
INSERT INTO Restaurant (RestaurantID,Name,Localization,Classification ) VALUES (4,'restaurante 4','Porto',4);

INSERT INTO Meal (Name,MealID,Price )   VALUES   ('Arroz com frango',1,3);
INSERT INTO Meal (Name,MealID,Price )   VALUES   ('Atum em lata',2,3);
INSERT INTO Menu (RestaurantID,MealID ) VALUES (1,1);
INSERT INTO Menu (RestaurantID,MealID ) VALUES (1,2);


COMMIT;



