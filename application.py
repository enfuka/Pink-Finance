import os
import re
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":

        qnt = request.form.get("count")

        stock = request.form.get("button")

        if not stock or lookup(stock) == None:
            return apology("Invalid Symbol")

        elif not qnt or int(qnt) < 1:
            return apology("Invalid number of shares")

        rows = db.execute("SELECT * FROM users WHERE id = :uid", uid=session["user_id"])
        quote = lookup(stock)


        total = float(quote['price']) * int(qnt)

        symbol = stock
        sym = symbol.upper()

        book = db.execute("SELECT * FROM book WHERE username = :uname AND stock = :stck" , uname=rows[0]['username'], stck=sym)
        if not book:
            return apology("share not owned")
        elif int(book[0]['quantity']) < int(qnt):
            return apology("not enough shares")
        else:
            decrmnt = int(book[0]['quantity']) - int(qnt)
            db.execute("UPDATE book SET quantity = :newquantity WHERE username = :uname AND stock = :stck" , uname=rows[0]['username'], stck=sym, newquantity=decrmnt)

        db.execute("UPDATE users SET cash = :newcash WHERE id = :uid", newcash=(rows[0]['cash'] + total), uid=session["user_id"])

        db.execute("INSERT INTO log (username, action, stock, quantity, price, total) VALUES (?,?,?,?,?,?)", rows[0]['username'], "sell", quote['symbol'], qnt, quote['price'], total)

        return render_template("sold.html",book=book, name=quote['name'], total=total, number=qnt)


    else:
        """Show portfolio of stocks"""

        book = db.execute("SELECT stock, quantity FROM book WHERE username = :uname", uname=session["username"])
        grand = 0
        for row in book:
            quote = lookup(row['stock'])
            row['current'] = quote['price']
            total = float(quote['price']) * int(row['quantity'])
            row['total'] = total
            row['name'] = quote['name']
            grand += total
            row['current'] = round(row['current'], 2)
            row['total'] = round(row['total'], 2)

        book = [row for row in book if not int(row['quantity']) == 0]

        getcash = db.execute("SELECT cash FROM users WHERE username = :uname", uname=session["username"])
        cash = round(getcash[0]['cash'],2)
        grand += cash
        return render_template("index.html", book=book, cash=cash, grand=round(grand,2))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":

        if not request.form.get("symbol") or lookup(request.form.get("symbol")) == None:
            return apology("Invalid Symbol")

        elif not request.form.get("shares") or int(request.form.get("shares")) < 1:
            return apology("Invalid number of shares")

        rows = db.execute("SELECT * FROM users WHERE id = :uid", uid=session["user_id"])
        quote = lookup(request.form.get("symbol"))

        symbol = request.form.get("symbol")
        sym = symbol.upper()

        total = float(quote['price']) * int(request.form.get("shares"))

        if rows[0]['cash'] < total:
            return apology("not enough cash")

        db.execute("UPDATE users SET cash = :newcash WHERE id = :uid", newcash=(rows[0]['cash'] - total), uid=session["user_id"])


        book = db.execute("SELECT * FROM book WHERE username = :uname AND stock = :stck" , uname=rows[0]['username'], stck=sym)
        if not book:
            db.execute("INSERT INTO book (username, stock, quantity) VALUES (?,?,?)", rows[0]['username'], quote['symbol'], int(request.form.get("shares")))
        else:
            incrmnt = int(book[0]['quantity']) + int(request.form.get("shares"))
            db.execute("UPDATE book SET quantity = :newquantity WHERE username = :uname AND stock = :stck" , uname=rows[0]['username'], stck=sym, newquantity=incrmnt)

        db.execute("INSERT INTO log (username, action, stock, quantity, price, total) VALUES (?,?,?,?,?,?)", rows[0]['username'], "buy", quote['symbol'], int(request.form.get("shares")), quote['price'], total)

        return render_template("bought.html", name=quote['name'], total=round(total, 2), number=request.form.get("shares"),)

    else:
        return render_template("buy.html")



@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    log = db.execute("SELECT * FROM log WHERE username = :uname", uname=session["username"])
    for row in log:
        row['price'] = round(row['price'], 2)
        row['total'] = round(row['total'], 2)

    return render_template("history.html", log=log)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        session["username"] = rows[0]["username"]
        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        if lookup(request.form.get("symbol")) == None:
            return apology("invalid symbol")
        quoted = lookup(request.form.get("symbol"))
        return render_template("quoted.html", quoted=quoted)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            return apology("must provide a username")

        elif not password:
            return apology("must provide a password")

        elif not confirmation or confirmation != password:
            return apology("passwords do not match")

        elif not len(password) > 5 or not re.search('[a-zA-Z]', password) or not re.search('[0-9]', password) :
            return apology("bad password")


        rows = db.execute("SELECT username FROM users WHERE username = :uname", uname=username)
        if bool(rows):
            return apology("username already exists")

        hashed = generate_password_hash(password)
        db.execute("INSERT INTO users (username, hash) VALUES (:uname, :pword)", uname=username, pword=hashed)

        return redirect("/login")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":

        if not request.form.get("symbol") or lookup(request.form.get("symbol")) == None:
            return apology("Invalid Symbol")

        elif not request.form.get("shares") or int(request.form.get("shares")) < 1:
            return apology("Invalid number of shares")

        rows = db.execute("SELECT * FROM users WHERE id = :uid", uid=session["user_id"])
        quote = lookup(request.form.get("symbol"))


        total = float(quote['price']) * int(request.form.get("shares"))

        symbol = request.form.get("symbol")
        sym = symbol.upper()

        book = db.execute("SELECT * FROM book WHERE username = :uname AND stock = :stck" , uname=rows[0]['username'], stck=sym)
        if not book:
            return apology("share not owned")
        elif int(book[0]['quantity']) < int(request.form.get("shares")):
            return apology("not enough shares")
        else:
            decrmnt = int(book[0]['quantity']) - int(request.form.get("shares"))
            db.execute("UPDATE book SET quantity = :newquantity WHERE username = :uname AND stock = :stck" , uname=rows[0]['username'], stck=sym, newquantity=decrmnt)

        db.execute("UPDATE users SET cash = :newcash WHERE id = :uid", newcash=(rows[0]['cash'] + total), uid=session["user_id"])

        db.execute("INSERT INTO log (username, action, stock, quantity, price, total) VALUES (?,?,?,?,?,?)", rows[0]['username'], "sell", quote['symbol'], int(request.form.get("shares")), quote['price'], total)

        return render_template("sold.html",book=book, name=quote['name'], total=total, number=request.form.get("shares"))

    else:
        book = db.execute("SELECT stock, quantity FROM book WHERE username = :uname", uname=session["username"])
        book = [row for row in book if not int(row['quantity']) == 0]
        return render_template("sell.html", book=book)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

@app.route("/account", methods=["GET", "POST"])
@login_required
def passwordChange():
    if request.method == "POST":

        newpassword = request.form.get("newpassword")

        if not newpassword:
            return apology("must provide a new password")

        elif not request.form.get("newconfirmation") or request.form.get("newconfirmation") != newpassword:
            return apology("passwords do not match")

        elif not len(newpassword) > 5 or not re.search('[a-zA-Z]', newpassword) or not re.search('[0-9]', newpassword) :
            return apology("bad password")


        hashed = generate_password_hash(request.form.get("newpassword"))
        db.execute("UPDATE users SET hash = :hashd WHERE id = :uid", hashd=hashed, uid=session["user_id"])

        return render_template("pwordchanged.html")

    else:
        return render_template("account.html")


@app.route("/addcash", methods=["GET", "POST"])
@login_required
def addcash():
    if request.method == "POST":

        if not request.form.get("cash") or not int(request.form.get("cash")) > 0:
            return apology("must provide a valid cash amount")
        getcash = db.execute("SELECT cash FROM users WHERE id = :uid", uid=session["user_id"])
        newcash = getcash[0]['cash'] + float(request.form.get("cash"))
        db.execute("UPDATE users SET cash = :cash WHERE id = :uid", cash=newcash, uid=session["user_id"])

        return render_template("cashadded.html")

    else:
        return render_template("addcash.html")