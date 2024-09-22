import re
from flask import Flask, render_template, request, redirect, session, url_for, flash
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Secret key for session management


# Error handler for internal server errors
@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html")  # Render 500 error page


# Error handler for page not found errors
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404  # Render 404 error page


# Home route
@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template("login.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':  # If the form is submitted
        username = request.form.get('username')
        password = request.form.get('password')

        if username and password:
            try:
                # Connect to the database
                conn = sqlite3.connect('Cricket.db.db')
                cur = conn.cursor()
                # Check if the username exists and get the password
                cur.execute("SELECT password FROM User WHERE username = ?", (username,))
                user = cur.fetchone()
                conn.close()

                # Validate the user credentials
                if user and user[0] == password:
                    session['username'] = username  # Store username in session
                    return redirect(url_for('about'))  # Redirect to cricket portal page if login succeded
            except Exception as e:
                print(f"Error: {e}")
                flash(" Invalid password or username")  # Flash an error message
                return redirect(url_for('login'))  # Redirect back to login
    return render_template('login.html')  # Render login page


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':  # If the form is submitted
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Validate password and confirm password
        if password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for('register'))

        elif len(password) < 7:
            flash("Password should be at least 7 characters long.")
            return redirect(url_for('register'))

        elif not re.search(r'[A-Z]', password):
            flash("Password should contain at least one uppercase letter.")
            return redirect(url_for('register'))

        try:
            # Connect to the database
            conn = sqlite3.connect('Cricket.db.db')
            cur = conn.cursor()
            # Insert new user into the User table
            cur.execute("INSERT INTO User (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            return redirect(url_for('registartionsucessfull'))  # Redirect to success page, if the registration was sucessfull.
        except sqlite3.IntegrityError:
            flash("Username already exists. Please choose a different username.")
            return redirect(url_for('register'))


    return render_template('register.html')  # Render registration page


# Logout route
@app.route('/logout')
def logout():
    session.clear()  # Clear all session data
    return redirect(url_for('login'))  # Redirect to the login page


# Registration success route
@app.route('/registartionsucessfull')
def registartionsucessfull():
    return render_template('registeration.html')  # Render success page


# About route
@app.route('/about')
def about():
    return render_template("CricketPortal.html")  # Render Cricket portal page


# Players route
@app.route('/Players')
def Players():
    conn = sqlite3.connect('Cricket.db.db')
    cur = conn.cursor()
    # Fetch results from players and matches table
    cur.execute("""
        SELECT
            Player.PlayerName,
            Player.Role,
            Matches.Matches,
            Matches.Average,
            Matches.Innings,
            Matches.Runs,
            Matches.Wickets,
            Matches.Team
        FROM
            Player
        INNER JOIN
            Matches
        ON
            Player.PlayerId = Matches.PlayerId
        WHERE
            Player.Verified = 1;  -- Only select approved players
    """)
    Crickets = cur.fetchall()  # Fetch all results
    return render_template("Players.html", Crickets=Crickets)  # Render players page


# Add player route
@app.route('/player', methods=['GET', 'POST'])
def addplayer():
    conn = sqlite3.connect('Cricket.db.db')
    cur = conn.cursor()

    if request.method == 'POST':  # If the form is submitted
        player_name = request.form['player_name']
        role = request.form['role']

        # Insert the new player into the PendingPlayers table
        cur.execute("""
            INSERT INTO PendingPlayers (PlayerName, Role)
            VALUES (?, ?)
        """, (player_name, role))

        conn.commit()
        conn.close()
        flash('Player will be added after profanity check.')  # Flash message to conevy that player will be added after manual check
        return redirect(url_for('Players'))  # Redirect to Players page


# Verify players route
@app.route('/verify_players')
def verify_players():
    conn = sqlite3.connect('Cricket.db.db')
    cur = conn.cursor()

    cur.execute("SELECT * FROM Player")  # Fetch all players
    player = cur.fetchall()

    return render_template("verify_players.html", players=player)  # Render verify players page


# Approve player route
@app.route('/approve_player/<int:player_id>')
def approve_player(player_id):
    conn = sqlite3.connect('Cricket.db.db')
    cur = conn.cursor()

    # Retrieve the player details from PendingPlayers
    cur.execute("SELECT PlayerName, Role FROM PendingPlayers WHERE id=?", (player_id,))
    player = cur.fetchone()

    if player:
        player_name, role = player
        # Insert the player into the Player table and set Verified to 1
        cur.execute("""
            INSERT INTO Player (PlayerName, Role, Verified)
            VALUES (?, ?, 1)
        """, (player_name, role))

        # Delete the player from PendingPlayers
        cur.execute("DELETE FROM PendingPlayers WHERE id=?", (player_id,))

    conn.commit()
    conn.close()

    return redirect(url_for('verify_players'))  # Redirect back to verify players


@app.route('/Ranking', defaults={'ranking_id': None})
@app.route('/Ranking/<int:ranking_id>')
def Ranking(ranking_id):
    format = request.args.get('format', 'ALL').upper()  # Get format from query parameters
    conn = sqlite3.connect('Cricket.db.db')
    cur = conn.cursor()

    # Selecting data based on the format
    if format == 'TEST':
        query = "SELECT Ranking, Player_Name, points, team, 'TEST' AS Format FROM TEST"
    elif format == 'T20':
        query = "SELECT Ranking, Player_Name, points, team, 'T20' AS Format FROM T20"
    elif format == 'ODI':
        query = "SELECT Ranking, Player_Name, points, team, 'ODI' AS Format FROM ODI"
    else:
        query = """
            SELECT Ranking, Player_Name, points, team, 'T20' AS Format FROM T20
            UNION
            SELECT Ranking, Player_Name, points, team, 'ODI' AS Format FROM ODI
            UNION
            SELECT Ranking, Player_Name, points, team, 'TEST' AS Format FROM TEST
        """  # Combine all ranking data

    cur.execute(query)
    Crickets = cur.fetchall()  # Fetch ranking data
    conn.close()

    # If a ranking ID is provided, filter the results
    if ranking_id is not None:
        Crickets = [player for player in Crickets if player[0] == ranking_id]
        if not Crickets:  # If no matching player is found
            return render_template('404.html')  # Render a 404 page or an error message

    return render_template("Ranking.html", Crickets=Crickets)  # Render rankings page


# Record route
@app.route('/Record', defaults={'record_id': None})
@app.route('/Record/<int:record_id>')
def record(record_id):
    conn = sqlite3.connect('Cricket.db.db')
    cur = conn.cursor()
    # Fetch results from three tables data tables results from records which was sepreated on the basis on diffrent format and used join function to combine records.
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
    Crickets = cur.fetchall()  # Fetch all results
    return render_template("Record.html", Crickets=Crickets)  # Render records page


# Statistics route
@app.route('/Stats')
def Statistics():
    # Connect to the database
    conn = sqlite3.connect('Cricket.db.db')
    cur = conn.cursor()

    # Execute the query to get team data with image paths
    cur.execute("SELECT Information FROM Statistics")
    Crickets = cur.fetchall()  # Fetch all results

    # Close the database connection
    conn.close()

    # Render the Stats.html template with the Crickets data
    return render_template("Stats.html", Crickets=Crickets)


# Review route
@app.route('/Review')
def Review():
    conn = sqlite3.connect('Cricket.db.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM Review WHERE Is_Deleted = 0")  # Fetch active reviews
    Crickets = cur.fetchall()  # Fetch all results
    return render_template("Review.html", Crickets=Crickets)  # Render reviews page


# Add review route
@app.route('/addreview', methods=['POST'])
def add_review():
    comments = request.form['Review']
    rating = request.form['rating']
    conn = sqlite3.connect('Cricket.db.db')
    cur = conn.cursor()
    # Insert  review into the Review table
    cur.execute("INSERT INTO Review(comments, rating) VALUES (?, ?)", (comments, rating))
    conn.commit()
    conn.close()
    return redirect('/Review')  # Redirect to reviews page


# Run the website
if __name__ == "__main__":
    app.run(debug=True)  # Enable debug mode