import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

db = SQL("sqlite:///finance.db")

rows = db.execute("SELECT * FROM users WHERE id = :uid", uid='4')
print(rows[0]['cash'])





found = False
        for row in book:
            if row['stock'] == request.form.get("symbol"):
                found = True
                break
        if found == False:
            db.execute("INSERT INTO book (username, stock, quantity) VALUES (?,?,?)", rows[0]['username'], quote['symbol'], int(request.form.get("shares")))
        else:
            db.execute("SELECT * FROM book WHERE username = :uname AND stock = :stck" , uname=rows[0]['username'], stck=request.form.get("symbol"))
            
            db.execute("UPDATE book SET  = :newcash WHERE id = :uid", newcash=(rows[0]['cash'] - total), uid=session["user_id"])