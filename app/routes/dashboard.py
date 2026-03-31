from flask import redirect, url_for, flash
from flask_login import current_user
from .blueprint import bp as app


@app.route("/dashboard", endpoint="dashboard")
def dashboard():
    try:
        if current_user.type == "buyer":
            return redirect(url_for("buyer_profile"))
        if current_user.type == "seller":
            return redirect(url_for("seller_profile"))
        if current_user.type == "admin":
            return redirect(url_for("admin_profile"))
    except Exception as e:
        flash("An error occurred. Please try again later.")
        return f"Error : {e}", 400
