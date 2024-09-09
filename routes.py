from flask import Flask, render_template, request , redirect , session , url_for
import sqlite3
import hashlib


app = Flask(__name__)
app.secret_key= 'your_secret_key'



@app.errorhandler(500)
def internal_server_error(e):
   return render_template("500.html")

@app.errorhandler(404)
def page_not_found(e):
    return render_template ("404.html"),404

def hash_password(password):
  return hashlib.sha256(password.encode()).hexdigest()

@app.route('/', methods =['GET', 'POST'])
def home():
  if 'username' not in session:
    return redirect (url_for('login'))
  return render_template("Cricketportal.html")

@app.route('/login', methods=['GET', 'POST'])
def login ():
  username = None
  if request.method == 'POST':
    username = request.form.get('username')
    password = request.form.get('password')
  try:
            conn = sqlite3.connect('Cricket.db.db')
            cur = conn.cursor()
            cur.execute("SELECT password FROM User WHERE username = ?", (username,))
            user = cur.fetchone()
            conn.close()

            if user and user[0] == hash_password(password):
                session['username'] = username
                return redirect(url_for('/login'))

  except Exception as e:
            print(f"Error: {e}")
 


  return render_template ('login.html')

@app.route ('/register', methods = ['GET', 'POST'])
def register():
  if request.method =='POST':
   username = request.form ['username']

   password = request.form ['password']

   hashed_password= hash_password(password)
 
  conn = sqlite3.connect ('Cricket.db.db')
  cur = conn.cursor ()
  cur.execute("INSERT INTO User (username, password) VALUES (?, ?)", (username, hashed_password))
  conn.commit()
  conn.close()



  return render_template('register.html')





@app.route('/about')
def about():
  return render_template("CricketPortal.html")


@app.route('/Players')
def Players():
  conn = sqlite3.connect('Cricket.db.db')
  cur = conn.cursor()
  cur.execute("SELECT * FROM Player")
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
