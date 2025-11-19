from flask import Flask, render_template, redirect, url_for
from db import get_db

app = Flask(__name__)

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/login")
def login():
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