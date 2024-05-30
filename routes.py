from flask import Flask, render_template
import sqlite3

app = Flask(__name__)
DATABASE = 'Cricket.db'

def query_db(query, params=()):
    conn = sqlite3.connect(DATABASE)
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
    cricket = query_db("SELECT * FROM Team WHERE Team_id=?", (id,), one=True)
    return render_template("Cricketportal.html", Crickets=[cricket])

@app.route('/players')
def players():
    Crickets = query_db("SELECT * FROM Player")
    return render_template("Players.html", Crickets=Crickets)

@app.route('/ranking')
def ranking():
    Crickets = query_db("SELECT * FROM Test")
    return render_template("Ranking.html", Crickets=Crickets)

@app.route('/statistics')
def statistics():
    Crickets = query_db("SELECT * FROM odi")
    return render_template("Stats.html", Crickets=Crickets)

@app.route('/teams')
def teams():
    Crickets = query_db("SELECT * FROM T20,ODI,Test")
    return render_template("Teams.html", Crickets=Crickets)

if __name__ == "__main__":
    app.run(debug=True)
