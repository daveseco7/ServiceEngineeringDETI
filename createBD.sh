#!/bin/bash
if [ -e "database.db" ]; then
	rm "database.db"
fi
cat database.sql | sqlite3 database.db
