from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_wtf import FlaskForm  # Add this import
from wtforms import StringField, PasswordField, SubmitField  # Add this import
from wtforms.validators import DataRequired, Length  # Add this import
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from database import *
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class User(UserMixin):
    def __init__(self, id, username, password, is_admin, credits):
        self.id = id
        self.username = username
        self.password = password
        self.is_admin = is_admin
        self.credits = credits

@login_manager.user_loader
def load_user(user_id):
    user = fetch_user_by_id(user_id)  # Fetch from the database
    if user:
        return User(id=user['id'], username=user['username'], password=user['password'], is_admin=user['is_admin'], credits=user['credits'])
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = fetch_user_by_username(form.username.data)  # Fetch user from the database
        if user and form.password.data == user['password']:
            user_obj = User(id=user['id'], username=user['username'], password=user['password'], is_admin=user['is_admin'], credits=user['credits'])
            login_user(user_obj)
            flash('Logged in successfully.')    
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
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        submissions = fetch_submissions(admin=True)  # Fetch all submissions for admin
        template = 'admin_dashboard.html'
    else:
        submissions = fetch_submissions(user_id=current_user.id)  # Fetch user-specific submissions
        template = 'dashboard.html'
    return render_template(template, username=current_user.username, credits=current_user.credits, submissions=submissions)

@app.route('/view_account')
@login_required
def view_account():
    user = fetch_user_by_id(current_user.id)  # Fetch user data
    if not user:
        flash('User not found.')
        return redirect(url_for('dashboard'))
    return render_template('view_account.html', user=user)

@app.route('/update_credits', methods=['GET', 'POST'])
@login_required
def update_credits():
    if request.method == 'POST':
        try:
            # Get the current credits from the current_user object
            current_credits = current_user.credits

            # Get the amount of credits to add from the form
            add_credits = request.form.get('add_credits', 0, type=int)

            # Calculate the new balance
            new_balance = current_credits + add_credits

            # Update the user's credits in the database
            update_credits_by_id(current_user.id, new_balance)

            # Flash a success message and redirect to the dashboard
            flash(f"Credits updated successfully! Your new balance is {new_balance}.")
            return redirect(url_for('dashboard'))

        except Exception as e:
            # If there’s an error, flash an error message and redirect to the update form
            flash(f"An error occurred: {str(e)}")
            return redirect(url_for('update_credits'))
    
    return render_template('update_credits.html', credits=current_user.credits)

@app.route('/select_model', methods=['GET', 'POST'])
@login_required
def select_model():
    if request.method == 'POST':
        try:
            # Debug: Log the form submission
            print("Form submitted successfully")

            # Insert a problem into the database using the function from database.py
            problem_id = insert_problem(
                user_id=current_user.id,  # Pass the current user's ID
                num_vehicles=None,        # Placeholder, to be updated later
                depot=None,               # Placeholder
                max_distance=None,        # Placeholder
                locations=None,           # Placeholder (empty JSON)
                status='Not Ready'        # Problem's initial status
            )

            # Debug: Log the inserted problem ID
            print(f"Problem created with ID: {problem_id}")

            # Redirect to view_submission so the user can add/edit parameters for the newly created problem
            return redirect(url_for('view_submission', submission_id=problem_id))

        except Exception as e:
            # Debug: Log the error message
            print(f"An error occurred: {str(e)}")

            flash(f"An error occurred: {str(e)}")
            return redirect(url_for('select_model'))

    return render_template('select_model.html')



@app.route('/view_submission/<int:submission_id>', methods=['GET', 'POST'])
@login_required
def view_submission(submission_id):
    submission = fetch_submission_by_id(submission_id)  # Fetch submission from the database
    username = fetch_username_by_id(submission['user_id'])

    if request.method == 'POST':
        try:
            # Update problem parameters
            num_vehicles = request.form.get('num_vehicles')
            depot = request.form.get('depot')
            max_distance = request.form.get('max_distance')
            locations = request.form.get('locations')  # Locations should be in JSON format

            # Update the problem in the database
            update_problem(
                submission_id=submission_id,
                num_vehicles=num_vehicles,
                depot=depot,
                max_distance=max_distance,
                locations=locations,
                status='Ready to Run'
            )

            flash("Problem updated successfully.")
            return redirect(url_for('view_submission', submission_id=submission_id))

        except Exception as e:
            flash(f"An error occurred: {str(e)}")
            return redirect(url_for('view_submission', submission_id=submission_id))

    return render_template('view_submission.html', submission=submission, username=username)

@app.route('/update_submission/<int:submission_id>', methods=['POST'])
@login_required
def update_submission(submission_id):
    try:
        # Fetch current submission data from the database
        current_submission = fetch_submission_by_id(submission_id)
        
        # Retrieve updated form data
        num_vehicles = request.form.get('num_vehicles')
        depot = request.form.get('depot')
        max_distance = request.form.get('max_distance')
        
        # Parse JSON string from the locations field
        locations = request.form.get('locations')

        # Validate and parse locations field if provided
        if locations:
            try:
                locations = json.loads(locations)
            except json.JSONDecodeError:
                flash("Invalid JSON format for locations.")
                return redirect(url_for('view_submission', submission_id=submission_id))

        # Check if all the fields are filled
        if num_vehicles and depot and max_distance and locations:
            status = 'Ready'  # If all fields are provided, set status to 'Ready'
        else:
            status = current_submission['status']  # Retain the current status if fields are missing

        # Update the submission in the database
        update_problem(
            submission_id=submission_id,
            num_vehicles=num_vehicles,
            depot=depot,
            max_distance=max_distance,
            locations=json.dumps(locations) if locations else None,  # Store locations as JSON
            status=status  # Update status to 'Ready' or retain existing status
        )

        print('Submission updated successfully.')
    except Exception as e:
        print(f"An error occurred: {str(e)}")

    return redirect(url_for('view_submission', submission_id=submission_id))

@app.route('/run_submission/<int:submission_id>', methods=['POST'])
@login_required
def run_submission(submission_id):
    # Update the submission status to 'Executed'
    update_submission_status(submission_id, 'Executed')
    flash('Submission executed successfully.')
    return redirect(url_for('dashboard'))

@app.route('/delete_submission/<int:submission_id>', methods=['POST'])
@login_required
def delete_submission(submission_id):
    delete_submission(submission_id)  # Delete the problem
    flash('Submission deleted successfully.')
    return redirect(url_for('dashboard'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404
