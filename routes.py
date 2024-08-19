from flask import Flask,request, render_template
import sqlite3

app = Flask(__name__)
Database = 'Cricket.db'

def query_db(query, params=()):
    conn = sqlite3.connect(Database)
    cur = conn.cursor()
    cur.execute(query, params)
    results = cur.fetchall()
    conn.close()
    return results

@app.route('/')
def home():
    return render_template("Cricketportal.html")

@app.route('/about')
def about():
    return render_template("about.Cricketportal")

@app.route('/all_Cricket')
def all_Cricket():
    Crickets = query_db("SELECT * FROM Team")
    return render_template("Cricketportal.html", Crickets=Crickets)

@app.route('/Cricket/<int:id>')
def cricket(id):
    Rankings = query_db("SELECT * FROM Team WHERE Team_id=?", (id,), one=True)
    return render_template("Cricketportal.html", Rankings=Rankings)

@app.route('/Players')
def players():
    Crickets = query_db("SELECT * FROM Player where name like ?")
    return render_template("Players.html", Crickets=Crickets)


@app.route('/Ranking')
def ranking():
    Crickets = query_db("SELECT * FROM Test")
    return render_template("Ranking.html", Crickets=Crickets)

@app.route('/Record')
def record():
    Crickets = query_db("SELECT * FROM Test")
    return render_template("Record.html" , Crickets=Crickets)


@app.route('/Stats')
def statistics():
    Crickets = query_db("SELECT * FROM Team")
    return render_template("Stats.html", Crickets=Crickets)

@app.route('/team')
def teams():
    Crickets = query_db("SELECT * FROM T20,ODI,Test")
    return render_template("Teams.html", Crickets=Crickets)
@app.route('/Review')
def Review():
    Crickets = query_db("Select * from review")
    return render_template("Review.html", Crickets=Crickets)

if __name__ == "__main__":
    app.run(debug=True)
