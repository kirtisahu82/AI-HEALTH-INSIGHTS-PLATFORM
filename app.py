from flask import Flask, render_template, request, jsonify, make_response, redirect, url_for, session, flash,request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime , timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import os , csv , requests
from io import StringIO

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "health_dev_secret_123")

APP_ID = "cc786e86"
APP_KEY = "7d3cbaf6469a5cd56809ea1077d768a8"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, "health.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# Models

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def check_password(self, pw_plain):
        return check_password_hash(self.password_hash, pw_plain)


class WaterIntake(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    intake = db.Column(db.Integer, default=0)   # ml of water consumed



class Meal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    meal_type = db.Column(db.String(20), nullable=False)   # breakfast, lunch...
    description = db.Column(db.String(300))
    calories = db.Column(db.Integer, nullable=False)


class CalorieLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    calories = db.Column(db.Integer, nullable=False)


class StepLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    steps = db.Column(db.Integer, nullable=False)


# Routes

@app.before_request
def create_tables():
    db.create_all()


@app.route("/")
def root():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        age = request.form.get("age", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")


        if not name or not email or not password:
            flash("Please fill all required fields.", "danger")
            return render_template("signup.html")


        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("Email already registered. Please login.", "warning")
            return redirect(url_for("login"))

        try:
            age_val = int(age) if age else None
        except ValueError:
            age_val = None

        user = User(
            name=name,
            age=age_val,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()

        flash("Signup successful — please login.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["user_name"] = user.name
            flash("Login successful — welcome!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password.", "danger")
            return render_template("login.html")

    return render_template("login.html")




@app.route("/home")
def home():
    if "user_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    today = datetime.now().strftime("%Y-%m-%d")


    meals = Meal.query.filter_by(user_id=user_id, date=today).all()
    total_calories = sum(m.calories for m in meals)


    water = WaterIntake.query.filter_by(user_id=user_id, date=today).first()
    water_intake = water.intake if water else 0


    return render_template(
        "home.html",
        total_calories=total_calories,
        meals=meals,
        water_intake=water_intake
    )





@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("login"))

    # You can fetch user-specific data here
    user = User.query.get(session["user_id"])
    return render_template("dashboard.html", username=user.name)


@app.route("/logout")
def logout():
    print("logout triggered!")
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))



@app.route("/bmi", methods=["GET", "POST"])
def bmi():
    if "user_id" not in session:
        flash("Please login to continue.", "warning")
        return redirect(url_for("login"))

    result = None
    status = None

    if request.method == "POST":
        weight = request.form.get("weight")
        height = request.form.get("height")

        if not weight or not height:
            flash("Please enter both fields.", "danger")
            return redirect(url_for("bmi"))

        weight = float(weight)
        height = float(height) / 100

        if height == 0:
            flash("Height cannot be zero.", "danger")
            return redirect(url_for("bmi"))

        bmi_value = round(weight / (height * height), 2)

        if bmi_value < 18.5:
            status = "Underweight"
        elif bmi_value < 24.9:
            status = "Normal"
        elif bmi_value < 29.9:
            status = "Overweight"
        else:
            status = "Obese"

        result = bmi_value

    return render_template("bmi.html", result=result, status=status)




@app.route("/water", methods=["GET", "POST"])
def water():
    if "user_id" not in session:
        flash("Please login to continue.", "warning")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    today = datetime.now().strftime("%Y-%m-%d")

    record = WaterIntake.query.filter_by(user_id=user_id, date=today).first()

    if not record:
        record = WaterIntake(user_id=user_id, date=today, intake=0)
        db.session.add(record)
        db.session.commit()

    if request.method == "POST":
        amount = int(request.form["amount"])
        record.intake += amount
        db.session.commit()
        flash("Water added successfully!", "success")
        return redirect(url_for("water"))

    daily_goal = 3000   # 3 Liters
    percent = (record.intake / daily_goal) * 100
    percent = min(percent, 100)

    return render_template("water.html", intake=record.intake, percent=percent, goal=daily_goal)




@app.route("/meal", methods=["GET", "POST"])
def meal():
    if "user_id" not in session:
        flash("Please login to continue.", "warning")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    today = datetime.now().strftime("%Y-%m-%d")

    if request.method == "POST":
        meal_type = request.form["meal_type"]
        description = request.form.get("description", "")

        # 🔥 API se calories calculate karenge
        url = f"https://api.edamam.com/api/nutrition-details?app_id={APP_ID}&app_key={APP_KEY}"
        headers = {
            "Content-Type": "application/json"
            }
        payload = {
            "title": "Meal",
            "ingr": [description]
            }
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        print(data)

        # ✅ Safe extraction
        try:
            calories = round(data["ingredients"][0]["parsed"][0]["nutrients"]["ENERC_KCAL"]["quantity"])
        except:
            print("API ERROR:", data)
            calories = 0

        meal_entry = Meal(
            user_id=user_id,
            date=today,
            meal_type=meal_type,
            description=description,
            calories=calories
        )

        db.session.add(meal_entry)
        db.session.commit()

        flash("Meal added successfully!", "success")
        return redirect(url_for("meal"))

    meals = Meal.query.filter_by(user_id=user_id, date=today).all()

    total_calories = sum(m.calories for m in meals)

    return render_template("meal.html", meals=meals, total=total_calories)






@app.route("/calories", methods=["GET", "POST"])
def calories():
    if "user_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    today = datetime.now().strftime("%Y-%m-%d")

    if request.method == "POST":
        calories = int(request.form["calories"])
        entry = CalorieLog(user_id=user_id, date=today, calories=calories)
        db.session.add(entry)
        db.session.commit()
        flash("Calories added!", "success")
        return redirect(url_for("calories"))


    logs = CalorieLog.query.filter_by(user_id=user_id, date=today).all()
    total = sum(l.calories for l in logs)


    days_data = []
    for i in range(7):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        cals = CalorieLog.query.filter_by(user_id=user_id, date=d).all()
        days_data.append({
            "date": d,
            "calories": sum(x.calories for x in cals)
        })

    days_data.reverse()

    return render_template("calories.html", logs=logs, total=total, chart_data=days_data)





@app.route("/steps", methods=["GET", "POST"])
def steps():
    if "user_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    today = datetime.now().strftime("%Y-%m-%d")

    if request.method == "POST":
        steps = int(request.form["steps"])
        entry = StepLog(user_id=user_id, date=today, steps=steps)
        db.session.add(entry)
        db.session.commit()
        flash("Steps added successfully!", "success")
        return redirect(url_for("steps"))

    logs = StepLog.query.filter_by(user_id=user_id, date=today).all()
    total_steps = sum(l.steps for l in logs)


    days_data = []
    for i in range(7):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        steps = StepLog.query.filter_by(user_id=user_id, date=d).all()
        days_data.append({
            "date": d,
            "steps": sum(x.steps for x in steps)
        })

    days_data.reverse()

    return render_template("steps.html", logs=logs, total=total_steps, chart_data=days_data)




@app.route("/history", methods=["GET", "POST"])
def history():
    if "user_id" not in session:
        flash("Please login to continue.", "warning")
        return redirect(url_for("login"))

    user_id = session["user_id"]


    start_date = request.args.get("start")
    end_date = request.args.get("end")

    if not start_date and not end_date:

        today = datetime.now().strftime("%Y-%m-%d")
        start_date = end_date = today

    if start_date and not end_date:
        end_date = start_date


    def get_range_dates(s, e):

        d0 = datetime.strptime(s, "%Y-%m-%d")
        d1 = datetime.strptime(e, "%Y-%m-%d")
        days = []
        while d0 <= d1:
            days.append(d0.strftime("%Y-%m-%d"))
            d0 += timedelta(days=1)
        return days

    dates = get_range_dates(start_date, end_date)


    meals = Meal.query.filter(Meal.user_id==user_id, Meal.date.in_(dates)).order_by(Meal.date.desc()).all()
    waters = WaterIntake.query.filter(WaterIntake.user_id==user_id, WaterIntake.date.in_(dates)).order_by(WaterIntake.date.desc()).all()
    cals = CalorieLog.query.filter(CalorieLog.user_id==user_id, CalorieLog.date.in_(dates)).order_by(CalorieLog.date.desc()).all()
    steps = StepLog.query.filter(StepLog.user_id==user_id, StepLog.date.in_(dates)).order_by(StepLog.date.desc()).all()

    summary = {}
    for d in dates:
        summary[d] = {"meals":0, "calories":0, "water":0, "steps":0}

    for m in meals:
        summary[m.date]["meals"] += 1
        summary[m.date]["calories"] += (m.calories or 0)

    for w in waters:
        summary[w.date]["water"] += (w.intake or 0)

    for c in cals:
        summary[c.date]["calories"] += (c.calories or 0)

    for s in steps:
        summary[s.date]["steps"] += (s.steps or 0)


    ordered_days = sorted(summary.keys(), reverse=True)

    return render_template("history.html",
                           ordered_days=ordered_days,
                           summary=summary,
                           meals=meals,
                           waters=waters,
                           cals=cals,
                           steps=steps,
                           start_date=start_date,
                           end_date=end_date)


@app.route("/history/export")
def history_export():
    if "user_id" not in session:
        flash("Please login to continue.", "warning")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    start_date = request.args.get("start")
    end_date = request.args.get("end")

    if not start_date:
        start_date = datetime.now().strftime("%Y-%m-%d")
    if not end_date:
        end_date = start_date

    dates = []
    d0 = datetime.strptime(start_date, "%Y-%m-%d")
    d1 = datetime.strptime(end_date, "%Y-%m-%d")
    while d0 <= d1:
        dates.append(d0.strftime("%Y-%m-%d"))
        d0 += timedelta(days=1)


    rows = []

    meals = Meal.query.filter(Meal.user_id==user_id, Meal.date.in_(dates)).all()
    for m in meals:
        rows.append(["Meal", m.date, m.meal_type, m.description or "", m.calories])

    waters = WaterIntake.query.filter(WaterIntake.user_id==user_id, WaterIntake.date.in_(dates)).all()
    for w in waters:
        rows.append(["Water", w.date, "", "", w.intake])

    cals = CalorieLog.query.filter(CalorieLog.user_id==user_id, CalorieLog.date.in_(dates)).all()
    for c in cals:
        rows.append(["Calories", c.date, "", "", c.calories])

    steps = StepLog.query.filter(StepLog.user_id==user_id, StepLog.date.in_(dates)).all()
    for s in steps:
        rows.append(["Steps", s.date, "", "", s.steps])


    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(["Type", "Date", "Meal Type", "Description", "Value"])
    for r in rows:
        cw.writerow(r)

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=history_{start_date}_to_{end_date}.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route("/chatbot")
def chatbot():
    return render_template("chatbot.html")

if __name__ == "__main__":
    app.run(debug=True,port = 5003)
