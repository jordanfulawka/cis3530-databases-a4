from flask import Flask, render_template, redirect, url_for, request, flash
from db import get_db

app = Flask(__name__)

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        if not username or not password:
            flash("Username and password cannot be empty.")
            return render_template("login.html")
        else:
            return redirect(url_for("employees"))
        
    return render_template("login.html")

@app.route("/employees")
def employees():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT Fname, Minit, Lname, SSN, Dno, Address, Salary FROM Employee 
            """)
            employees_list = cur.fetchall()
    return render_template("employees.html", employees=employees_list)

if __name__ == "__main__":
    app.run(debug=True)