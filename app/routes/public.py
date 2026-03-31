from flask import render_template, redirect, url_for
from flask_login import current_user
from .blueprint import bp as app


@app.route("/", endpoint="home")
def home():
    try:
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return render_template("home.html")
    except Exception as e:
        # Keep same behavior: print and return minimal message
        print(f"An error occurred: {str(e)}")
        return "Welcome"
