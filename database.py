import sqlite3

def get_db_connection():
    conn = sqlite3.connect('/app/db/saastest.db')
    conn.row_factory = sqlite3.Row
    return conn

# Fetch user by username
def fetch_user_by_username(username):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return user

# Fetch user by ID
def fetch_user_by_id(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return user

def fetch_username_by_id(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return user['username']

def update_credits_by_id(user_id, new_credits):
    """Update the credits for a user in the database."""
    conn = get_db_connection()
    
    try:
        # Update the credits in the user_credits table
        conn.execute('UPDATE users SET credits = ? WHERE id = ?', (new_credits, user_id))
        conn.commit()
    finally:
        conn.close()

# Insert a new problem into the database
def insert_problem(user_id, num_vehicles, depot, max_distance, locations, status):
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO vrp_problems (user_id, num_vehicles, depot, max_distance, locations, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, num_vehicles, depot, max_distance, locations, status))
    conn.commit()
    problem_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.close()
    return problem_id

def update_vrp_problem(submission_id, num_vehicles, depot, max_distance, locations):
    conn = get_db_connection()
    conn.execute('''
        UPDATE vrp_problems
        SET num_vehicles = ?, depot = ?, max_distance = ?, locations = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (num_vehicles, depot, max_distance, locations, submission_id))
    conn.commit()
    conn.close()
    
def update_submission_in_db(submission_id, num_vehicles, depot, max_distance, locations_json, status):
    conn = get_db_connection()
    conn.execute('''
        UPDATE vrp_problems
        SET num_vehicles = ?, depot = ?, max_distance = ?, locations = ?, updated_at = CURRENT_TIMESTAMP, status = ?
        WHERE id = ?
    ''', (num_vehicles, depot, max_distance, locations_json, submission_id, status))
    conn.commit()
    conn.close()

# Fetch submission by ID
def fetch_submission_by_id(submission_id):
    conn = get_db_connection()
    submission = conn.execute('SELECT * FROM vrp_problems WHERE id = ?', (submission_id,)).fetchone()
    conn.close()
    return submission

# Fetch all submissions or submissions by a specific user
def fetch_submissions(user_id=None, admin=False):
    conn = get_db_connection()
    if admin:
        submissions = conn.execute('SELECT * FROM vrp_problems ORDER BY created_at DESC').fetchall()
    else:
        submissions = conn.execute('SELECT * FROM vrp_problems WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()
    conn.close()
    return submissions

# Update a submission's parameters
def update_problem(submission_id, num_vehicles, depot, max_distance, locations, status):
    conn = get_db_connection()
    conn.execute('''
        UPDATE vrp_problems
        SET num_vehicles = ?, depot = ?, max_distance = ?, locations = ?, status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (num_vehicles, depot, max_distance, locations, status, submission_id))
    conn.commit()
    conn.close()


# Update submission status
def update_submission_status(submission_id, status):
    conn = get_db_connection()
    conn.execute('UPDATE vrp_problems SET status = ? WHERE id = ?', (status, submission_id))
    conn.commit()
    conn.close()

# Delete a submission
def delete_submission(submission_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM vrp_problems WHERE id = ?', (submission_id,))
    conn.commit()
    conn.close()
