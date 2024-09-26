import re
import sqlite3
import time
from flask import Flask, render_template
from flask import request, redirect, session, url_for, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SESSION_COOKIE_SECURE'] = True  # Use secure cookies for session
# Prevent JavaScript access to session cookie
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Prevent CSRF attacks

login_attempts = {}  # Track login attempts for rate limiting
DATABASE = 'Cricket.db.db'  # SQLite database file


# Function to establish a database connection
def get_db_connection():
    conn = sqlite3.connect(DATABASE)  # Connect to the SQLite database
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn  # Return the connection object


# Decorator to enforce login requirement for certain routes
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:  # Check if the user is logged in
            flash("Please log in to access this page.")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)  # Proceed to the requested function
    return decorated_function


# Error handler for 500 internal server errors
@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


# Home route, displays the login page
@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template("login.html")


# Login route for user authentication
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':  # If the form is submitted
        username = request.form.get('username')  # Get the username
        password = request.form.get('password')  # Get the password
        # Validate input
        if not username or not password:
            flash("Please enter both username and password.")
            return render_template('login.html')

        # Rate limiting logic
        ip_address = request.remote_addr
        current_time = time.time()
        attempts = login_attempts.get(ip_address, [])

        # Clean up old attempts
        attempts = [t for t in attempts if current_time - t < 30]
        login_attempts[ip_address] = attempts

        # Check if too many attempts were made
        if len(attempts) >= 5:
            flash("Too many login attempts. Please try again later in 30 seconds.")
            return render_template('login.html')

        # Proceed with login logic
        conn = get_db_connection()
        cur = conn.cursor()
        # Query for password
        cur.execute("SELECT password FROM User WHERE username = ?", (username,))
        user = cur.fetchone()
        conn.close()

        # Validate password
        if user and check_password_hash(user[0], password):  # Check hashed password
            session.clear()
            session['username'] = username
            session.permanent = True  # Set session as permanent for logged-in users
            session.modified = False  # Ensure the session is saved
            next_page = request.args.get('next')
            return redirect(next_page or url_for('about'))
        else:
            flash("Invalid username or password.")
            login_attempts[ip_address].append(current_time)

    return render_template('login.html')


# Route for user logout
@app.route('/logout')
def logout():
    session.clear()  # Clear the session data
    session.permanent = False  # Set the session to not be permanent
    session.modified = True  # Mark session as modified
    flash("You have been successfully logged out.")
    return render_template('login.html')


# Registration route for new users
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        # Validate input
        if password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for('register'))
        elif len(password) < 7:
            flash("Password should be at least 7 characters long.")
            return redirect(url_for('register'))
        elif len(username) < 5:
            flash("The username should be at least 5 characters long.")
            return redirect(url_for('register'))
        elif len(username) > 10:
            flash("Username should be at most 10 characters.")
            return redirect(url_for('register'))
        elif not re.search(r'[A-Z]', password):
            flash("Password should contain at least one uppercase letter.")
            return redirect(url_for('register'))

        try:
            conn = get_db_connection()
            # Set WAL mode for improved concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            cur = conn.cursor()
            # Insert new user into the User table with a hashed password
            cur.execute("INSERT INTO User (username, password) VALUES (?, ?)",
                        (username, generate_password_hash(password)))
            conn.commit()
            return redirect(url_for('registration_successful'))
        except sqlite3.IntegrityError:
            flash("Username already exists. Please choose a different username.")
            return redirect(url_for('register'))
        except sqlite3.OperationalError:
            # if database is locked
            flash("Database is busy. Please try again in a few moments.")
            return redirect(url_for('register'))
        finally:
            if conn:
                conn.close()

    return render_template('register.html')  # Render registration page for GET requests


# Route for successful registration
@app.route('/registration_successful')
def registration_successful():
    return render_template('registeration.html')


# Route for the about page, requires login
@app.route('/about')
@login_required
def about():
    return render_template("CricketPortal.html")


# Route for listing players, requires login
@app.route('/players')
@login_required
def players():
    conn = get_db_connection()
    cur = conn.cursor()
    # Query to get all teams and their respective players
    cur.execute("""
    SELECT
       Teams.TeamName,
        Player.PlayerName,
        Player.Role,
        Matches.Matches,
        Matches.Average,
        Matches.Innings,
        Matches.Runs,
        Matches.Wickets
    FROM Teams
    INNER JOIN Player ON Teams.TeamId = Player.TeamId
    INNER JOIN Matches ON Player.PlayerId = Matches.PlayerId
    WHERE Player.Verified = 1
    ORDER BY Teams.TeamName, Player.PlayerName
    """)
    players_by_team = cur.fetchall()
    conn.close()
    teams_data = {}
    for row in players_by_team:
        team_name = row[0]  # Extract team name
        player_data = row[1:]  # Extract player data
        if team_name not in teams_data:
            teams_data[team_name] = []
        teams_data[team_name].append(player_data)
    return render_template("Players.html", teams_data=teams_data)


# Route for searching players, requires login
@app.route('/search', methods=['GET'])
@login_required  # Protect this route with login requirement
def search():
    query = request.args.get('query', '')  # Get the search query
    conn = get_db_connection()  # Establish DB connection
    cur = conn.cursor()
    # Query to get searched players details
    cur.execute("""
        SELECT Player.PlayerName, Player.Role, Matches.Matches, Matches.Average,
               Matches.Innings, Matches.Runs, Matches.Wickets, Matches.Team
        FROM Player
        INNER JOIN Matches ON Player.PlayerId = Matches.PlayerId
        WHERE Player.Verified = 1 AND Player.PlayerName LIKE ?
    """, ('%' + query + '%',))
    players = cur.fetchall()
    conn.close()

    if not players:  # If no players found
        abort(404)  # Trigger 404 error

    teams_data = {}  # Prepare data structure for rendering
    for player in players:
        team_name = player[7]  # Extract team name
        if team_name not in teams_data:
            teams_data[team_name] = []
        teams_data[team_name].append(player)
    return render_template("Players.html", teams_data=teams_data, query=query)


# Route for adding a player, requires login
@app.route('/players', methods=['GET', 'POST'])
@login_required  # Protect this route with login requirement
def add_player():
    if request.method == 'POST':
        player_name = request.form['player_name']  # Get player name
        role = request.form['role']  # Get player role
        conn = get_db_connection()
        cur = conn.cursor()

        # Validate input
        if len(player_name) > 40:
            flash("The player name is quite long")
        elif len(player_name) < 3:
            flash("Please enter a correct player name")
        elif len(role) > 10:
            flash("Please enter the correct role")
        elif len(role) < 5:
            flash("Please enter the correct role")
        else:
            flash('Player will be added after a profanity check.')

        # Insert player into PendingPlayers table
        cur.execute("""
        INSERT INTO PendingPlayers (PlayerName, Role)
        VALUES (?, ?)
        """, (player_name, role))
        conn.commit()
        return redirect(url_for('players'))


# Route for displaying rankings, requires login
@app.route('/ranking', defaults={'ranking_id': None})
@login_required
def ranking(ranking_id):
    format = request.args.get('format', 'ALL').upper()
    conn = get_db_connection()
    cur = conn.cursor()
    # Determine SQL query based on the format
    if format == 'TEST':
        query = "SELECT Ranking, Player_Name, points, team, 'TEST' AS Format FROM TEST"
    elif format == 'T20':
        query = "SELECT Ranking, Player_Name, points, team, 'T20' AS Format FROM T20"
    elif format == 'ODI':
        query = "SELECT Ranking, Player_Name, points, team, 'ODI' AS Format FROM ODI"
    elif format == 'ALL':
        query = """
            SELECT Ranking, Player_Name, points, team, 'T20' AS Format FROM T20
            UNION
            SELECT Ranking, Player_Name, points, team, 'ODI' AS Format FROM ODI
            UNION
            SELECT Ranking, Player_Name, points, team, 'TEST' AS Format FROM TEST
        """
    else:
        abort(500)

    cur.execute(query)
    crickets = cur.fetchall()
    conn.close()
    return render_template("Ranking.html", crickets=crickets)


# Route for displaying records, requires login
@app.route('/record')
@login_required
def record():
    conn = get_db_connection()
    cur = conn.cursor()
    # Query to get distinct team records
    cur.execute("""
        SELECT DISTINCT
            t.TeamName AS country,
            tr.record_test,
            o.record_odi,
            t.record_value
        FROM
            test_records tr
        LEFT JOIN
            odi_records o ON tr.Team_id = o.Team_id
        LEFT JOIN
            t20_records t ON tr.Team_id = t.Team_id
        LEFT JOIN
            Teams t ON tr.Team_id = t.Teamid
        ORDER BY
            t.TeamName
    """)
    crickets = cur.fetchall()
    conn.close()
    return render_template("Record.html", crickets=crickets)


# Route for displaying statistics, requires login
@app.route('/stats')
@login_required
def statistics():
    conn = get_db_connection()
    cur = conn.cursor()
    # Query for statistics to extract information, images and team name
    cur.execute("SELECT Team, image_url, Information FROM Statistics")
    teams_info = cur.fetchall()
    conn.close()
    return render_template("Stats.html", teams_info=teams_info)


# Review for route
@app.route('/review')
@login_required
def review():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Review WHERE Is_Deleted = 0")
    crickets = cur.fetchall()
    conn.close()
    return render_template("Review.html", crickets=crickets)


# Route for adding a review, requires login
@app.route('/addreview', methods=['POST'])
@login_required
def add_review():
    comments = request.form['Review']  # Get review comments
    rating = request.form['rating']  # Get review rating
    conn = get_db_connection()
    cur = conn.cursor()

    # Validate review length
    if len(comments.split()) > 200:
        flash("The review should be below 200 words.")
        conn.close()
        return redirect('/404')  # Redirect to 404 error page
    cur.execute("""INSERT INTO Review(comments, rating) VALUES (?, ?)""",
                (comments, rating))
    conn.commit()
    conn.close()
    return redirect('/review')


# Main entry point for running the app
if __name__ == "__main__":
    app.run(debug=True)
