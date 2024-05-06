from flask import Flask, render_template
import sqlite3

app = Flask(__name__)


@app.route('/')
def home():
  return render_template("Cricketportal.html")


@app.route('/about')
def about():
  return render_template("about.Cricketportal")


@app.route('/all_Cricket')
def all_pizzas():
  conn = sqlite3.connect('Cricket.db')
  cur = conn.cursor()
  cur.execute("SELECT * FROM Team")
  Crickets = cur.fetchall()
  return render_template("Cricketportal.html", Crickets=Crickets)


@app.route('/Cricket/<int:id>')
def pizza(id):
  conn = sqlite3.connect('Cricket.db')
  cur = conn.cursor()
  cur.execute ("SELECT * FROM Team WHERE Team_id=?, (id, )")
  pizza = cur.fetchone()
  return render_template("Cricketportal.html", pizza=pizza)


if __name__ == "__main__":
  app.run(debug=True)
