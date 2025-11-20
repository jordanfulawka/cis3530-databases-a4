from flask import Flask, render_template, redirect, url_for, request, flash, session, g
from db import get_db, close_db
from functools import wraps
from werkzeug.security import check_password_hash
import psycopg

app = Flask(__name__)
app.secret_key = "randomkey" # change later
app.teardown_appcontext(close_db)

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.before_request
def load_user():
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
        return

    conn = get_db()
    #row_factory line just ensures that cur.fetchone returns a dictionary, not a tuple. important for role_required function
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute("SELECT id, username, role FROM app_user WHERE id = %s", (user_id,))
        g.user = cur.fetchone()

def login_required(view):
    @wraps(view)
    def wrapped(**kwargs):
        if g.get("user") is None:
            return redirect(url_for("login"))
        return view(**kwargs)
    return wrapped

def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if g.user is None:
                return redirect(url_for("login"))
            if g.user.get("role") != role:
                flash("No permission")
                return redirect(url_for("login"))
            return view(*args, **kwargs)
        return wrapped_view
    return decorator

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        return redirect(url_for("employees"))
        #username = request.form["username"].strip()
        #password = request.form["password"].strip()

        #conn = get_db()
     #   with conn.cursor() as cur:
         #   cur.execute("SELECT id, password_hash FROM app_user WHERE username = %s", (username,))
         #   row = cur.fetchone()
           # print(row)
#
       # if row is None:
          #  flash('Invalid username of password')
          #  return render_template("login.html")
        
       # user_id, password_hash = row
        
       # if not check_password_hash(password_hash, password):
          #  flash('Invalid username or password')
           # print('invalid!')
          #  return render_template("login.html")

        #session.clear()
        #session["user_id"] = user_id

        

    return render_template("login.html")

@app.route("/employees")
#@login_required
def employees():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT E.Fname || ' ' || E.Minit || '. ' || E.Lname AS full_name,D.Dname AS department_name,COUNT(DP.Dependent_name) AS num_dependents,COUNT(DISTINCT W.Pno) AS num_projects,COALESCE(SUM(W.Hours), 0) AS total_hours
                            FROM Employee E
                            JOIN Department D ON E.Dno = D.Dnumber
                            LEFT JOIN Dependent DP ON E.Ssn = DP.Essn
                            LEFT JOIN Works_On W ON E.Ssn = W.Essn
                            GROUP BY E.Ssn, D.Dname""")
            employees_list = cur.fetchall()
    return render_template("employees.html", employees=employees_list)

@app.route("/projects")
def projects():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT P.Pname,D.Dname AS owning_department,COUNT(DISTINCT W.Essn) AS headcount,COALESCE(SUM(W.Hours), 0) AS total_assigned_hours
                            FROM Project P
                            JOIN Department D ON P.Dnum = D.Dnumber
                            LEFT JOIN Works_On W ON P.Pnumber = W.Pno
                            GROUP BY P.Pnumber, D.Dname""")
            projects_list = cur.fetchall()
    return render_template("projects.html", projects=projects_list)

@app.route("/managers")
def managers():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT D.Dname,D.Dnumber,(M.Fname || ' ' || M.Minit || '. ' || M.Lname) AS manager_full_name,COUNT(DISTINCT E.Ssn) AS employee_count, COALESCE(SUM(W.Hours), 0) AS department_total_hours
                            FROM Department D
                            LEFT JOIN Employee M ON D.Mgr_ssn = M.Ssn
                            LEFT JOIN Employee E ON E.Dno = D.Dnumber
                            LEFT JOIN Works_On W ON E.Ssn = W.Essn
                            GROUP BY D.Dname, D.Dnumber, manager_full_name""")

            managers_list = cur.fetchall()
    return render_template("managers.html", managers=managers_list)



if __name__ == "__main__":
    app.run(debug=True)