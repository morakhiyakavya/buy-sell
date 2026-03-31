from flask import flash, redirect, url_for
from flask_login import current_user


def flash_message():
    """Base-level unauthorized message + redirect, reused across routes."""
    try:
        if current_user.is_authenticated:
            flash(f"As a {current_user.type} you are not authorized to view the page.")
            return redirect(url_for("dashboard"))
        else:
            flash("You are not authorized to view the page. Please Login first.")
            return redirect(url_for("login"))
    except Exception:
        flash("An error occurred while processing your request.")
        return redirect(url_for("dashboard"))

