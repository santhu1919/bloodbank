from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
import re

app = Flask(__name__)
app.secret_key = "bloodbank_secret_key"

# ================== DATABASE CONNECTION ==================
client = MongoClient("mongodb://localhost:27017/")
db = client["bloodbank"]

donors = db["donors"]
requests_collection = db["requests"]
stock = db["stock"]

# ================== LOGIN PAGE ==================
@app.route("/")
def home():
    return render_template("login.html")

# ================== LOGIN FUNCTION ==================
@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"].strip()

    if username:
        session["user"] = username
        return redirect(url_for("dashboard"))
    else:
        return render_template("login.html", error="Please enter your name")

# ================== DASHBOARD ==================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("home"))
    return render_template("index.html", user=session["user"])

# ================== LOGOUT ==================
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))

# ================== DONOR PAGE ==================
@app.route("/donor")
def donor_page():
    if "user" not in session:
        return redirect(url_for("home"))
    return render_template("donor.html")

# ================== REQUEST PAGE ==================
@app.route("/request")
def request_page():
    if "user" not in session:
        return redirect(url_for("home"))
    return render_template("request.html")

# ================== STOCK PAGE ==================
@app.route("/stock")
def view_stock():
    if "user" not in session:
        return redirect(url_for("home"))
    all_stock = stock.find()
    return render_template("stock.html", stock=all_stock)

# ================== ADD DONOR ==================
@app.route("/add_donor", methods=["POST"])
def add_donor():
    if "user" not in session:
        return redirect(url_for("home"))

    name = request.form["name"].strip()
    age = request.form["age"]
    blood = request.form["blood"].strip().upper()

    pattern = r'^(A|B|AB|O)[+-]$'
    if not re.match(pattern, blood):
        return "Invalid Blood Group! Only A+, A-, B+, B-, AB+, AB-, O+, O- allowed <br><a href='/donor'>Go Back</a>"

    if not age.isdigit() or int(age) < 18 or int(age) > 65:
        return "Invalid Age! Age must be between 18 and 65 <br><a href='/donor'>Go Back</a>"

    donors.insert_one({
        "name": name,
        "age": int(age),
        "blood_group": blood
    })

    stock.update_one(
        {"blood_group": blood},
        {"$inc": {"units": 1}},
        upsert=True
    )

    return "Donor Added & Stock Increased <br><a href='/dashboard'>Go Dashboard</a>"

# ================== ADD REQUEST ==================
@app.route("/add_request", methods=["POST"])
def add_request():
    if "user" not in session:
        return redirect(url_for("home"))

    patient = request.form["patient"].strip()
    blood = request.form["blood"].strip().upper()
    units = request.form["units"]

    pattern = r'^(A|B|AB|O)[+-]$'
    if not re.match(pattern, blood):
        return "Invalid Blood Group! <br><a href='/request'>Go Back</a>"

    if not units.isdigit() or int(units) <= 0:
        return "Invalid Units! <br><a href='/request'>Go Back</a>"

    units = int(units)

    blood_data = stock.find_one({"blood_group": blood})

    if blood_data and blood_data.get("units", 0) >= units:
        requests_collection.insert_one({
            "patient_name": patient,
            "blood_group": blood,
            "units": units
        })

        stock.update_one(
            {"blood_group": blood},
            {"$inc": {"units": -units}}
        )

        return "Blood Issued Successfully <br><a href='/dashboard'>Go Dashboard</a>"
    else:
        return "Not Enough Stock <br><a href='/dashboard'>Go Dashboard</a>"

if __name__ == "__main__":
    app.run(debug=True)
