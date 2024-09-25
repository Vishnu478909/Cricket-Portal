import re
import sqlite3
import time
from flask import Flask, render_template, request, redirect, session, url_for, flash,abort

app = Flask(__name__)  # Create Flask object
app.secret_key = 'your_secret_key'  # Secret key for session management
login_attempts = {}
DATABASE = 'Cricket.db.db'


def get_db_connections():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500  # Render 500 error page and return 500 status

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404  # Render 404 error page and return 404 status


# Home route
@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template("login.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash("Please enter both username and password.")

        # Rate limiting logic
        ip_address = request.remote_addr
        current_time = time.time()
        attempts = login_attempts.get(ip_address, [])

        # Clean up old attempts
        attempts = [t for t in attempts if current_time - t < 30]
        login_attempts[ip_address] = attempts

        if len(attempts) >= 5:
            flash("Too many login attempts. Please try again later in 30 seconds.")
            return render_template('login.html')

        # Proceed with login logic
        conn = get_db_connections()
        cur = conn.cursor()
        cur.execute("SELECT password FROM User WHERE username = ?", (username,))
        user = cur.fetchone()
        conn.close()

        if user and user[0] == password:  # Check plain text password
            session['username'] = username  # Store username in session
            return redirect(url_for('about'))
        else:
            flash("Invalid username or password.")
            login_attempts[ip_address].append(current_time)  # Record the failed attempt

    return render_template('login.html')  # Render login page for GET request



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Validate password and confirm password
        if password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for('register'))
        # The lenght of the password should be atleat 7 characters long
        elif len(password) < 7:
            flash("Password should be at least 7 characters long.")
            return redirect(url_for('register'))
        # The lenght of the username be minimum 5 character long
        elif len(username) < 5:
            flash("The username should be at least 5 characters long.")
            return redirect(url_for('register'))
        #the username should be below 10 characters
        elif len(username) > 10:
            flash("Username should be at most 10 characters.")
            return redirect(url_for('register'))
        # Password should contain one chracters
        elif not re.search(r'[A-Z]', password):
            flash("Password should contain at least one uppercase letter.")
            return redirect(url_for('register'))

        try:
            conn = get_db_connections()
            cur = conn.cursor()
            cur.execute("INSERT INTO User (username, password) VALUES (?, ?)",(username, password))
            conn.commit()
            conn.close()
            return redirect(url_for('registration_successful'))
        except sqlite3.IntegrityError:
            # This fucntion if the username is already stored in the database, it would prevent the 
            flash("Username already exists. Please choose a different username.")
            return redirect(url_for('register'))
    return render_template('register.html')  # Render registration page


@app.route('/logout')
def logout():
    session.clear()  # Clear all session data
    return redirect(url_for('login'))  # Redirect to the login page


@app.route('/registration_successful')
def registration_successful():
    return render_template('registeration.html')  # Render success page


@app.route('/about')
def about():
    return render_template("CricketPortal.html")  # Render Cricket portal page


@app.route('/Players')
def Players():
    conn = get_db_connections()  # Use your defined function here
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
    # Process the data into a dictionary format for easier use in the template
    teams_data = {}
    for row in players_by_team:
        team_name = row[0]
        player_data = row[1:]
        if team_name not in teams_data:
            teams_data[team_name] = []
        teams_data[team_name].append(player_data)
    return render_template("Players.html", teams_data=teams_data)


@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '')  # Get the search query
    conn = get_db_connections()
    cur = conn.cursor()
    cur.execute("""
        SELECT Player.PlayerName, Player.Role, Matches.Matches, Matches.Average, 
               Matches.Innings, Matches.Runs, Matches.Wickets, Matches.Team
        FROM Player
        INNER JOIN Matches ON Player.PlayerId = Matches.PlayerId
        WHERE Player.Verified = 1 AND Player.PlayerName LIKE ?
    """, ('%' + query + '%',))
    players = cur.fetchall()  # Get all players that match the query
    conn.close()
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


@app.route('/Players/<int:id>')
def player_detail(id):
    conn = get_db_connections()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            Player.PlayerName,
            Player.Role,
            Matches.Matches,
            Matches.Innings,
            Matches.Runs,
            Matches.Wickets,
            Matches.Average,
            Matches.Team_id
        FROM
            Player
        INNER JOIN
            Matches ON Player.PlayerId = Matches.PlayerId
        WHERE
            Player.PlayerId = ? AND Player.Verified = 1
    """, (id,))
    Player = cur.fetchone()
    conn.close()
    if Player:
        return render_template("Players.html", Player=Player)
    else:
        return render_template("404.html")


@app.route('/Players', methods=['GET', 'POST'])
def addplayer():
    if request.method == 'POST':
        player_name = request.form['player_name']
   # Retrieve player name and role from the submitted form
    player_name = request.form['player_name']
    role = request.form['role']
    # Establish a connection to the database
    conn = get_db_connections() 
    cur = conn.cursor()
    # Validate the length of the player name
    if len(player_name) > 40:
        flash("The player name is quite long")  # Error if too long
    elif len(player_name) < 3:
        flash("Please enter a correct player name")  # Error if characters are below 2 
    # Validate the length of the role
    elif len(role) > 10:
        flash("Please enter the correct role")  # Error if too long
    elif len(role) < 5:
        flash("Please enter the correct role")  # Error if too short
    else:
        flash('Player will be added after a profanity check.')  # Confirmation message
    # Insert the new player into the PendingPlayers table
    cur.execute("""
    INSERT INTO PendingPlayers (PlayerName, Role)
    VALUES (?, ?)
""", (player_name, role))
    # Commit the changes to the database
    conn.commit()
    return redirect(url_for('Players'))


@app.route('/verify_players')
def verify_players():
    conn = get_db_connections()
    cur = conn.cursor()
    cur.execute("SELECT * FROM PendingPlayers")  # Fetch all pending players
    players = cur.fetchall()
    conn.close()
    return render_template("verify_players.html", players=players)


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
    # Execute the query
    cur.execute(query)
    Crickets = cur.fetchall()
    conn.close()
    return render_template("Ranking.html", Crickets=Crickets)


@app.route('/Record')
def record():
    conn = get_db_connections()
    cur = conn.cursor()
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


@app.route('/Stats')
def Statistics():
    conn = get_db_connections()  # Establish DB connection
    cur = conn.cursor()
     # Query to fetch team names and their respective information
    cur.execute("SELECT Team, image_url, Information FROM Statistics")
    TeamsInfo = cur.fetchall()
    conn.close()  # Close the DB connection
    # Pass the results to the template
    return render_template("Stats.html", TeamsInfo=TeamsInfo)



@app.route('/Review')
def Review():
    conn = get_db_connections()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Review WHERE Is_Deleted = 0")
    Crickets = cur.fetchall()
    conn.close()
    return render_template("Review.html", Crickets=Crickets)


@app.route('/addreview', methods=['POST'])
def add_review():
    comments = request.form['Review']
    rating = request.form['rating']
    conn = get_db_connections()
    cur = conn.cursor()

    # Check the length of the comments
    if len(comments.split()) > 200:
        flash("The review should be below 200 words.")  # Use flash to show a message
        conn.close()
        return redirect('/404')  # Redirect back to reviews page

    cur.execute("""INSERT INTO Review(comments, rating) VALUES (?, ?)""",
                (comments, rating))
    conn.commit()
    conn.close()
    return redirect('/Review')  # Redirect to reviews page


# Run the website
if __name__ == "__main__":
    app.run(debug=True)  # Enable debug mode
