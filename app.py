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
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            flash('You must be logged in to access this page.')
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

def admin_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            flash('Login required')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Invalid permission')
            return redirect(url_for('employees'))
        return view(**kwargs)
    return wrapped_view

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT id, password_hash, role FROM app_user WHERE username = %s", (username,))
            row = cur.fetchone()

        if row is None:
            flash("Invalid username or password")
            return render_template("login.html")
        
        user_id, password_hash, role = row
        
        if not check_password_hash(password_hash, password):
            flash("Invalid username or password")
            print('invalid!')
            return render_template("login.html")

        session.clear()
        session["user_id"] = user_id
        session["role"] = role
        
        return redirect(url_for("employees"))

    return render_template("login.html")

@app.route("/employees")
@login_required
def employees():
    conn = get_db()
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute("""
            SELECT  E.Ssn,
                    E.Fname, 
                    E.Minit, 
                    E.Lname,
                    D.Dname as department_name,
                    COALESCE(COUNT(DP.Dependent_name), 0) as num_dependents,
                    COALESCE(COUNT(DISTINCT W.Pno), 0) as num_projects,
                    COALESCE(SUM(W.Hours), 0) as total_hours
            FROM Employee E
            LEFT JOIN Department D
                ON E.Dno = D.Dnumber
            LEFT JOIN Dependent DP
                ON E.Ssn = DP.Essn
            LEFT JOIN Works_On W
                ON E.Ssn = W.Essn
            GROUP BY
                E.Ssn, E.Fname, E.Minit, E.Lname, D.Dname
            ORDER BY E.Fname, E.Lname;
        """)
        employees_list = cur.fetchall()
    return render_template("employees.html", employees=employees_list)

@app.route("/projects")
@login_required
def projects():
    with get_db() as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("""
                SELECT p.Pname as project_name,
                        d.Dname as department_name,
                        COUNT(DISTINCT W.Essn) as headcount,
                        COALESCE(SUM(W.Hours), 0) as total_hours,
                        p.Pnumber as project_number
                FROM Project p
                JOIN Department d ON p.Dnum = d.Dnumber
                LEFT JOIN Works_On w ON p.Pnumber = w.Pno
                GROUP BY p.Pnumber, p.Pname, d.Dname
            """)
            projects_list = cur.fetchall()

    return render_template("projects.html", projects=projects_list)

@app.route("/project/<int:project_id>", methods=["GET", "POST"])
@login_required
def project_details(project_id):
    conn = get_db()

    if request.method == "POST":
        emp_ssn = request.form.get("employee")
        new_hours = request.form.get("hours")

        if not emp_ssn or not new_hours:
            flash("Employee and hours are required.")
        else:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO Works_On (Essn, Pno, Hours)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (Essn, Pno)
                    DO UPDATE SET Hours = Works_On.Hours + EXCLUDED.Hours;
                """, (emp_ssn, project_id, new_hours))
            conn.commit()
            flash("Assignment updated successfully.")
            return redirect(url_for("project_details", project_id=project_id))

    with conn.cursor() as cur:
        cur.execute("""
            SELECT Pname, Pnumber, Dnum
            FROM Project
            WHERE Pnumber = %s
        """, (project_id,))
        project = cur.fetchone()

        if project is None:
            return "Project not found", 404
        
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                E.Ssn,
                E.Fname,
                E.Minit,
                E.Lname,
                W.Hours
            FROM Works_On W
            JOIN Employee E ON E.Ssn = W.Essn
            WHERE W.Pno = %s
            ORDER BY E.Lname, E.Fname;
        """, (project_id,))
        assigned = cur.fetchall()

    with conn.cursor() as cur:
        cur.execute("""
            SELECT Ssn, Fname, Minit, Lname
            FROM Employee
            ORDER BY Lname, Fname;
        """)
        all_employees = cur.fetchall()

    return render_template(
        "project_details.html",
        project=project,
        assigned=assigned,
        all_employees=all_employees,
    )


@app.route("/employees/add", methods=["GET"])
@admin_required
def add_employee():
    return render_template("employee_add.html")

@app.route("/employees/add", methods=["POST"])
def add_employee_submit():
    conn = get_db()
    ssn = request.form["ssn"]
    fname = request.form["fname"]
    minit = request.form["minit"]
    lname = request.form["lname"]
    sex = request.form["sex"]
    address = request.form["address"]
    salary = request.form["salary"]
    dno = request.form["dno"]
    bday = request.form["bday"]

    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO employee (Ssn, Fname, Minit, Lname, Sex, Address, Salary, Dno, BDate)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """, (ssn, fname, minit, lname, sex, address, salary, dno, bday))
        conn.commit()
        return redirect("/employees")

    except psycopg.errors.UniqueViolation:
        conn.rollback()
        return "Error: SSN must be unique.", 400
    
@app.route("/employees/<ssn>/edit", methods=["GET"])
@admin_required
def edit_employee_form(ssn):
    conn = get_db()
    cur = conn.cursor(row_factory=psycopg.rows.dict_row)
    cur.execute("""
        SELECT Ssn AS ssn,
               Fname AS first_name,
               Minit AS middle_initial,
               Lname AS last_name,
               Sex AS sex,
               Address AS address,
               Salary AS salary,
               Dno AS dno,
               BDate AS bday
        FROM Employee
        WHERE Ssn = %s;
    """, (ssn,))
    emp = cur.fetchone()
    return render_template("employee_edit.html", emp=emp)

@app.route("/employees/<ssn>/edit", methods=["POST"])
def edit_employee_submit(ssn):
    conn = get_db()
    first_name = request.form["first_name"]
    middle_initial = request.form["middle_initial"]
    last_name = request.form["last_name"]
    sex = request.form["sex"]
    address = request.form["address"]
    salary = int(request.form["salary"])
    dno = int(request.form["dno"])
    bday = request.form["bday"] or None

    cur = conn.cursor()
    cur.execute("""
        UPDATE Employee
        SET Fname=%s, Minit=%s, Lname=%s, Sex=%s, Address=%s, Salary=%s, Dno=%s, BDate=%s
        WHERE Ssn=%s;
    """, (first_name, middle_initial, last_name, sex, address, salary, dno, bday, ssn))

    conn.commit()
    return redirect("/employees")

@app.route("/employees/<ssn>/delete", methods=["POST"])
@admin_required
def delete_employee(ssn):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM employee WHERE Ssn=%s;", (ssn,))
        conn.commit()
        return redirect("/employees")

    except psycopg.errors.ForeignKeyViolation:
        conn.rollback()
        return (
            "Cannot delete employee: They are referenced in Works_on,"
            " Dependent, or manage/supervise another worker.",
            400
        )
    
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

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)