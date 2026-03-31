from datetime import datetime
from urllib.parse import urlparse as url_parse
from flask import render_template, redirect, url_for, flash, request, session
from flask_login import current_user, login_user, logout_user, login_required
from .blueprint import bp as app
from app import db
from app.forms import (
    BuyerRegistrationForm,
    SellerRegistrationForm,
    AdminRegistrationForm,
    LoginForm,
    ResetPasswordForm,
    RequestPasswordResetForm,
)
from app.models import User, Buyer, Seller, Admin
from app.my_email import send_login_details, send_password_reset_email
from .common import flash_message


@app.route("/login", methods=["GET", "POST"], endpoint="login")
def login():
    """Login logic"""
    try:
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user is None or not user.check_password(form.password.data):
                flash("Invalid username or password")
                return redirect(url_for("login"))
            if not user.is_active:
                flash("Your account is not active. Please contact support.")
                return redirect(url_for("home"))
            next_page = request.args.get("next")
            if not next_page or url_parse(next_page).netloc != "":
                next_page = url_for("dashboard")
            login_user(user, remember=form.remember_me.data)
            flash(f"Welcome {user.username}.")
            return redirect(next_page)
        return render_template("auth/login.html", title="Login", form=form)
    except Exception as e:
        flash("An error occurred. Please try again later.")
        return f"Error : {e}", 400


@app.route("/logout", endpoint="logout")
@login_required
def logout():
    """Logged in user can log out"""
    logout_user()
    return redirect(url_for("login"))


@app.route("/request-password-reset", methods=["GET", "POST"], endpoint="request_password_reset")
def request_password_reset():
    """Active user can request a password reset (email remains generic)."""
    try:
        if current_user.is_authenticated:
            if current_user.type == "buyer":
                return redirect(url_for("buyer_profile"))
            if current_user.type == "seller":
                return redirect(url_for("seller_profile"))
            if current_user.type == "admin":
                return redirect(url_for("admin_profile"))
        form = RequestPasswordResetForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user:
                send_password_reset_email(user)
            flash("Check your email for the instructions to reset your password")
            return redirect(url_for("login"))
        return render_template(
            "auth/register_anonymous_user.html",
            title="Request Password Reset",
            form=form,
        )
    except Exception as e:
        flash("An error occurred. Please try again later.")
        return f"Error : {e}", 400


@app.route("/reset-password/<token>", methods=["GET", "POST"], endpoint="reset_password")
def reset_password(token):
    """Time-bound link to reset password."""
    try:
        if current_user.is_authenticated:
            if current_user.type == "buyer":
                return redirect(url_for("buyer_profile"))
            if current_user.type == "seller":
                return redirect(url_for("seller_profile"))
            if current_user.type == "admin":
                return redirect(url_for("admin_profile"))
        user = User.verify_reset_password_token(token)
        if not user:
            return redirect(url_for("login"))
        form = ResetPasswordForm()
        if form.validate_on_submit():
            user.set_password(form.password.data)
            user.confirm_password = form.confirm_password.data
            db.session.commit()
            flash("Your password has been reset. Login to continue")
            return redirect(url_for("login"))
        return render_template(
            "auth/register_anonymous_user.html", title="Reset Password", form=form
        )
    except Exception as e:
        print(f"An error occurred: {e}")
        flash("An error occurred. Please try again later.")
        return redirect(url_for("login"))


@app.route("/register/buyer", methods=["GET", "POST"], endpoint="register_buyer")
def register_buyer():
    """Buyer registration logic"""
    try:
        if current_user.type == "admin":
            form = BuyerRegistrationForm()
            if form.validate_on_submit():
                buyer = Buyer(
                    first_name=form.first_name.data.title(),
                    last_name=form.last_name.data.title(),
                    username=form.username.data,
                    email=form.email.data,
                    phone_number=form.phone_number.data,
                    confirm_password=form.confirm_password.data,
                    current_residence=form.current_residence.data,
                )
                session["password"] = form.password.data
                user_password = session["password"]
                buyer.set_password(form.password.data)
                db.session.add(buyer)
                db.session.commit()
                send_login_details(buyer, user_password)
                del session["password"]
                flash(
                    f"Successfully registered Buyer {buyer.username}! Sent email for further guidance."
                )
                return redirect(url_for("dashboard"))
            return render_template(
                "auth/register_current_user.html",
                title="Register A Buyer",
                form=form,
            )
        else:
            return flash_message()
    except Exception as e:
        flash("An error occurred. Please try again later.")
        return f"Error : {e}", 400


@app.route("/register/seller", methods=["GET", "POST"], endpoint="register_seller")
@login_required
def register_seller():
    """Seller registration logic"""
    try:
        if current_user.type == "buyer":
            form = SellerRegistrationForm()
            if form.validate_on_submit():
                seller = Seller(
                    first_name=form.first_name.data,
                    last_name=form.last_name.data,
                    username=form.username.data,
                    email=form.email.data,
                    phone_number=form.phone_number.data,
                    current_residence=form.current_residence.data,
                    confirm_password=form.confirm_password.data,
                    buyer=current_user,
                )
                session["password"] = form.password.data
                user_password = session["password"]
                seller.set_password(form.password.data)
                db.session.add(seller)
                db.session.commit()
                send_login_details(seller, user_password)
                del session["password"]
                flash(
                    f"Successfully registered seller as {seller.username}! An email has been sent to them on the next steps to take."
                )
                return redirect(url_for("buyer_profile"))
        else:
            return flash_message()
        return render_template(
            "auth/register_current_user.html", title="Register Your Seller", form=form
        )
    except Exception as e:
        flash("An error occurred. Please try again later.")
        return f"Error : {e}", 400


@app.route("/register/admin", methods=["GET", "POST"], endpoint="register_admin")
@login_required
def register_admin():
    """Admin registration logic"""
    try:
        if current_user.department == "Super Admin":
            form = AdminRegistrationForm()
            if form.validate_on_submit():
                admin = Admin(
                    first_name=form.first_name.data,
                    last_name=form.last_name.data,
                    username=form.username.data,
                    email=form.email.data,
                    phone_number=form.phone_number.data,
                    current_residence=form.current_residence.data,
                    confirm_password=form.confirm_password.data,
                )
                session["password"] = form.password.data
                user_password = session["password"]
                admin.set_password(form.password.data)
                db.session.add(admin)
                db.session.commit()
                send_login_details(admin, user_password)
                del session["password"]
                flash(
                    f"Successfully registered your admin {admin.username}! An email has been sent to the admin on the next steps."
                )
                return redirect(url_for("all_admins"))
        else:
            flash("You do not have access to this page!")
            if current_user.type == "seller":
                return redirect(url_for("seller_profile"))
            if current_user.type == "buyer":
                return redirect(url_for("buyer_profile"))
        return render_template(
            "auth/register_current_user.html", title="Register An Admin", form=form
        )
    except Exception as e:
        flash(f"An error occurred during admin registration: {str(e)}")
        return "Error : {e}", 400
