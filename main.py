from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import sqlite3
from ortools.linear_solver import pywraplp


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

def get_db_connection():
    conn = sqlite3.connect('/app/db/saastest.db')
    conn.row_factory = sqlite3.Row
    return conn

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class User(UserMixin):
    def __init__(self, id, username, password, is_admin):
        self.id = id
        self.username = username
        self.password = password
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return User(id=user['id'], username=user['username'], password=user['password'], is_admin=user['is_admin'])
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (form.username.data,)).fetchone()
        conn.close()
        if user and form.password.data == user['password']:
            user_obj = User(id=user['id'], username=user['username'], password=user['password'], is_admin=user['is_admin'])
            login_user(user_obj)
            flash('Logged in successfully.')

            # Redirect based on user role
            if user_obj.is_admin:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('index'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=current_user.username, is_admin=current_user.is_admin)

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    return render_template('admin_dashboard.html', users=users)

# Route for submitting an OR-Tools problem
@app.route('/submit_problem', methods=['GET', 'POST'])
@login_required
def submit_problem():
    if request.method == 'POST':
        try:
            # Parse objective coefficients
            objective_coefficients = list(map(float, request.form.get('objective').split(',')))

            # Parse constraint coefficients
            constraints_raw = request.form.getlist('constraints')
            constraint_coefficients = [list(map(float, x.split(','))) for x in constraints_raw]

            # Parse bounds
            bounds = list(map(float, request.form.get('bounds').split(',')))

            # Solve the problem using OR-Tools
            solver = pywraplp.Solver.CreateSolver('GLOP')

            num_vars = len(objective_coefficients)
            x = [solver.NumVar(0, solver.infinity(), f'x{i}') for i in range(num_vars)]

            solver.Maximize(solver.Sum(objective_coefficients[i] * x[i] for i in range(num_vars)))

            for coeff, bound in zip(constraint_coefficients, bounds):
                solver.Add(solver.Sum(coeff[i] * x[i] for i in range(num_vars)) <= bound)

            status = solver.Solve()

            if status == pywraplp.Solver.OPTIMAL:
                result = {
                    'objective_value': solver.Objective().Value(),
                    'variable_values': [var.solution_value() for var in x]
                }
                session['result'] = result  # Store result in session
            else:
                session['result'] = None

            return redirect(url_for('view_results'))

        except ValueError as e:
            flash(f"Input error: {str(e)}. Please check your input and try again.")
            return redirect(url_for('submit_problem'))

    return render_template('submit_problem.html')

# Route for viewing the results of the OR-Tools problem
@app.route('/view_results')
@login_required
def view_results():
    result = session.get('result', None)
    session.pop('result', None)  # Clear the result after retrieving
    return render_template('view_results.html', result=result)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
