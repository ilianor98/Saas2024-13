from flask import Flask, render_template, request, redirect, url_for, flash, session, current_app, send_file, make_response
from flask_wtf import FlaskForm  # Add this import
from wtforms import StringField, PasswordField, SubmitField  # Add this import
from wtforms.validators import DataRequired, Length  # Add this import
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from database import *
import json
import os
import tempfile
import subprocess
import io
import pandas as pd
import time
import xlsxwriter

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
    submission = fetch_submission_by_id(submission_id)
    username = fetch_username_by_id(submission['user_id'])

    if request.method == 'POST':
        try:
            # Retrieve and convert form data
            num_vehicles = request.form.get('num_vehicles') or submission['num_vehicles']
            depot = request.form.get('depot') or submission['depot']
            max_distance = request.form.get('max_distance') or submission['max_distance']
            locations = request.form.get('locations') or submission['locations']
            name = request.form.get('name') or submission['name']

            # Convert to appropriate types if not None
            num_vehicles = int(num_vehicles) if num_vehicles else None
            depot = int(depot) if depot else None
            max_distance = int(max_distance) if max_distance else None
            locations = int(locations) if locations else 0  # Default to 0 if not provided

            # Validate 'locations' selection
            if locations not in [1, 2, 3]:
                locations = 0

            # Determine the status based on parameters
            if num_vehicles and depot is not None and max_distance and locations != 0:
                status = 'Ready'
            else:
                status = 'Not Ready'

            # Update the problem in the database
            update_problem(
                submission_id=submission_id,
                num_vehicles=num_vehicles,
                depot=depot,
                max_distance=max_distance,
                locations=locations,
                status=status,
                name=name
            )

            flash("Problem updated successfully.")
            return redirect(url_for('view_submission', submission_id=submission_id))

        except ValueError as e:
            flash(f"Invalid input: {str(e)}")
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

@app.route('/run_submission/<int:submission_id>')
@login_required
def run_submission(submission_id):
    try:
        # Fetch the submission from the database
        submission = fetch_submission_by_id(submission_id)

        # Ensure the submission exists
        if not submission:
            flash("Submission not found.")
            return redirect(url_for('dashboard'))

        # Ensure the submission belongs to the current user, or the user is an admin
        if submission['user_id'] != current_user.id and not current_user.is_admin:
            flash("Access denied.")
            return redirect(url_for('dashboard'))

        # Check if the submission is ready to run
        if submission['status'] != 'Ready':
            flash("Submission is not ready to run.")
            return redirect(url_for('dashboard'))

        # Extract parameters
        num_vehicles = submission['num_vehicles']
        depot = submission['depot']
        max_distance = submission['max_distance']
        locations_choice = submission['locations']  # This is now an integer between 1 and 3

        # Validate parameters
        if None in (num_vehicles, depot, max_distance, locations_choice):
            flash("Submission parameters are incomplete.")
            return redirect(url_for('dashboard'))

        # Map the locations_choice to the corresponding JSON file
        locations_files = {
            1: 'locations_20.json',
            2: 'locations_200.json',
            3: 'locations_1000.json'
        }

        if locations_choice in locations_files:
            # Build the path to the JSON file
            locations_file = os.path.join(app.root_path, 'jsons', locations_files[locations_choice])
        else:
            flash("Invalid locations selection.")
            return redirect(url_for('dashboard'))

        # Ensure the JSON file exists
        if not os.path.isfile(locations_file):
            flash(f"Locations file not found: {locations_files[locations_choice]}")
            return redirect(url_for('dashboard'))

        # Prepare the command to run vrpSolver.py
        vrp_solver_script = os.path.join(app.root_path, 'vrpSolver.py')
        cmd = [
            'python', vrp_solver_script,
            locations_file,
            str(num_vehicles),
            str(depot),
            str(max_distance)
        ]

        # Record the start time
        start_time = time.time()

        # Run vrpSolver.py as a subprocess
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Record the end time
        end_time = time.time()

        # Calculate execution time
        execution_time = end_time - start_time  # In seconds

        # Calculate credits as integer part of execution time
        credits = int(execution_time)

        # Check for errors
        if result.returncode != 0:
            # vrpSolver.py returned an error
            error_message = result.stderr or result.stdout
            update_submission_results(
                submission_id=submission_id,
                success=0,
                result=error_message,
                status='Executed',  # Update status even if failed
                execution_time=execution_time,
                credits=credits
            )
            flash(f"Solver failed: {error_message}")
        else:
            # Get the output from vrpSolver.py
            solver_output = result.stdout

            # Parse the output to extract the results
            objective_value, routes = parse_solver_output(solver_output)

            # Update the submission in the database
            update_submission_results(
                submission_id=submission_id,
                objective_value=objective_value,
                routes=json.dumps(routes) if routes else None,
                result=solver_output,
                success=1,
                status='Executed',  # Update the status to 'Executed'
                execution_time=execution_time,
                credits=credits
            )
            flash("Submission executed successfully.")

        # Redirect back to the dashboard
        return redirect(url_for('dashboard'))

    except Exception as e:
        flash(f"An error occurred while running the submission: {str(e)}")
        return redirect(url_for('dashboard'))
    
def parse_solver_output(output):
    """
    Parses the output from vrpSolver.py and extracts the objective value and routes.
    """
    objective_value = None
    routes = []
    max_route_distance = None

    lines = output.strip().split('\n')
    current_vehicle = None
    route = []
    route_distance = None

    for line in lines:
        line = line.strip()
        if line.startswith('Objective:'):
            # Extract objective value
            try:
                objective_value = int(line.split(':')[1].strip())
            except ValueError:
                objective_value = None
        elif line.startswith('Route for vehicle'):
            # Save previous vehicle's route if exists
            if current_vehicle is not None:
                routes.append({
                    'Vehicle': current_vehicle,
                    'Route': route,
                    'Distance': route_distance
                })
            # Start new vehicle route
            current_vehicle = int(line.split('vehicle')[1].split(':')[0].strip())
            route = []
            route_distance = None
        elif '->' in line:
            # Extract route nodes
            nodes = line.strip().split('->')
            for node in nodes:
                node = node.strip()
                if node.isdigit():
                    route.append(int(node))
        elif line.startswith('Distance of the route:'):
            # Extract route distance
            try:
                route_distance = int(line.split(':')[1].strip().rstrip('m'))
            except ValueError:
                route_distance = None
        elif line.startswith('Maximum of the route distances:'):
            # Extract max route distance
            try:
                max_route_distance = int(line.split(':')[1].strip().rstrip('m'))
            except ValueError:
                max_route_distance = None

    # Append the last vehicle's route
    if current_vehicle is not None:
        routes.append({
            'Vehicle': current_vehicle,
            'Route': route,
            'Distance': route_distance
        })

    return objective_value, routes

@app.route('/delete_submission/<int:submission_id>', methods=['POST'])
@login_required
def delete_submission_route(submission_id):
    # Fetch the submission
    submission = fetch_submission_by_id(submission_id)
    if not submission:
        flash("Submission not found.")
        return redirect(url_for('dashboard'))

    # Ensure the submission belongs to the current user or the user is an admin
    if submission['user_id'] != current_user.id and not current_user.is_admin:
        flash("Access denied.")
        return redirect(url_for('dashboard'))

    # Delete the submission
    delete_submission(submission_id)
    flash('Submission deleted successfully.')
    return redirect(url_for('dashboard'))

@app.route('/view_results/<int:submission_id>')
@login_required
def view_results(submission_id):
    # Fetch the submission from the database
    submission = fetch_submission_by_id(submission_id)

    # Ensure the submission exists
    if not submission:
        flash("Submission not found.")
        return redirect(url_for('dashboard'))

    # Ensure the submission belongs to the current user or the user is an admin
    if submission['user_id'] != current_user.id and not current_user.is_admin:
        flash("Access denied.")
        return redirect(url_for('dashboard'))

    # Check if the submission has been executed
    if submission['status'] != 'Executed':
        flash("Results are not available for this submission.")
        return redirect(url_for('dashboard'))

    # Retrieve the results from the submission
    objective_value = submission['objective_value']
    routes_json = submission['routes']
    result_text = submission['result']
    success = submission['success']

    # Parse the routes JSON
    if routes_json:
        try:
            routes = json.loads(routes_json)
        except json.JSONDecodeError as e:
            flash(f"Error parsing routes data: {str(e)}")
            routes = None
    else:
        routes = None

    # Retrieve input parameters
    num_vehicles = submission['num_vehicles']
    depot = submission['depot']
    max_distance = submission['max_distance']
    locations_choice = submission['locations']  # Now an integer between 1 and 3

    # Map the locations_choice to the corresponding JSON file
    locations_files = {
        1: 'locations_20.json',
        2: 'locations_200.json',
        3: 'locations_1000.json'
    }

    if locations_choice in locations_files:
        locations_file = os.path.join(app.root_path, 'jsons', locations_files[locations_choice])
        # Read the locations data from the file
        try:
            with open(locations_file, 'r') as f:
                locations_data = json.load(f)
                locations = locations_data.get('Locations', [])
        except Exception as e:
            flash(f"Error reading locations file: {str(e)}")
            locations = None
    else:
        locations = None
        flash("Invalid locations selection.")

    # Parse the result_text to extract MaxRouteDistance
    if result_text:
        try:
            lines = result_text.strip().split('\n')
            max_route_distance = None
            for line in lines:
                if line.startswith('Maximum of the route distances:'):
                    max_route_distance = int(line.split(':')[1].strip().rstrip('m'))
                    break
            if max_route_distance is None:
                max_route_distance = 'N/A'
        except Exception as e:
            max_route_distance = 'N/A'
    else:
        max_route_distance = 'N/A'

    # Compute the number of vehicles used
    vehicles_used = sum(1 for route in routes if route['Distance'] > 0) if routes else 0

    # Calculate the total distance
    total_distance = sum(route['Distance'] for route in routes) if routes else 0

    # Pass all data to the template
    return render_template(
        'view_results.html',
        submission=submission,
        objective_value=objective_value,
        routes=routes,
        result_text=result_text,
        success=success,
        num_vehicles=num_vehicles,
        depot=depot,
        max_distance=max_distance,
        locations=locations,
        max_route_distance=max_route_distance,
        vehicles_used=vehicles_used,
        total_distance=total_distance,
        execution_time=submission['execution_time'],  # Already added previously
        credits=submission['credits']  # Add this line
    )

@app.route('/download_excel/<int:submission_id>')
@login_required
def download_excel(submission_id):
    # Fetch the submission
    submission = fetch_submission_by_id(submission_id)

    # Check permissions
    if not submission or (submission['user_id'] != current_user.id and not current_user.is_admin):
        flash("Access denied.")
        return redirect(url_for('dashboard'))

    # Check if the submission was successful
    if submission['status'] != 'Executed' or submission['success'] != 1:
        flash("No data available for download.")
        return redirect(url_for('dashboard'))

    # Retrieve routes and locations
    routes_json = submission['routes']
    routes = json.loads(routes_json) if routes_json else None

    # Retrieve locations data based on `locations_choice`
    locations_choice = submission['locations']
    locations_files = {
        1: 'locations_20.json',
        2: 'locations_200.json',
        3: 'locations_1000.json'
    }

    if locations_choice in locations_files:
        locations_file = os.path.join(app.root_path, 'jsons', locations_files[locations_choice])
        try:
            with open(locations_file, 'r') as f:
                locations_data = json.load(f)
                locations = locations_data.get('Locations', [])
        except Exception as e:
            flash(f"Error reading locations file: {str(e)}")
            return redirect(url_for('dashboard'))
    else:
        flash("Invalid locations selection.")
        return redirect(url_for('dashboard'))

    # Generate Excel file
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')

    for route_info in routes:
        if route_info['Distance'] > 0:
            data = []
            for idx, location_index in enumerate(route_info['Route']):
                loc = locations[location_index]
                data.append({
                    'Stop Number': idx + 1,
                    'Location Index': location_index,
                    'Latitude': loc['Latitude'],
                    'Longitude': loc['Longitude']
                })
            df = pd.DataFrame(data)
            sheet_name = f'Vehicle_{route_info["Vehicle"]}'
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    writer.save()
    output.seek(0)

    # Send the file
    return send_file(
        output,
        attachment_filename=f'submission_{submission_id}_routes.xlsx',
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/download_raw/<int:submission_id>')
@login_required
def download_raw(submission_id):
    # Fetch the submission
    submission = fetch_submission_by_id(submission_id)

    # Check permissions
    if not submission or (submission['user_id'] != current_user.id and not current_user.is_admin):
        flash("Access denied.")
        return redirect(url_for('dashboard'))

    # Check if the submission was successful
    if submission['status'] != 'Executed' or submission['success'] != 1:
        flash("No data available for download.")
        return redirect(url_for('dashboard'))

    # Retrieve result text or routes
    result_text = submission['result']
    if not result_text:
        flash("No result data available.")
        return redirect(url_for('dashboard'))

    # Send the raw data as a file
    response = make_response(result_text)
    response.headers['Content-Disposition'] = f'attachment; filename=submission_{submission_id}_raw.txt'
    response.mimetype = 'text/plain'
    return response

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404
