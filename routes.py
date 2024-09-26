import re
import sqlite3
import time
from flask import Flask, render_template, request, redirect, session, url_for, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)  # Create Flask object
app.secret_key = 'your_secret_key'  # Secret key for session management
login_attempts = {}
app.config['SESSION_COOKIE_SECURE'] = True  # Use secure cookies
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access to session cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Prevent CSRF
DATABASE = 'Cricket.db.db'  # sql Database


def get_db_connections():
    conn = sqlite3.connect(DATABASE)  # Connect to the SQLite database
    conn.row_factory = sqlite3.Row  # Configure the connection to return rows as dictionaries
    return conn  # Return the database connection


@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500  # Render 500 error page and return 500 status


@app.errorhandler(404)
def page_not_found(e):
    # Render 404 error page and return 404 status
    return render_template("404.html"), 404


# Home route
@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template("login.html")


# ogin route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash("Please enter both username and password.")
            return render_template('login.html')

        ip_address = request.remote_addr
        current_time = time.time()
        attempts = login_attempts.get(ip_address, [])

        attempts = [t for t in attempts if current_time - t < 30]
        login_attempts[ip_address] = attempts

        if len(attempts) >= 5:
            flash("Too many login attempts. Please try again later in 30 seconds.")
            return render_template('login.html')

        conn = get_db_connections()
        cur = conn.cursor()
        cur.execute("SELECT password FROM User WHERE username = ?", (username,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user[0], password):
            session.clear()  # Clear any existing session data
            session['username'] = username
            session.permanent = True  # Set session as permanent for logged-in users
            session.modified = False  # Ensure the session is saved
            next_page = request.args.get('next')
            return redirect(next_page or url_for('about'))
        else:
            flash("Invalid username or password.")
            login_attempts[ip_address].append(current_time)

    return render_template('login.html')


# Register Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        # Validate input
        if password != confirm_password:
            flash("Passwords do not match.")
        elif len(password) < 7:
            flash("Password should be at least 7 characters long.")
        elif len(username) < 5:
            flash("The username should be at least 5 characters long.")
        elif len(username) > 10:
            flash("Username should be at most 10 characters long.")
        elif not re.search(r'[A-Z]', password):
            flash("Password should contain at least one uppercase letter.")
        else:
            try:
                conn = get_db_connections()
                # Setting the databaase to write ahead logging mode for improved concurrency
                conn.execute("PRAGMA journal_mode=WAL")
                cur = conn.cursor()
                # Insert new user into the User table with a hashed password
                cur.execute("INSERT INTO User (username, password) VALUES (?, ?)",
                            (username, generate_password_hash(password)))
                conn.commit()
                # Redirect the user to the rgistration sucess page
                return redirect(url_for('registration_successful'))
                # Handle the case to check wheather the username already exists in the database
            except sqlite3.IntegrityError:
                flash("Username already exists. Please choose a different username.")
                # Handle the case where the database is busy and cannot process the request
            except sqlite3.OperationalError:
                flash("Database is busy. Please try again in a few moments.")
            finally:
                if conn:
                    conn.close()
        return render_template('register.html')


@app.route('/logout')
def logout():
    # Clear the session
    session.clear()
    session.permanent = False
    session.modified = True
    flash("You have been successfully logged out.")
    return render_template('login.html')


# Route for Registeration sucessfull
@app.route('/registration_successful')
def registration_successful():
    return render_template('registeration.html')


# Route for Homepage of CricketPortal
@app.route('/about')
def about():
    return render_template("CricketPortal.html")  # Render Cricket portal page


# Route for Players
@app.route('/Players')
def Players():
    conn = get_db_connections()  # Establish DB connection
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
    # Process the data by having team name as the title and repsective players listed down
    teams_data = {}
    for row in players_by_team:
        team_name = row[0]
        player_data = row[1:]
        if team_name not in teams_data:
            teams_data[team_name] = []
        teams_data[team_name].append(player_data)
    return render_template("Players.html", teams_data=teams_data)  # render players page


# Route for Serach bar of players page
@app.route('/search', methods=['GET'])
def Search():
    query = request.args.get('query', '')  # Get the search query
    conn = get_db_connections()  # Establish DB connection
    cur = conn.cursor()
    # This query will get the serached players details
    cur.execute("""
        SELECT Player.PlayerName, Player.Role, Matches.Matches, Matches.Average,
               Matches.Innings, Matches.Runs, Matches.Wickets, Matches.Team
        FROM Player
        INNER JOIN Matches ON Player.PlayerId = Matches.PlayerId
        WHERE Player.Verified = 1 AND Player.PlayerName LIKE ?
    """, ('%' + query + '%',))
    players = cur.fetchall()  # Get all players that match the query
    conn.close()
    # wrong player details will be redirected to 404 error page
    if not players:
        abort(404)

    # Organize players by team
    teams_data = {}
    for player in players:
        team_name = player[7]  # Assuming this is the Team name from your query
        if team_name not in teams_data:
            teams_data[team_name] = []
        teams_data[team_name].append(player)  # Add player to the respective team list
    return render_template("Players.html", teams_data=teams_data, query=query)


# add player route
@app.route('/Players', methods=['GET', 'POST'])
def Add_player():
    if request.method == 'POST':
        player_name = request.form['player_name']
    # Retrieve player name and role from the submitted form
    player_name = request.form['player_name']
    role = request.form['role']
    conn = get_db_connections()
    cur = conn.cursor()
    # Validate the inputs
    if len(player_name) > 40:
        flash("The player name is quite long")
    elif len(player_name) < 3:
        flash("Please enter a correct player name")
    elif len(role) > 15:
        flash("Please enter the correct role")
    elif len(role) < 5:
        flash("Please enter the correct role")
    else:
        flash('Player will be added after a profanity check.')
    # Insert the new player into the PendingPlayers table
    cur.execute("""
    INSERT INTO PendingPlayers (PlayerName, Role)
    VALUES (?, ?)
""", (player_name, role))
    conn.commit()
    return redirect(url_for('Players'))


# Route for Ranking Page
@app.route('/Ranking', defaults={'ranking_id': None})
def Ranking(ranking_id):
    format = request.args.get('format', 'ALL').upper()  # Default format is 'ALL'
    conn = get_db_connections()
    cur = conn.cursor()
    # Determine the SQL query based on the format
    if format == 'TEST':
        query = "SELECT Ranking, Player_Name, points, team, 'TEST' AS Format FROM TEST"
    elif format == 'T20':
        query = "SELECT Ranking, Player_Name, points, team, 'T20' AS Format FROM T20"
    elif format == 'ODI':
        query = "SELECT Ranking, Player_Name, points, team, 'ODI' AS Format FROM ODI"
    elif format == 'ALL':  # For 'ALL', combine results from all formats
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
    Crickets = cur.fetchall()
    conn.close()
    return render_template("Ranking.html", Crickets=Crickets)


@app.route('/Record')  # Define the route for the 'Record' page
def record():
    conn = get_db_connections()
    cur = conn.cursor()
    # Execute a SQL query to fetch distinct cricket team records
    # including test, ODI, and T20 statistics
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
    Crickets = cur.fetchall()
    conn.close()
    return render_template("Record.html", Crickets=Crickets)


# stats route
@app.route('/stats')  
def Statistics():
    conn = get_db_connections()  
    cur = conn.cursor()
    # Query to fetch team names and their respective information
    cur.execute("SELECT Team, image_url, Information FROM Statistics")
    teams_info = cur.fetchall()  # Use lowercase variable for consistency
    conn.close()
    return render_template("Stats.html", teams_info=teams_info)  # Pass lowercase variable


# Route for Review
@app.route('/Review')
def Review():
    conn = get_db_connections()
    cur = conn.cursor()
    # Fecth all details from reviews for Existing review function
    cur.execute("SELECT * FROM Review WHERE Is_Deleted = 0")
    Crickets = cur.fetchall()
    conn.close()
    return render_template("Review.html", Crickets=Crickets)


# App route for add review option
@app.route('/addreview', methods=['POST'])
def add_review():
    comments = request.form['Review']  # Retrieve the review comments from the form data
    rating = request.form['rating']     # Retrieve the rating value from the form data
    conn = get_db_connections()
    cur = conn.cursor()

    # Check the length of the comments
    if len(comments.split()) > 200:
        flash("The review should be below 200 words.")
        conn.close()
        return redirect('/404')  # Redirect back to reviews page
    # The revuew will be added to the Review table
    cur.execute("""INSERT INTO Review(comments, rating) VALUES (?, ?)""",
                (comments, rating))
    conn.commit()
    conn.close()
    return redirect('/Review')


# Run the website
if __name__ == "__main__":
    app.run(debug=True)