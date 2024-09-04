from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import sqlite3
from ortools.linear_solver import pywraplp
import json
from solvers import solve_linear_program, solve_integer_program, solve_mixed_integer_program

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
    conn = get_db_connection()
    submissions = conn.execute('SELECT * FROM problems WHERE user_id = ?', (current_user.id,)).fetchall()
    conn.close()
    return render_template('dashboard.html', username=current_user.username, submissions=submissions)

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

@app.route('/select_model', methods=['GET', 'POST'])
@login_required
def select_model():
    if request.method == 'POST':
        selected_model_id = request.form.get('model')
        session['selected_model_id'] = selected_model_id
        return redirect(url_for('submit_problem_step2'))

    # Fetch available models from the database
    conn = get_db_connection()
    models = conn.execute('SELECT id, title, notes FROM models').fetchall()
    conn.close()
    return render_template('select_model.html', models=models)

# Route for submitting an OR-Tools problem
@app.route('/submit_problem_step2', methods=['GET', 'POST'])
@login_required
def submit_problem_step2():
    if request.method == 'POST':
        try:
            # Debug: Print out form data
            print("Received POST data:", request.form)

            # Retrieve model details from form
            selected_model_id = request.form.get('model_id')
            selected_model_title = request.form.get('model_title')
            selected_model_notes = request.form.get('model_notes')

            # Debug: Print out retrieved form data
            print("Selected Model ID:", selected_model_id)
            print("Selected Model Title:", selected_model_title)
            print("Selected Model Notes:", selected_model_notes)

            # Handle file uploads
            metadata_file = request.files.get('metadata')
            input_data_file = request.files.get('input_data')

            if not metadata_file or not input_data_file:
                flash("Both metadata and input data files are required.")
                return redirect(url_for('submit_problem_step2'))

            # Optional: Validate file types
            allowed_extensions = ['txt', 'csv', 'json']
            if not (metadata_file.filename.endswith(tuple(allowed_extensions)) and 
                    input_data_file.filename.endswith(tuple(allowed_extensions))):
                flash("Invalid file type. Only .txt, .csv, .json files are allowed.")
                return redirect(url_for('submit_problem_step2'))

            # Process the files and save them (e.g., save to the filesystem)
            metadata_content = metadata_file.read().decode('utf-8')
            input_data_content = input_data_file.read().decode('utf-8')

            # Insert into database
            conn = get_db_connection()
            conn.execute('''
                INSERT INTO problems (user_id, title, description, objective_function, constraints, problem_type, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                current_user.id,
                f"Problem for Model {selected_model_id}",
                "Description based on uploaded metadata and input data",
                metadata_content,
                input_data_content,
                selected_model_id,
                'Ready to Run'
            ))
            conn.commit()

            # Retrieve the last inserted ID
            problem_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            conn.close()

            flash("Problem submission created successfully.")
            return redirect(url_for('view_submission', submission_id=problem_id))

        except Exception as e:
            flash(f"An error occurred: {str(e)}")
            return redirect(url_for('submit_problem_step2'))

    # If GET request, assume data is passed in URL query parameters
    selected_model_id = request.args.get('model_id')
    selected_model_title = request.args.get('model_title')
    selected_model_notes = request.args.get('model_notes')

    if not selected_model_id:
        flash("Invalid request. Please select a model.")
        return redirect(url_for('select_model'))

    return render_template('submit_problem.html', selected_model={
        'id': selected_model_id,
        'title': selected_model_title,
        'notes': selected_model_notes
    })
    
@app.route('/view_submission/<int:submission_id>', methods=['GET'])
@login_required
def view_submission(submission_id):
    conn = get_db_connection()
    submission = conn.execute('SELECT * FROM problems WHERE id = ?', (submission_id,)).fetchone()
    
    # Assuming you store metadata and input data as JSON in the database
    metadata = json.loads(submission['metadata']) if submission['metadata'] else []
    input_data = json.loads(submission['input_data']) if submission['input_data'] else []

    submission_data = {
        'scenario_id': submission_id,
        'scenario_name': submission['title'],
        'solver_id': submission['problem_type'],
        'creator': current_user.username,
        'created_on': submission['created_at'],
        'status': submission['status'],
        'metadata': metadata,
        'input_data': input_data
    }

    conn.close()

    return render_template('view_submission.html', submission=submission_data)

@app.route('/view_account')
@login_required
def view_account():
    # Render the account page
    return render_template('view_account.html', user=current_user)

# Route for viewing the results of the OR-Tools problem
@app.route('/view_results')
@login_required
def view_results():
    result = session.get('result', None)
    session.pop('result', None)  # Clear the result after retrieving
    return render_template('view_results.html', result=result)

@app.route('/run_submission/<int:submission_id>', methods=['POST'])
@login_required
def run_submission(submission_id):
    # Here, you would add the logic to execute the OR-Tools solver or whatever task needs to be run
    # For now, we'll just update the status to 'Executed' to simulate a run

    conn = get_db_connection()
    conn.execute('UPDATE problems SET status = ? WHERE id = ?', ('Executed', submission_id))
    conn.commit()
    conn.close()

    flash('Submission executed successfully.')
    return redirect(url_for('dashboard'))


@app.route('/delete_submission/<int:submission_id>', methods=['POST'])
@login_required
def delete_submission(submission_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM problems WHERE id = ?', (submission_id,))
    conn.commit()
    conn.close()

    flash('Submission deleted successfully.')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
