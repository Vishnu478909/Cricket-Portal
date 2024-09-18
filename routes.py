import re
from flask import Flask, render_template, request , redirect , session , url_for
import sqlite3


app = Flask(__name__)
app.secret_key= 'your_secret_key'



@app.errorhandler(500)
def internal_server_error(e):
   return render_template("500.html")

@app.errorhandler(404)
def page_not_found(e):
    return render_template ("404.html"),404



@app.route('/', methods =['GET', 'POST'])
def home():
  if 'username' not in session:
    return redirect (url_for('login'))
  return render_template("Cricketportal.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username and password:
            try:
                conn = sqlite3.connect('Cricket.db.db')
                cur = conn.cursor()
                cur.execute("SELECT password FROM User WHERE username = ?", (username,))
                user = cur.fetchone()
                conn.close()


                if user and user[0] == password:
                    session['username'] = username
                    return redirect(url_for('home'))
                else:
                    return "Invalid username or password."
            except Exception as e:
                print(f"Error: {e}")
                return "An error occurred. Please try again later."
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    error_message = None # Intilisase error page
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            return "Passwords do not match."
        elif len(password) < 7:
           return (" Password should be atleast 7 characters long")
        elif not re.search(r'[A-Z]',password):
           return(" Password should atleast one uppecase letter")

        try:
            conn = sqlite3.connect('Cricket.db.db')
            cur = conn.cursor()
            cur.execute("INSERT INTO User (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            return redirect(url_for('registartionsucessfull'))
        except sqlite3.IntegrityError:
            return "Username already exists. Please choose a different username."
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return "An error occurred. Please try again later."

    return render_template('register.html')


@app.route (('/logout'))
def  logout():
   session.pop ('username', None) # Remove the username from the session
   return redirect(url_for('logout')) # redirect them to the login page

@app.route(('/registartionsucessfull'))
def registartionsucessfull():
   return render_template('registeration.html')

@app.route('/about')
def about():
  return render_template("CricketPortal.html")


@app.route('/Players')
def Players():
  conn = sqlite3.connect('Cricket.db.db')
  cur = conn.cursor()
  cur.execute("""SELECT 
    Player.PlayerId, 
    Player.PlayerName, 
    Player."Role ",
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
    Player.PlayerId = Matches.PlayerId;
""")
  Crickets= cur.fetchall()
  return render_template("Players.html",Crickets=Crickets)

@app.route('/Ranking')
def Ranking():
    format= request.args.get ('format','ALL').upper()
    conn = sqlite3.connect('Cricket.db.db')
    cur = conn.cursor()
    if format == 'TEST':
      query = ("""Select Ranking, Player_Name, points, team, 'TEST' AS Format FROM TEST""")
    elif  format == 'T20':
      query = ("""  SELECT Ranking, Player_Name, points, team,  'T20' AS Format FROM T20""")
    elif format == 'ODI':
      query = ("""SELECT Ranking, Player_Name, points,team, 'ODI' AS Format FROM ODI""")
    else:
      query=("""
        SELECT Ranking, Player_Name, points, team, 'T20' AS Format FROM T20
        UNION
        SELECT Ranking, Player_Name, points, team, 'ODI' AS Format FROM ODI
        UNION
        SELECT Ranking, Player_Name, points, team, 'TEST' AS Format FROM TEST
    """)
    cur.execute(query)
    Crickets = cur.fetchall()
    conn.close()
    return render_template("Ranking.html", Crickets=Crickets)


@app.route('/Record')
def Record():
  conn = sqlite3.connect('Cricket.db.db')
  cur = conn.cursor()
  cur.execute("SELECT DISTINCT tr.team AS country,tr.record_test,o.record_odi, t.record_value FROM test_records tr LEFT JOIN odi_records o ON tr.teamid = o.teamid LEFT JOIN t20_records t ON tr.team = t.team ORDER By  tr.team;",)
  Crickets = cur.fetchall()
  return render_template("Record.html",Crickets=Crickets)

@app.route('/Stats')
def Statistics():
  conn = sqlite3.connect('Cricket.db.db')
  cur = conn.cursor()
  cur.execute("SELECT Information FROM Statistics ")
  Crickets = cur.fetchall()
  return render_template("Stats.html",Crickets=Crickets)




@app.route('/Review')
def Review():
  conn = sqlite3.connect('Cricket.db.db')
  cur = conn.cursor()
  cur.execute("Select * from Review where Is_Deleted = 0")
  Crickets = cur.fetchall()
  return render_template ("Review.html", Crickets=Crickets)

@app.route('/addreview',methods = ['POST'])
def add_review():
  comments = request.form['Review']
  rating = request.form['rating']
  conn = sqlite3.connect('Cricket.db.db')
  cur = conn.cursor()
  cur.execute (" INSERT INTO  Review(comments, rating) VALUES (?,?)", (comments, rating))
  conn.commit()
  conn.close()
  return redirect('/Review')

@app.route('/deletereview',methods= ['POST'])
def delete_review():
  # print for debugging purposes 
  print("form keys:", request.form.keys())
  print("form data:", request.form)

  review_id = request.form ['review_id']
 
  if review_id is None :
   return redirect ('/404/missing_review_review_id')
  
  try:
    review_id = int(review_id)
  except:
    return redirect ('/404/invalid_review_review_id')
  
 
  conn = sqlite3.connect('Cricket.db.db')
  cur= conn.cursor()
  cur.execute ("SELECT COUNT(*) FROM Review WHERE Id = ? AND Is_Deleted = 0", (review_id,))
  if cur.fetchone() [ 0] == 0:
    conn.close()
    return redirect('/404')

  cur.execute("UPDATE Review SET Is_Deleted = 1 WHERE Id = ?", (review_id,))
  conn.commit()
  conn.close()

  return redirect('/Review')

if __name__ == "__main__":
  app.run(debug=True)
