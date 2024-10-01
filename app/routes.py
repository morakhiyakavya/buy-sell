import ast
from datetime import datetime
import random
from random import randint
# from cryptography.fernet import Fernet
import json
import os
import re
import sqlite3
import string
from flask import (
    render_template,
    redirect,
    url_for,
    flash,
    request,
    session,
    jsonify,
    send_file,
    abort,
)
from flask_login import current_user, login_user, logout_user, login_required
from flask_socketio import emit, join_room
import socketio
from app.forms import (
    BuyerRegistrationForm,
    SellerRegistrationForm,
    AdminRegistrationForm,
    LoginForm,
    ResetPasswordForm,
    RequestPasswordResetForm,
    VerifyForm,
    EmailForm,
    EditEmailForm,
    EditPhoneForm,
    EditUsernameForm,
    ProductForm,
    PanForm,
    DetailForm,
    AllotmentForm,
)
from app.models import (
    TransactionPan,
    User,
    Buyer,
    Seller,
    Admin,
    Email,
    # Product,
    Transaction,
    Pan,
    Details,
    IPO,
)
from app.email import send_user_private_email, send_login_details
from app.email import send_password_reset_email, request_account_deletion
from werkzeug.urls import url_parse
from werkzeug.utils import secure_filename

# Check and Write Allotment in Excel.
from app.allotment import scrape_data_from_websites, driver_path, IPODetailsScraper
from app.excel import process_excel_data, write_in_excel, process_excel

from app import app, db, socketio
from sqlalchemy.exc import IntegrityError
from sqlalchemy import inspect, MetaData

@app.route('/healthz', methods=['GET'])
def checkup():
    return jsonify(status='healthy', message='The server is running smoothly!')

# =========================================
# USER AUTHENTICATION
# =========================================


# Checked
def flash_message():  # An base level error message function
    try:
        if current_user.is_authenticated:
            flash(f"As a {current_user.type} you are not authorized to view the page.")
            return redirect(url_for("dashboard"))
        else:
            flash("You are not authorized to view the page. Please Login first.")
            return redirect(url_for("login"))
    except Exception as e:
        flash("An error occurred while processing your request.")
        return redirect(url_for("dashboard"))


# Checked
@app.route("/")
def home():
    try:
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return render_template("home.html")
    except Exception as e:
        # Handle the exception here
        print(f"An error occurred: {str(e)}")


# @app.route("/all-links")
# @login_required
# def all_links():
#     if current_user.is_authenticated:
#         urls = {}
#         with app.test_request_context():
#             for rule in app.url_map.iter_rules():
#                 # Skip endpoints that require arguments.
#                 if "GET" in rule.methods and len(rule.arguments) == 0:
#                     try:
#                         urls[rule.endpoint] = url_for(rule.endpoint)
#                     except Exception as e:
#                         # Handle or log the error for endpoints that still can't be built
#                         print(f"Error building URL for endpoint '{rule.endpoint}': {e}")
#         return render_template("all_links.html", urls=urls)


# @app.route("/allotment_file")
# def allotment_file():
#     file_path = "C:\\Users\\kavya\\Documents\\My_programming\\buy-sell\\myflaskapp\\app\\upload_folder\\ENSER_COM_-_PANCARD_-_Copy.xlsx"
#     return send_file(file_path, as_attachment=True)


# Checked
@app.route("/dashboard")
def dashboard():
    try:
        if current_user.type == "buyer":
            return redirect(url_for("buyer_profile"))
        if current_user.type == "seller":
            return redirect(url_for("seller_profile"))
        if current_user.type == "admin":
            return redirect(url_for("admin_profile"))
    except Exception as e:
        # Handle the exception here
        flash("An error occurred. Please try again later.")
        return f"Error : {e}", 400


# Login
# Checked
@app.route("/login", methods=["GET", "POST"])
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
        # Handle the exception here
        flash("An error occurred. Please try again later.")
        return f"Error : {e}", 400


# Logout
# Checked
@app.route("/logout")
@login_required
def logout():
    """Logged in user can log out"""
    logout_user()
    return redirect(url_for("login"))


# Request password reset


# Not Checked for Buyer and Seller
@app.route("/request-password-reset", methods=["GET", "POST"])
def request_password_reset():
    """
    Registerd user can request for a password reset
    If not registered, the application will not tell the anonymous user why not
    """
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
                # Send user an email
                send_password_reset_email(user)
            # Conceal database information by giving general information
            flash("Check your email for the instructions to reset your password")
            return redirect(url_for("login"))
        return render_template(
            "auth/register_anonymous_user.html",
            title="Request Password Reset",
            form=form,
        )
    except Exception as e:
        # Handle the exception here
        flash("An error occurred. Please try again later.")
        return f"Error : {e}", 400


# Reset password
# Not Checked for Buyer and Seller
@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """
    Time-bound link to reset password requested by an active user sent to their inbox
    """
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
        # Handle the exception here
        print(f"An error occurred: {e}")
        # Optionally, you can redirect to an error page or display a flash message
        flash("An error occurred. Please try again later.")
        return redirect(url_for("login"))


# Buyer registration
# Checked
# Potential Updates : We might need to give other field to be filled by buyer and might send direct otp or link to user.
@app.route("/register/buyer", methods=["GET", "POST"])
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

                # Show actual seller password in registration email
                session["password"] = form.password.data
                user_password = session["password"]

                # Update database
                buyer.set_password(form.password.data)
                # buyer.generate_encryption_key()
                db.session.add(buyer)
                db.session.commit()

                # Send buyer and email with login credentials
                send_login_details(buyer, user_password)

                # Delete seller password session
                del session["password"]

                flash(
                    f"Successfully registered Buyer {buyer.username}! "
                    "Sent email for further guidance."
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
        # Handle the exception here
        flash("An error occurred. Please try again later.")
        return f"Error : {e}", 400


# seller registration
# Checked
# Potential Update : We need to check weather there is same username or not.
@app.route("/register/seller", methods=["GET", "POST"])
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

                # Show actual teacher password in registration email
                session["password"] = form.password.data
                user_password = session["password"]

                # Update database
                seller.set_password(form.password.data)
                # seller.generate_encryption_key()
                db.session.add(seller)
                db.session.commit()

                # Send seller an email with login credentials
                send_login_details(seller, user_password)

                # Delete seller password session
                del session["password"]

                flash(
                    f"Successfully registered seller as {seller.username}! "
                    "An email has been sent to them on the next steps to take."
                )
                return redirect(url_for("buyer_profile"))
        else:
            return flash_message()
        return render_template(
            "auth/register_current_user.html", title="Register Your Seller", form=form
        )
    except Exception as e:
        # Handle the exception here
        flash("An error occurred. Please try again later.")
        return f"Error : {e}", 400


# Admin registration
# Checked
@app.route("/register/admin", methods=["GET", "POST"])
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

                # Show actual admin password in registration email
                session["password"] = form.password.data
                user_password = session["password"]

                # Update the database
                admin.set_password(form.password.data)
                # admin.generate_encryption_key()
                db.session.add(admin)
                db.session.commit()

                # Send admin an email with login credentials
                send_login_details(admin, user_password)

                # Delete seller password session
                del session["password"]

                flash(
                    f"Successfully registered your admin {admin.username}! "
                    "An email has been sent to the admin on the next steps."
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


# =========================================
# END OF USER AUTHENTICATION
# =========================================


# =========================================
# AUTHENTICATED USERS
# =========================================

# ==========
# DASHBOARD
# ==========


# --------------------------------------
# Admin profile
# --------------------------------------


# Admin profile
# Checked
@app.route("/admin/profile")
@login_required
def admin_profile():
    try:
        if current_user.type == "admin":
            return render_template("admin/profile.html", title="Admin Profile")
        else:
            return flash_message()
    except Exception as e:
        # Handle the exception here
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


# Compose direct email to admin
# Not Checked
@app.route(
    "/dashboard/compose-direct-email-to-an-admin/<email>", methods=["GET", "POST"]
)
@login_required
def compose_direct_email_to_admin(email):
    """Write email to individual admin"""
    try:
        # Get the admin
        admin = Admin.query.filter_by(email=email).first()
        admin_username = admin.email.split("@")[0].capitalize()
        session["admin_email"] = admin.email
        session["admin_first_name"] = admin.first_name

        form = EmailForm()
        form.signature.choices = [
            (current_user.first_name.capitalize(), current_user.first_name.capitalize())
        ]
        if form.validate_on_submit():
            email = Email(
                subject=form.subject.data,
                body=form.body.data,
                closing=form.closing.data,
                signature=form.signature.data,
                bulk="Admin Email",
                author=current_user,
            )
            db.session.add(email)
            db.session.commit()
            flash(f"Sample private email to {admin_username} saved")
            return redirect(url_for("emails_to_individual_admins"))
        return render_template(
            "admin/email_admin.html",
            title="Compose Private Email",
            form=form,
            admin=admin,
        )
    except Exception as e:
        flash(f"Error composing email: {str(e)}")
        return redirect(url_for("emails_to_individual_admins"))


# List of emails sent out to individual admin
# Not Checked
@app.route("/dashboard/emails-to-individual-admins")
@login_required
def emails_to_individual_admins():
    """Emails sent out to individual admins"""
    try:
        emails_sent_to_individual_admins = Email.query.filter_by(
            bulk="Admin Email"
        ).all()
        emails = len(emails_sent_to_individual_admins)
        return render_template(
            "admin/individual_admin_email.html",
            title="Emails Sent To Individual Admins",
            emails_sent_to_individual_admins=emails_sent_to_individual_admins,
            emails=emails,
        )
    except Exception as e:
        # Handle the exception or log the error
        print(f"Error occurred: {e}")
        # Return an appropriate response or redirect to an error page
        return f"Error : {e}", 400


# List all admins
# Not Checked
@app.route("/dashboard/all-admins")
@login_required
def all_admins():
    try:
        if current_user.type == "admin":
            admins = Admin.query.all()
            all_registered_admins = len(admins)
            return render_template(
                "admin/all_admins.html",
                title="All Admins",
                admins=admins,
                all_registered_admins=all_registered_admins,
            )
        else:
            return flash_message()
    except Exception as e:
        # Handle the exception here
        print(f"An error occurred: {e}")
        # You can also log the error or perform any other necessary actions
        return f"Error : {e}", 400


# Deactivate admin
# Not Checked
@app.route("/dashboard/deactivate-admin/<username>")
@login_required
def deactivate_admin(username):
    try:
        if current_user.department == "Super Admin":
            admin = Admin.query.filter_by(username=username).first_or_404()
            admin.active = False
            db.session.add(admin)
            db.session.commit()
            flash(f"{admin.username} has been deactivated as an admin")
            return redirect(url_for("all_admins"))
        else:
            return flash_message()
    except Exception as e:
        # Handle the exception here
        # You can log the error or perform any other necessary actions
        flash("An error occurred while deactivating the admin")
        print(f"An error occurred: {e}")
        return redirect(url_for("all_admins"))


# Reactivate admin
# Not Checked
@app.route("/dashboard/reactivate-admin/<username>")
@login_required
def reactivate_admin(username):
    try:
        if current_user.department == "Super Admin":
            admin = Admin.query.filter_by(username=username).first_or_404()
            admin.active = True
            db.session.add(admin)
            db.session.commit()
            flash(f"{admin.username} has been reactivated as an admin")
            return redirect(url_for("all_admins"))
        else:
            return flash_message()
    except Exception as e:
        # Handle the exception here
        flash("An error occurred while reactivating the admin")
        print(f"An error occurred: {e}")
        return redirect(url_for("all_admins"))


# Delete admin
# Not Checked
@app.route("/dashboard/delete-admin/<username>")
@login_required
def delete_admin(username):
    try:
        if current_user.department == "Super Admin" or current_user.username == username:
            admin = Admin.query.filter_by(username=username).first_or_404()
            db.session.delete(admin)
            db.session.commit()
            flash(f"{admin.username} has been deleted as an admin")
            return redirect(url_for("all_admins"))
        else:
            return flash_message()
    except Exception as e:
        # Handle the exception here
        flash("An error occurred while deleting the admin")
        print(f"An error occurred: {e}")
        return redirect(url_for("all_admins"))


# Send email to individual admin
# Not Checked
@app.route("/send-email-to-admin/<id>")
@login_required
def send_admin_email(id):
    try:
        """Send email to admin from the database"""
        email = Email.query.filter_by(id=id).first()
        admin_email = session["admin_email"]
        admin_first_name = session["admin_first_name"]

        # Update db so that the email is not sent again
        email.allow = True
        db.session.add(email)
        db.session.commit()

        # Send email to user
        send_user_private_email(email, admin_email, admin_first_name)

        # Notify user that email has been sent
        flash(f"Email successfully sent to the teacher {admin_email}")
        del session["admin_email"]
        del session["admin_first_name"]
        return redirect(url_for("emails_to_individual_admins"))
    except Exception as e:
        flash(f"Error sending email: {str(e)}")
        return redirect(url_for("emails_to_individual_admins"))


# Edit sample email
# Not Checked
@app.route("/edit-admin-email/<id>", methods=["GET", "POST"])
@login_required
def edit_admin_email(id):
    """Edit email to admin from the database"""
    try:
        email = Email.query.filter_by(id=id).first()
        form = EmailForm()
        form.signature.choices = [
            (current_user.first_name.capitalize(), current_user.first_name.capitalize())
        ]
        if form.validate_on_submit():
            email.subject = form.subject.data
            email.body = form.body.data
            email.closing = form.closing.data
            email.signature = form.signature.data
            db.session.commit()
            flash("Your changes have been saved")
            return redirect(url_for("emails_to_individual_admins"))
        if request.method == "GET":
            form.subject.data = email.subject
            form.body.data = email.body
            form.signature.data = email.signature
        return render_template(
            "admin/edit_email.html", title="Edit Sample Email", form=form
        )
    except Exception as e:
        flash("An error occurred while editing the email.")
        print(f"An error occurred: {e}")
        return redirect(url_for("emails_to_individual_admins"))


# Delete email from database
# Not Checked
@app.route("/delete-email-sent-to-a-admin/<id>")
@login_required
def delete_admin_email(id):
    """Delete email to user from the database"""
    try:
        email = Email.query.filter_by(id=id).first()
        db.session.delete(email)
        db.session.commit()
        flash("Email successfully deleted")
        del session["admin_email"]
        del session["admin_first_name"]
        return redirect(url_for("emails_to_individual_admins"))
    except Exception as e:
        flash("An error occurred while deleting the email")
        print(f"Error: {e}")
        return redirect(url_for("emails_to_individual_admins"))


# --------------------------------------
# End of admin profile
# --------------------------------------


# --------------------------------------
# All buyer
# --------------------------------------


# Buyer profile
# Checked
@app.route("/buyer/profile")
@login_required
def buyer_profile():
    try:
        if current_user.type == "buyer":
            return render_template("buyer/profile.html", title="Buyer Profile")
        else:
            return flash_message()
    except Exception as e:
        # Handle the exception here
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


# Deactivate own account
# Not Checked
@app.route("/buyer/deactivate-account")
@login_required
def buyer_deactivate_account():
    try:
        # Get current user
        buyer = Buyer.query.filter_by(username=current_user.username).first()

        # Send email to all admins about the request to delete account
        admins = Admin.query.all()
        for admin in admins:
            request_account_deletion(admin, buyer)

        flash(
            "Your request has been sent to the admins."
            " You will receive an email notification if approved"
        )
        return redirect(url_for("buyer_profile"))
    except Exception as e:
        flash(
            "An error occurred while deactivating your account. Please try again later."
        )
        print(f"An error occurred: {e}")
        return redirect(url_for("buyer_profile"))


# Compose direct email to buyer
# Not Checked
@app.route(
    "/dashboard/compose-direct-email-to-a-buyer/<email>", methods=["GET", "POST"]
)
@login_required
def compose_direct_email_to_buyer(email):
    """Write email to individual buyer"""
    try:
        # Get the buyer
        buyer = Buyer.query.filter_by(email=email).first()
        buyer_username = buyer.email.split("@")[0].capitalize()
        session["buyer_email"] = buyer.email
        session["buyer_first_name"] = buyer.first_name

        form = EmailForm()
        form.signature.choices = [
            (current_user.first_name.capitalize(), current_user.first_name.capitalize())
        ]
        if form.validate_on_submit():
            email = Email(
                subject=form.subject.data,
                body=form.body.data,
                closing=form.closing.data,
                signature=form.signature.data,
                bulk="buyer Email",
                author=current_user,
            )
            db.session.add(email)
            db.session.commit()
            flash(f"Sample private email to {buyer_username} saved")
            return redirect(url_for("emails_to_individual_buyers"))
        return render_template(
            "admin/email_buyer.html",
            title="Compose Private Email",
            form=form,
            buyer=buyer,
        )
    except Exception as e:
        flash(f"An error occurred: {str(e)}")
        print(f"An error occurred: {e}")
        return redirect(url_for("emails_to_individual_buyers"))


# List of emails sent out to individual buyer
# Not Checked
@app.route("/dashboard/emails-to-individual-buyers")
@login_required
def emails_to_individual_buyers():
    """Emails sent out to individual buyers"""
    try:
        emails_sent_to_individual_buyer = Email.query.filter_by(
            bulk="buyer Email"
        ).all()
        emails = len(emails_sent_to_individual_buyer)
        return render_template(
            "admin/individual_buyer_email.html",
            title="Emails Sent To Individual buyers",
            emails_sent_to_individual_buyer=emails_sent_to_individual_buyer,
            emails=emails,
        )
    except Exception as e:
        # Handle the exception here
        flash("An error occurred while retrieving emails.", "danger")
        print(f"An error occurred: {e}")
        return redirect(url_for("dashboard"))


# List all buyers
# Not Checked
@app.route("/dashboard/all-buyers")
@login_required
def all_buyers():
    try:
        buyers = Buyer.query.all()
        all_registered_buyers = len(buyers)
        return render_template(
            "admin/all_buyers.html",
            title="All buyers",
            buyers=buyers,
            all_registered_buyers=all_registered_buyers,
        )
    except Exception as e:
        # Handle the exception here
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


# Deactivate buyer
# Not Checked
@app.route("/dashboard/deactivate-buyer/<username>")
@login_required
def deactivate_buyer(username):
    try:
        buyer = Buyer.query.filter_by(username=username).first_or_404()
        buyer.active = False
        db.session.add(buyer)
        db.session.commit()
        flash(f"{buyer.username} has been deactivated as a buyer")
        return redirect(url_for("all_buyers"))
    except Exception as e:
        flash("An error occurred while deactivating the buyer")
        print(f"An error occurred: {e}")
        return redirect(url_for("all_buyers"))


# Reactivate buyer
# Not Checked
@app.route("/dashboard/reactivate-buyer/<username>")
@login_required
def reactivate_buyer(username):
    try:
        buyer = Buyer.query.filter_by(username=username).first_or_404()
        buyer.active = True
        db.session.add(buyer)
        db.session.commit()
        flash(f"{buyer.username} has been reactivated as a buyer")
        return redirect(url_for("all_buyers"))
    except Exception as e:
        flash("An error occurred while reactivating the buyer")
        return redirect(url_for("all_buyers"))


# Delete buyer
# Not Checked
@app.route("/dashboard/delete-buyer/<username>")
@login_required
def delete_buyer(username):
    try:
        buyer = Buyer.query.filter_by(username=username).first_or_404()
        if current_user.department == "Super Admin" or current_user.id == buyer.id:
            db.session.delete(buyer)
            db.session.commit()
            flash(f"{buyer.username} has been deleted as a buyer")
            return redirect(url_for("all_buyers"))
        else:
            flash("You do not have enough permissions.")
            return redirect(url_for("dashboard"))
    except Exception as e:
        flash("An error occurred while deleting the buyer.")
        print(f"An error occurred: {e}")
        return redirect(url_for("all_buyers"))


# Send email to individual buyer
# Not Checked
@app.route("/send-email-to-buyer/<id>")
@login_required
def send_buyer_email(id):
    """Send email to buyer from the database"""
    try:
        email = Email.query.filter_by(id=id).first()
        buyer_email = session["buyer_email"]
        buyer_first_name = session["buyer_first_name"]

        # Update db so that the email is not sent again
        email.allow = True
        db.session.add(email)
        db.session.commit()

        # Send email to user
        send_user_private_email(email, buyer_email, buyer_first_name)

        # Notify user that email has been sent
        flash(f"Email successfully sent to the teacher {buyer_email}")
        del session["buyer_email"]
        del session["buyer_first_name"]
        return redirect(url_for("emails_to_individual_buyers"))
    except Exception as e:
        flash(f"An error occurred while sending the email: {str(e)}")
        print(f"An error occurred: {e}")
        return redirect(url_for("emails_to_individual_buyers"))


# Edit sample email
# Not Checked
@app.route("/edit-buyer-email/<id>", methods=["GET", "POST"])
@login_required
def edit_buyer_email(id):
    """Edit email to buyer from the database"""
    try:
        email = Email.query.filter_by(id=id).first()
        form = EmailForm()
        form.signature.choices = [
            (current_user.first_name.capitalize(), current_user.first_name.capitalize())
        ]
        if form.validate_on_submit():
            email.subject = form.subject.data
            email.body = form.body.data
            email.closing = form.closing.data
            email.signature = form.signature.data
            db.session.commit()
            flash("Your changes have been saved")
            return redirect(url_for("emails_to_individual_buyers"))
        if request.method == "GET":
            form.subject.data = email.subject
            form.body.data = email.body
            form.signature.data = email.signature
        return render_template(
            "admin/edit_email.html", title="Edit Sample Email", form=form
        )
    except Exception as e:
        flash("An error occurred while editing the email")
        print(f"An error occurred: {e}")
        return redirect(url_for("emails_to_individual_buyers"))


# Delete email from database
# Not Checked
@app.route("/delete-email-sent-to-a-buyer/<id>")
@login_required
def delete_buyer_email(id):
    """Delete email to buyer from the database"""
    try:
        email = Email.query.filter_by(id=id).first()
        db.session.delete(email)
        db.session.commit()
        flash("Email successfully deleted")
        del session["buyer_email"]
        del session["buyer_first_name"]
        return redirect(url_for("emails_to_individual_buyers"))
    except Exception as e:
        flash("An error occurred while deleting the email")
        print(f"Error: {e}")
        return redirect(url_for("emails_to_individual_buyers"))


# --------------------------------------
# End of all buyers
# --------------------------------------


# --------------------------------------
# All sellers
# --------------------------------------


# seller profile
# Checked
@app.route("/seller/profile", methods=["GET", "POST"])
@login_required
def seller_profile():
    try:
        if current_user.type == "seller":
            # Profile edits
            username_form = EditUsernameForm()
            email_form = EditEmailForm()
            phone_form = EditPhoneForm()

            if request.method == "GET":
                username_form.username.data = current_user.username
                email_form.email.data = current_user.email
                phone_form.phone.data = current_user.phone_number
            if username_form.validate_on_submit() and username_form.username.data:
                current_user.username = username_form.username.data
                db.session.commit()
                flash("Username updated.")
                return redirect(url_for("seller_profile"))
            if email_form.validate_on_submit() and email_form.email.data:
                current_user.email = email_form.email.data
                db.session.commit()
                flash("Email updated.")
                return redirect(url_for("seller_profile"))
            if phone_form.validate_on_submit() and phone_form.phone.data:
                current_user.phone_number = phone_form.phone.data
                db.session.commit()
                flash("Phone number updated.")
                return redirect(url_for("seller_profile"))
            return render_template(
                "seller/profile.html",
                title="Seller Profile",
                username_form=username_form,
                email_form=email_form,
                phone_form=phone_form,
            )
        else:
            return flash_message()
    except Exception as e:
        # Handle the exception here
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


# Deactivate seller
# Not Checked
@app.route("/seller/deactivate-account")
@login_required
def seller_deactivate_account():
    try:
        # Get current user
        seller = Seller.query.filter_by(username=current_user.username).first()

        # Send email to all admins about the request to delete account
        buyer = Buyer.query.filter_by(id=seller.buyer_id).first()
        request_account_deletion(buyer, seller)

        flash(
            "Your request has been sent to the admins."
            " You will receive an email notification if approved"
        )
        return redirect(url_for("seller_profile"))
    except Exception as e:
        flash(
            "An error occurred while deactivating your account. Please try again later."
        )
        print(f"An error occurred: {e}")
        return redirect(url_for("seller_profile"))


# Compose direct email to seller
# Not Checked
@app.route(
    "/dashboard/compose-direct-email-to-a-seller/<email>", methods=["GET", "POST"]
)
@login_required
def compose_direct_email_to_seller(email):  
    try:
        """Write email to individual seller"""
        # Get the buyer
        seller = Seller.query.filter_by(email=email).first()
        seller_username = seller.email.split("@")[0].capitalize()
        session["seller_email"] = seller.email
        session["seller_first_name"] = seller.first_name

        form = EmailForm()
        form.signature.choices = [
            (current_user.first_name.capitalize(), current_user.first_name.capitalize())
        ]
        if form.validate_on_submit():
            email = Email(
                subject=form.subject.data,
                body=form.body.data,
                closing=form.closing.data,
                signature=form.signature.data,
                bulk="seller Email",
                author=current_user,
            )
            db.session.add(email)
            db.session.commit()
            flash(f"Sample private email to {seller_username} saved")
            return redirect(url_for("emails_to_individual_sellers"))
        return render_template(
            "admin/email_seller.html",
            title="Compose Private Email",
            form=form,
            seller=seller,
        )
    except Exception as e:
        # Handle the exception here
        print(f"An error occurred: {e}")
        flash(f"An error occurred: {str(e)}")
        return redirect(url_for("emails_to_individual_sellers"))


# List of emails sent out to individual seller
# Not Checked
@app.route("/dashboard/emails-to-individual-sellers")
@login_required
def emails_to_individual_sellers():
    try:
        """Emails sent out to individual seller"""
        emails_sent_to_individual_seller = Email.query.filter_by(
            bulk="seller Email"
        ).all()
        emails = len(emails_sent_to_individual_seller)
        return render_template(
            "admin/individual_seller_email.html",
            title="Emails Sent To Individual sellers",
            emails_sent_to_individual_seller=emails_sent_to_individual_seller,
            emails=emails,
        )
    except Exception as e:
        # Handle the exception here
        print(f"An error occurred: {e}")
        flash("An error occurred while retrieving emails.")
        return redirect(url_for("dashboard"))


# List all sellers
# Not Checked
@app.route("/dashboard/all-sellers")
@login_required
def all_sellers():
    try:
        if current_user.type == "admin":
            sellers = Seller.query.all()
            all_registered_sellers = len(sellers)
            return render_template(
                "seller/all_sellers.html",
                title="All sellers",
                sellers=sellers,
                all_registered_sellers=all_registered_sellers,
            )
        elif current_user.type == "buyer":
            sellers = Seller.query.filter_by(buyer_id=current_user.id).all()
            all_registered_sellers = len(sellers)
            return render_template(
                "seller/all_sellers.html",
                title="All sellers",
                sellers=sellers,
                all_registered_sellers=all_registered_sellers,
            )
        else:
            return flash_message()
    except Exception as e:
        # Handle the exception here
        print(f"An error occurred: {e}")
        # You can also log the error or return an error message to the user
        return f"Error : {e}", 400


# Deactivate seller
# Checked
@app.route("/dashboard/deactivate-seller/<username>")
@login_required
def deactivate_seller(username):
    try:
        if current_user.type == "buyer" or current_user.type == "admin":
            seller = Seller.query.filter_by(username=username).first_or_404()
            seller.active = False
            db.session.add(seller)
            db.session.commit()
            flash(f"{seller.username} has been deactivated as a seller")
            return redirect(url_for("all_sellers"))
        else:
            return flash_message()
    except Exception as e:
        # Handle the exception here
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


# Reactivate seller
# Checked
@app.route("/dashboard/reactivate-seller/<username>")
@login_required
def reactivate_seller(username):
    try:
        if current_user.type == "buyer" or current_user.type == "admin":
            seller = Seller.query.filter_by(username=username).first_or_404()
            seller.active = True
            db.session.add(seller)
            db.session.commit()
            flash(f"{seller.username} has been reactivated as a seller")
            return redirect(url_for("all_sellers"))
        else:
            return flash_message()
    except Exception as e:
        # Handle the exception here
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


# Delete seller
# Checked
@app.route("/dashboard/delete-seller/<username>")
@login_required
def delete_seller(username):
    try:
        if current_user.is_authenticated:
            seller = Seller.query.filter_by(username=username).first_or_404()
            if current_user.type == "buyer":
                if seller.buyer_id == current_user.id or current_user.department == "Super Admin" or current_user.id == seller.id:
                    db.session.delete(seller)
                    db.session.commit()
                    flash(f"{seller.username} has been deleted as a seller")
                    return redirect(url_for("all_sellers"))
                else:
                    return flash_message()
            db.session.delete(seller)
            db.session.commit()
            flash(f"{seller.username} has been deleted as a seller")
            return redirect(url_for("all_sellers"))
        else:
            return flash_message()
    except Exception as e:
        # Handle or log the exception
        print(f"Error deleting seller: {e}")
        return f"Error : {e}", 400


# Send email to individual seller
# Not Checked
@app.route("/send-email-to-seller/<id>")
@login_required
def send_seller_email(id):
    try:
        """Send email to seller from the database"""
        email = Email.query.filter_by(id=id).first()
        seller_email = session["seller_email"]
        seller_first_name = session["seller_first_name"]

        # Update db so that the email is not sent again
        email.allow = True
        db.session.add(email)
        db.session.commit()

        # Send email to user
        send_user_private_email(email, seller_email, seller_first_name)

        # Notify user that email has been sent
        flash(f"Email successfully sent to the teacher {seller_email}")
        del session["seller_email"]
        del session["seller_first_name"]
        return redirect(url_for("emails_to_individual_sellers"))
    except Exception as e:
        flash(f"An error occurred while sending the email: {str(e)}")
        print(f"An error occurred: {e}")
        return redirect(url_for("emails_to_individual_sellers"))


# Edit sample email
# Not Checked
@app.route("/edit-seller-email/<id>", methods=["GET", "POST"])
@login_required
def edit_seller_email(id):
    try:
        """Edit email to seller from the database"""
        email = Email.query.filter_by(id=id).first()
        form = EmailForm()
        form.signature.choices = [
            (current_user.first_name.capitalize(), current_user.first_name.capitalize())
        ]
        if form.validate_on_submit():
            email.subject = form.subject.data
            email.body = form.body.data
            email.closing = form.closing.data
            email.signature = form.signature.data
            db.session.commit()
            flash("Your changes have been saved")
            return redirect(url_for("emails_to_individual_sellers"))
        if request.method == "GET":
            form.subject.data = email.subject
            form.body.data = email.body
            form.signature.data = email.signature
        return render_template(
            "admin/edit_email.html", title="Edit Sample Email", form=form
        )
    except Exception as e:
        # Handle the exception here
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


# Delete email from database
# Not Checked
@app.route("/delete-email-sent-to-a-seller/<id>")
@login_required
def delete_seller_email(id):
    """Delete email to seller from the database"""
    try:
        email = Email.query.filter_by(id=id).first()
        db.session.delete(email)
        db.session.commit()
        flash("Email successfully deleted")
        del session["seller_email"]
        del session["seller_first_name"]
        return redirect(url_for("emails_to_individual_sellers"))
    except Exception as e:
        flash("An error occurred while deleting the email")
        print(f"Error: {e}")
        return redirect(url_for("emails_to_individual_sellers"))


# --------------------------------------
# End of all sellers
# --------------------------------------

# Edit needed from here.
# --------------------------------------
# Products
# --------------------------------------


# -----------------------------
# Curd On Products  // Note : Edit code might and should not work
# -----------------------------


# Getting current ipo from chittorgarh
# Checked
@app.route("/get-product")
def get_product():
    try:
        scraper = IPODetailsScraper(driver_path, "chittorgarh", headless=True)

        ipo_details_green, ipo_details_lightyellow, ipo_details_aqua = (
            scraper.scrape_ipo_details()
        )
        process_ipo_details(
            ipo_details_green, ipo_details_lightyellow, ipo_details_aqua
        )
        return redirect(url_for("view_product"))
    except Exception as e:
        # Handle the exception here
        print(f"An error occurred: {str(e)}")
        # Optionally, you can redirect to an error page or return an error message
        return "An error occurred while getting the product"


# ipo status and name assigninig
# Checked
# Potential Updates : Analysze more.
def process_ipo_details(ipo_details_green, ipo_details_lightyellow, ipo_details_aqua):
    # Process green IPOs - Add new
    all_names = [
        item["Name"]
        for item in ipo_details_green + ipo_details_aqua + ipo_details_lightyellow
    ]
    all_names_set = set(all_names)  # Convert list to set for efficient comparison
    perfect_names = []
    db_names_set = {ipo.name for ipo in IPO.query.all()}
    for i in all_names_set:
        name = clean_name(i)
        perfect_names.append(name)
    names_not_in_dicts = db_names_set - set(perfect_names)
    for name in names_not_in_dicts:
        ipo = IPO.query.filter_by(name=name).first()
        ipo.status = "complete"
        db.session.commit()
    # Process light yellow IPOs - Update existing
    update_ipo_status(ipo_details_green, "open")
    update_ipo_status(ipo_details_lightyellow, "closed")
    update_ipo_status(ipo_details_aqua, "listed")


# Update ipo status
# Checked
def update_ipo_status(ipo_details, status):
    new_ipos = []
    collected_names = set()  # This will be used later if status is 'listed'

    for ipo in ipo_details:
        name = clean_name(ipo["Name"])
        collected_names.add(name)  # Used for checking listed IPOs later

        ipo_db = IPO.query.filter_by(name=name).first()
        if ipo_db:
            if status != "open":
                ipo_db.status = status
        else:
            # Prepare new IPO records
            new_ipo = IPO(
                name=name,
                price=ipo["Price"],
                issue_size=ipo["Issue Size"],
                lot_size=ipo["Lot Size"],
                open_date=datetime.strptime(ipo["Open Date"], "%b %d, %Y"),
                close_date=datetime.strptime(ipo["Close Date"], "%b %d, %Y"),
                listing_date=datetime.strptime(ipo["Listing Date"], "%b %d, %Y"),
                listing_at=ipo["Listing At"],
                status=status,
            )
            new_ipos.append(new_ipo)

    # Bulk add new IPOs
    if new_ipos:
        db.session.bulk_save_objects(new_ipos)

    if status == "listed":
        # Fetch all listed IPOs not included in the collected_names and update them to 'complete'
        IPO.query.filter(
            IPO.status == "listed", IPO.name.notin_(collected_names)
        ).update({IPO.status: "complete"}, synchronize_session=False)

    # Commit all changes made in this session
    db.session.commit()


# Make the ipo name smaller
# Checked
def clean_name(name):
    # Combine all patterns, prioritizing longer/more specific patterns to ensure they're matched first
    pattern = r"( PUBLIC LIMITED IPO\.? ?| LIMITED FPO\.? ?| LIMITED IPO\.? ?| PUBLIC LIMITED\.? ?| LTD IPO\.? ?| LIMITED\.? ?| LTD\.? ?| IPO)$"
    # Use re.IGNORECASE to make the pattern case-insensitive
    cleaned_name = re.sub(pattern, "", name, flags=re.IGNORECASE)
    return cleaned_name


# View Product


# Shows all the ipo's
# Checked
@app.route("/view-product")
@login_required
def view_product():  # Testing Feature
    try:
        if session.get("temp_details") is not None:
            session.pop("temp_details", None)
            print("Session pop")

        if current_user.is_authenticated:

            products = IPO.query.all()
            view_products = len(products)
            status_priority = {"open": 1, "closed": 2, "listed": 3}

            products.sort(
                key=lambda x: (status_priority.get(x.status, 4), x.listing_date)
            )
            return render_template(
                "Product/all_products.html",
                # "transaction/view_products.html",
                title="Running Ipo's ",
                products=products,
                view_products=view_products,
            )
        else:
            return flash_message()
    except Exception as e:
        # Handle the exception here
        print(f"An error occurred: {str(e)}")
        return f"Error : {e}", 400
    
@app.route("/delete-product/<int:id>")
@login_required
def delete_product(id):
    try:
        if current_user.type == "admin" or current_user.type == "Super Admin":
            product = IPO.query.filter_by(id=id).first_or_404()
            db.session.delete(product)
            db.session.commit()
            flash(f"{product.name} has been deleted")
            return redirect(url_for("view_product"))
        else:
            return flash_message()
    except Exception as e:
        # Handle the exception here
        print(f"An error occurred: {str(e)}")
        return f"Error : {e}", 400

# --------------
# End Of Curd On Products
# --------------


# --------------------------------------
# End of Products
# --------------------------------------

# --------------------------------------
# Related To Pans
# --------------------------------------


# --------------------
# Curd On Pan // Note : Edit code might and should not work
# --------------------


# Create Pan
# Checked
@app.route("/add-pan", methods=["GET", "POST"])
@login_required
def add_pan():
    try:
        if current_user.type == "seller":
            form = PanForm()
            if form.validate_on_submit():
                try:
                    pan = Pan(
                        name=form.name.data,
                        pan_number=form.pan_number.data.upper(),
                        dp_id=form.dp_id.data,
                        seller=current_user,
                    )
                    db.session.add(pan)
                    db.session.commit()
                    flash(f"Pan {pan.name}({pan.pan_number}) added . Add More.")
                    return redirect(url_for("add_pan"))
                except IntegrityError as e:
                    db.session.rollback()
                    flash("You Already have a pan with this number")
                    return redirect(url_for("add_pan"))
                except Exception as e:
                    # Handle the exception and return an appropriate response
                    print(e)
                    return f"Error: {str(e)}", 400
            return render_template("Pan/add_pan.html", title="Add Pan", form=form)

        # Add a return statement for cases when the current user type is not 'seller'
        return flash_message()
    except Exception as e:
        # Handle the exception and return an appropriate response
        print(e)
        return f"Error: {str(e)}", 400


@app.route("/edit-pans", methods=["POST"])
@login_required
def edit_pans():
    try:
        if current_user.type == "seller":
            data = request.get_json()
            record_id = data["id"]
            new_value = data["newValue"]
            new_column = data["column"]

            try:
                pan = Pan.query.filter_by(id=record_id).first()
                if not pan:
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "message": "No record found with the given ID",
                            }
                        ),
                        404,
                    )

                if new_column == "dp_id":
                    pan.dp_id = new_value
                elif new_column == "name":
                    pan.name = new_value
                elif new_column == "pan_number":
                    new_value = new_value.upper()
                    pan.pan_number = new_value
                else:
                    return (
                        jsonify({"status": "error", "message": "Invalid column name"}),
                        400,
                    )

                db.session.commit()
                return jsonify(
                    {"status": "success", "message": "Cell updated successfully"}
                )

            except IntegrityError as e:
                db.session.rollback()  # Roll back the transaction so you can continue cleanly
                # flash("You Already have a pan with this number")
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "You Already have a pan with this number ",
                        }
                    ),
                    400,
                )
            except Exception as e:
                db.session.rollback()  # Roll back the transaction on other exceptions too
                print(e)  # Log the error in production code
                return jsonify({"status": "error", "message": str(e)}), 500
        else:
            return (
                flash_message()
            )  # Assumes flash_message handles non-"seller" cases, ensure to return a valid response
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Multi Pan
# For Adding too many pans at once, for testing purpose only delete after use
# @app.route("/multi-pan")
# def multi_pan():
#     for i in range(10):
#         for j in range(10):
#             import random
#             import string
#             from faker import Faker

#             fake = Faker()
#             name = fake.name()
#             random_string = "".join(
#                 random.choice(string.ascii_letters) for _ in range(4)
#             )
#             random_number = random.randint(1000, 9999)
#             one = "".join(random.choice(string.ascii_letters) for _ in range(1))
#             pan = Pan(
#                 name=f"{name}",
#                 pan_number=f"{random_string}{random_number}{one}".upper(),
#                 dp_id=random.randint(1000000000, 9999999999),
#                 seller_id=3,
#             )
#             db.session.add(pan)
#             db.session.commit()
#     return redirect(url_for("all_pan"))


# Read Pan
# Checked
# Potential Updates : Buyer can not see the pan's of seller so we need to give something else in navbar
@app.route("/all-pan")
@login_required
def all_pan():
    try:
        if current_user.type == "seller":
            pans = Pan.query.filter_by(seller_id=current_user.id).all()
            all_pans = len(pans)
            return render_template(
                "Pan/all_pans.html",
                title="All Pans",
                pans=pans,
                all_pans=all_pans,
            )
        elif current_user.type == "admin":
            pans = Pan.query.all()
            all_pans = len(pans)
            return render_template(
                "Pan/all_pans.html",
                title="All Pans",
                pans=pans,
                all_pans=all_pans,
            )
        else:
            return flash_message()
    except Exception as e:
        return str(e)

# Delete Pan
# Checked
@app.route("/delete-pan/<id>")
@login_required
def delete_pan(id):
    try:
        if current_user.type == "seller":
            pan = Pan.query.filter_by(seller_id=current_user.id, id=id).first_or_404()
            db.session.delete(pan)
            db.session.commit()
            flash(f"The Pan {pan.name}({pan.pan_number}) has been deleted")
            return redirect(url_for("all_pan"))
        return flash_message()
    except Exception as e:
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400

# ----------
# End Of Curd On Pan
# ----------

# --------------------------------------
# End of Related To Pans
# --------------------------------------

# --------------------------------------
# Related To Transaction
# --------------------------------------


# --------------------------------------
# Add Details
# --------------------------------------

# ----------
# Curd On Details // Note : Edit code might and should not work
# ----------


# Create Details
# Checked
# Potential Updates : We need to verify the transaction from the buyer side.
@app.route("/add-details/<int:product_id>", methods=["GET", "POST"])
@login_required
def add_details(product_id):
    try:
        if current_user.type == "seller":
            product_name = IPO.query.filter_by(id=product_id).first_or_404()
            if "temp_details" not in session:
                session["temp_details"] = []
            if product_id is None:
                flash("No Product Selected")
                return redirect(url_for("view_product"))
            form = DetailForm()
            if form.validate_on_submit():
                details = Details(
                    product_id=product_id,
                    subject=form.subject.data,
                    formtype=form.formtype.data,
                    price=form.price.data,
                    quantity=form.quantity.data,
                    seller=current_user,
                )
                print(product_id)
                db.session.add(details)
                db.session.commit()
                session["temp_details"].append(details.id)
                session.modified = True
                print("Session ->", session["temp_details"])
                print(details.id)
                transaction = Transaction(
                    details_id=details.id,
                    product_id=product_id,
                    buyer_id=current_user.buyer_id,
                    seller_id=current_user.id,
                )
                db.session.add(transaction)
                db.session.commit()
                flash("Details added successfully")
                return redirect(url_for("add_details", product_id=product_id))

            return render_template(
                "Details/add_details.html",
                title="Add Details",
                form=form,
                product_name=product_name,
                extra_details=Details.query.filter(
                    Details.id.in_(session["temp_details"])
                ).all(),
            )

        if current_user.type != "seller":
            return flash_message()
    except Exception as e:
        # Handle the exception here
        print(f"An error occurred: {str(e)}")
        # Optionally, you can log the error or display a user-friendly error message


# ----------
# Curd On Transaction
# ----------


# Read Transaction
# Checked
@app.route("/all-transactions")
@login_required
def all_transaction():
    # try:
        if session.get("temp_details") is not None:
            session.pop("temp_details", None)
            # print("Session pop")
        if current_user.type == "seller":
            transactions = Transaction.query.filter_by(seller_id=current_user.id).all()
            for transaction in transactions:
                transaction.items_processed = count_pan(transaction.id)
            all_transactions = len(transactions)
            return render_template(
                "transaction/all_transactions.html",
                title="All Transactions",
                transactions=transactions,
                all_transactions=all_transactions,
            )
        elif current_user.type == "buyer" or current_user.type == "admin":
            seller_id = request.args.get("seller_id", type=int)
            seller = Seller.query.filter_by(id=seller_id).first_or_404()
            transactions = Transaction.query.filter_by(seller_id=seller.id).all()
            for transaction in transactions:
                transaction.items_processed = count_pan(transaction.id)
            all_transactions = len(transactions)
            return render_template(
                "transaction/all_transactions.html",
                title="All Transactions",
                transactions=transactions,
                all_transactions=all_transactions,
            )
        else:
            return flash_message()
    # except Exception as e:
    #     # Handle the exception here
    #     print(f"An error occurred: {str(e)}")
    #     return f"Error : {e}", 400

def count_pan(transaction_id):
    count = TransactionPan.query.filter_by(transaction_id=transaction_id).count()
    return count





@app.route("/delete-transaction/<int:id>", methods=["GET", "POST"])
@login_required
def delete_transaction(id):
    try:
        transaction = Transaction.query.filter_by(id=id).first_or_404()
        db.session.delete(transaction)
        db.session.commit()
        flash(f"The transaction has been deleted")
        return redirect(url_for("all_transaction"))
    except Exception as e:
        flash(f"An error occurred while deleting the transaction: {str(e)}")
        return redirect(url_for("all_transaction"))

# ----------
# End Of Curd On Transaction
# ----------

# Available Pans for transaction
# Checked


@app.route("/available-pans", methods=["GET", "POST"])
@login_required
def available_pans():
    try:
        if current_user.type != "seller":
            flash("You are not authorized to view this page.")
            return redirect(url_for("index"))

        transaction_id = request.args.get("transaction_id", type=int)
        transaction = Transaction.query.get_or_404(transaction_id)

        if not validate_pan_counts(transaction):
            return redirect(url_for("all_transaction"))

        if request.method == "GET":
            return show_available_pans(transaction)
        elif request.method == "POST":
            return process_selected_pans(transaction)
    except Exception as e:
        flash("An error occurred.")
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


def validate_pan_counts(transaction):
    try:
        count = count_pan(transaction.id)
        if count >= transaction.details.quantity:
            flash(
                f"You have already added {count} pans to this transaction. You cannot add more."
            )
            return False
        return True
    except Exception as e:
        flash("An error occurred.")
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


def show_available_pans(transaction):
    try:
        pans = Pan.query.filter_by(seller_id=current_user.id).all()
        return render_template(
            "transaction/available_pans.html",
            title="All Pans",
            pans=pans,
            all_pans=len(pans),
            transaction=transaction,
        )
    except Exception as e:
        flash("An error occurred.")
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


def process_selected_pans(transaction):
    try:
        selected_ids = request.form.getlist("ID[]")
        required_pans = transaction.details.quantity - count_pan(transaction.id)

        if len(selected_ids) > required_pans:
            flash(
                f"You must select exactly {required_pans} pans. You selected {len(selected_ids)}."
            )
            return redirect(url_for("available_pans", transaction_id=transaction.id))

        for selected_id in selected_ids:
            if pan_already_assigned_to_product(
                transaction.product_id, int(selected_id)
            ):
                pan = Pan.query.get(int(selected_id))
                flash(
                    f"Pan number {pan.pan_number} has already been assigned to a transaction for Ipo {transaction.product.name}."
                )
                return redirect(
                    url_for("available_pans", transaction_id=transaction.id)
                )
            add_pan_to_transaction(transaction.id, int(selected_id))
        db.session.commit()
        flash("The transaction has been updated successfully.")
        return redirect(url_for("all_transaction"))
    except IntegrityError:
        flash("A database error occurred.")
        db.session.rollback()
        return redirect(url_for("available_pans", transaction_id=transaction.id))
    except Exception as e:
        flash("An error occurred.")
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


def add_pan_to_transaction(transaction_id, pan_id):
    try:
        transaction_pan = TransactionPan(transaction_id=transaction_id, pan_id=pan_id)
        db.session.add(transaction_pan)
    except Exception as e:
        flash("An error occurred.")
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


def pan_already_assigned_to_product(product_id, pan_id):
    try:
        existing_transactions = Transaction.query.filter_by(product_id=product_id).all()
        existing_pans = [
            pan.pan_id
            for trans in existing_transactions
            for pan in TransactionPan.query.filter_by(transaction_id=trans.id).all()
        ]
        return pan_id in existing_pans
    except Exception as e:
        flash("An error occurred.")
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


# Details of the transaction
@app.route("/transaction-details/<int:product_id>")
@login_required
def transaction_details(product_id):
    try:
        if current_user.type == "seller":
            transactions = Transaction.query.filter_by(
                seller_id=current_user.id, product_id=product_id
            ).all()
            if not transactions:
                flash("No transaction found")
                return redirect(url_for("view_product"))
            transaction_pans = pannum_trans(transactions)
            # transaction_pans = []
            # for transaction in transactions:
            #     transaction_pan = TransactionPan.query.filter_by(
            #         transaction_id=transaction.id
            #     ).all()
            #     transaction_pans.extend(transaction_pan)
            return render_template(
                "transaction/details_transaction.html",
                title="Transaction Details",
                details=transactions[0].product.name,
                transactions=transaction_pans,
                total_transaction=len(transaction_pans),
                # transaction_pans=transaction_pans
            )
        elif current_user.type == "buyer":
                sellers = Seller.query.filter_by(buyer_id=current_user.id).all()
                seller_pans = []
                for seller in sellers:
                    transactions = Transaction.query.filter_by(seller_id=seller.id, product_id=product_id).all()
                    # print("Transactions  here->", transactions)
                    if transactions:
                        transaction_pans = pannum_trans(transactions)
                        seller_pans.extend(transaction_pans)
                # print("Seller Pans ->", seller_pans)
                if seller_pans:
                    return render_template(
                        "transaction/details_transaction.html",
                        title="Transaction Details",
                        details=seller_pans[0].transaction.product.name,
                        transactions=seller_pans,
                        total_transaction=len(seller_pans),
                        # transaction_pans=transaction_pans
                    )
                else:
                    flash("No transaction found")
                    return redirect(url_for("view_product"))
        else:
            return flash_message()
    except Exception as e:
        print("An error occurred:", str(e))
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {e.args}")
        return f"Error : {e}", 400

# --------------------------------------
# End of Related To Transaction
# --------------------------------------


def pannum_trans(transactions):
    transaction_pans = []
    for transaction in transactions:
        transaction_pan = TransactionPan.query.filter_by(
        transaction_id=transaction.id
    ).all()
        transaction_pans.extend(transaction_pan)
    return transaction_pans

@app.route("/seller-transaction/<int:product_id>")
def seller_transaction(product_id):
    try:
        # Get all the sellers of our buyer
        if current_user.type == "buyer":
            sellers = Seller.query.filter_by(buyer_id=current_user.id).all()
        elif current_user.type == "admin":
            sellers = Seller.query.all()
        else:
            return flash_message()    
        print("Sellers ->", sellers)
        
        transactions = []  # Initialize an empty list to collect transactions
        for seller in sellers:
            seller_transactions = Transaction.query.filter_by(seller_id=seller.id, product_id=product_id).all()
            print(f"Transactions for Seller {seller.id} ->", seller_transactions)
            transactions.extend(seller_transactions)  # Collect transactions
        
        if not transactions:  # Check if the list is empty
            flash("No transactions found")
            return redirect(url_for("view_product"))
        return render_template(
            "transaction/seller_transaction.html",
            title="Transaction Details",
            transactions=transactions,
            total_transaction=len(transactions),
        )
    except Exception as e:
        print("An error occurred:", str(e))
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {e.args}")
        return f"Error : {e}", 400


# --------------------------------------
# Related To Checking allotment
# --------------------------------------

@app.route("/allotment/<product_id>/<ipo>", methods=["GET", "POST"])
@login_required
def allotment(product_id, ipo, listing_On="bigshare"):
    if current_user.type == "buyer":
        if not os.path.exists(f"json_file/{ipo}/{current_user.id}.json"):
            print("Product id ->", product_id)
            print("Listing On ->", listing_On)
            print("Ipo ->", ipo)
            buyer_id = current_user.id
            sellers = Seller.query.filter_by(buyer_id=buyer_id).all()
            usernames = []   
            room = current_user.id         
            for seller in sellers:
                transactions = Transaction.query.filter_by(seller_id=seller.id, product_id=product_id).all()
                if transactions:
                    transaction_pans = pannum_trans(transactions)
                    for transaction_pan in transaction_pans:
                        usernames.append(transaction_pan.pan.pan_number)        
            results = scrape_data_from_websites(
                driver_path, listing_On, ipo, usernames, room, socketio, headless=True)
            if os.path.exists("json_file/{ipo}"):
                if not os.path.exists(f"json_file/{ipo}/{buyer_id}"):
                    with open(f"json_file/{ipo}/{buyer_id}", "w") as file:
                        json.dump(results, file)
            else:
                os.makedirs(f"json_file/{ipo}")  # Create the folder if it does not exist
                with open(f"json_file/{ipo}/{buyer_id}.json", "w") as file:
                    json.dump(results, file)
            print("Results ->", jsonify(results))
            return jsonify(results)
        else:
            return jsonify({"message": "We have already checked the allotment for this product."})
    else:
        return flash_message()
        
        


# Checking Allotment
# Checked
@app.route("/checking-allotment", methods=["GET", "POST"])
@login_required
def checking_allotment():
    try:
        if current_user.is_authenticated:
            form = AllotmentForm()
            file_ready = False
            room = current_user.id
            print("Room id ->", room)
            if form.validate_on_submit():
                # Checking whether the folder is empty or not
                folder_path = "C:\\Users\\kavya\\Documents\\My_programming\\buy-sell\\myflaskapp\\app\\upload_folder"
                for filename in os.listdir(folder_path):
                    file_path = os.path.join(folder_path, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                # Saving the file
                file = form.excel_file.data
                filename = secure_filename(file.filename)
                # Change this in Deployment.
                filepath = os.path.join(folder_path, filename)
                file.save(filepath)
                # Reading Data
                ipo = form.ipo.data.strip()
                listing_On = form.listing_On.data.strip()
                pan_Column = form.pan_Column.data.strip()
                if pan_Column.isdigit():
                    pan_Column = int(pan_Column) - 1
                start_Row = form.start_Row.data
                end_Row = form.end_Row.data

                # Reading the file
                usernames = process_excel_data(filepath, pan_Column, start_Row, end_Row)
                print("Usernames ->", type(usernames))
                # # Scraping the website
                print("Socket ->", socketio)
                results = scrape_data_from_websites(
                    driver_path, listing_On, ipo, usernames, room, socketio, headless=True
                )
                if os.path.exists("json"):
                    if os.path.exists(f"json/{ipo}.json"):
                        with open(f"json/{ipo}.json", "w") as file:
                            json.dump(results, file)  # Save the results to a JSON file
                    else:
                        with open(f"json/{ipo}.json", "w") as file:
                            json.dump(results, file)
                else:
                    os.makedirs("json")  # Create the folder if it does not exist
                    with open(f"json/{ipo}.json", "w") as file:
                        json.dump(results, file)
                # Saving the results
                write_in_excel(filepath, results, pan_Column)
                file_ready = True
                return download_updated_file(filepath)
            return render_template(
                "allotment/check_allotment.html",
                title="Checking Allotment",
                form=form,
                file_ready=file_ready,
                room=room,
            )
        else:
            return flash_message()
    except Exception as e:
        print("An error occurred:", str(e))
        # Handle the exception here or re-raise it if necessary
        return f"Error : {e}", 400

@socketio.on("join")
def on_join(data):
    room = current_user.id
    join_room(room)
    # emit('log', {'data': 'Connected to live log stream.'}, room=room)


def download_updated_file(filepath):

    if filepath and os.path.exists(filepath):
        try:
            # First, prepare the response using send_file
            response = send_file(filepath, as_attachment=True)
            return response
        except Exception as e:
            # Handle exceptions, possibly logging them
            print(e)
            abort(404)
    else:
        return "Invalid download token or file does not exist", 404


# --------------------------------------
# End of Checking allotment
# --------------------------------------


# --------------------------------------
# Bulk emails
# --------------------------------------


@app.route("/add-pan-from-excel", methods=["GET", "POST"])
def add_pan_from_excel():
    try:
        if current_user.type == "seller":
            file = request.files["file"]
            filename = secure_filename(file.filename)
            print("Filename ->", filename)
            content = file.read()
            df = process_excel(content)
            if df["pan"].isnull().any():
                raise ValueError(
                    "Pan column contains null values, which are not allowed."
                )
            # Convert DataFrame to list of dictionaries
            records = df.to_dict(orient="records")
            # print("Records ->", records)

            # Insert each record
            for record in records:
                existing_record = Pan.query.filter_by(
                    pan_number=record.get("pan"), seller=current_user
                ).first()

                if not existing_record:
                    pan = Pan(
                        name=record.get("name"),
                        pan_number=record.get("pan"),
                        dp_id=record.get("dp_id"),
                        seller=current_user,
                    )
                    db.session.add(pan)
                    db.session.commit()
            return redirect(url_for("all_pan"))
    except Exception as e:
        print(e)
        return e


# Bulk emails to all admins
# Not Checked
@app.route("/dashboard/bulk-emails/admins")
@login_required
def bulk_emails_admins():
    try:
        bulk_emails_sent_to_all_admins = Email.query.filter_by(bulk="Admin Email").all()
        emails = len(bulk_emails_sent_to_all_admins)
        return render_template(
            "admin/bulk_emails_admins.html",
            title="Bulk Emails Sent To All Admins",
            bulk_emails_sent_to_all_admins=bulk_emails_sent_to_all_admins,
            emails=emails,
        )
    except Exception as e:
        # Handle the exception here
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


# Bulk emails to all buyers
# Not Checked
@app.route("/dashboard/bulk-emails/buyers")
@login_required
def bulk_emails_buyers():
    try:
        bulk_emails_sent_to_all_buyers = Email.query.filter_by(bulk="buyer Email").all()
        emails = len(bulk_emails_sent_to_all_buyers)
        return render_template(
            "admin/bulk_emails_buyers.html",
            title="Bulk Emails Sent To All buyers",
            bulk_emails_sent_to_all_buyers=bulk_emails_sent_to_all_buyers,
            emails=emails,
        )
    except Exception as e:
        # Handle the exception here
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


# Bulk emails to all sellers
# Not Checked
@app.route("/dashboard/bulk-emails/sellers")
@login_required
def bulk_emails_sellers():
    try:
        bulk_emails_sent_to_all_sellers = Email.query.filter_by(bulk="buyer Email").all()
        emails = len(bulk_emails_sent_to_all_sellers)
        return render_template(
            "admin/bulk_emails_sellers.html",
            title="Bulk Emails Sent To All sellers",
            bulk_emails_sent_to_all_sellers=bulk_emails_sent_to_all_sellers,
            emails=emails,
        )
    except Exception as e:
        # Handle the exception here
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


# --------------------------------------
# End of bulk emails
# --------------------------------------

# ==========
# END OF DASHBOARD
# ==========


# @app.route("/rollback")
# def rollback():
#     pan = Pan.query.filter_by(seller=current_user)
#     for pans in pan:
#         db.session.delete(pans)
#         db.session.commit()
#     return redirect(url_for("all_pan"))

# # Only for Initial Setup, Delete after use
# @app.route("/del")
# def delete_det():
#     admin = Admin(
#         first_name="kavya",
#         last_name="Morakhiya",
#         username="kavya",
#         email="morakhiyakavya@gmail.com",
#         phone_number="7016184560",
#         current_residence="Ahmedabad,Gujarat",
#         # confirm_password="kavyaarya123.",
#         department="Super Admin",
#     )

#     buyer = Buyer(
#         first_name="Shrenik",
#         last_name="Morakhiya",
#         username="shrenik",
#         email="shrenik888@gmail.com",
#         phone_number="7016184560",
#         current_residence="Ahmedabad,Gujarat",
#         confirm_password="kavyaarya123.",
#     )

#     seller = Seller(
#         first_name="arya",
#         last_name="Morakhiya",
#         username="arya",
#         email="morakhiyakavya17@gmail.com",
#         phone_number="7016184560",
#         current_residence="Ahmedabad,Gujarat",
#         confirm_password="kavyaarya123.",
#         buyer_id=2,
#     )

#     # Show actual admin password in registration email
#     session["password"] = "kavyaarya123."
#     user_password = session["password"]

#     # Update the database
#     admin.set_password(user_password)
#     buyer.set_password(user_password)
#     seller.set_password(user_password)
#     db.session.add(admin)
#     db.session.add(buyer)
#     db.session.add(seller)
#     db.session.commit()

#     # Send admin an email with login credentials
#     send_login_details(admin, user_password)
#     send_login_details(buyer, user_password)
#     send_login_details(seller, user_password)

#     # Delete seller password session
#     del session["password"]

#     flash(
#         f"Successfully registered your admin {admin.username}! "
#         "An email has been sent to the admin on the next steps."
#     )
#     return "done"


# # This Deletes Everything from the table Pan and IPO, only for testing purpose delete after use
# @app.route("/del-ipo-det")
# def add_ipo_det():
#     product = User.query.all()
#     for i in product:
#         db.session.delete(i)
#         db.session.commit()
#     # pan = Pan.query.all()
#     # for i in pan:
#     #     db.session.delete(i)
#     #     db.session.commit()
#     return redirect(url_for("dashboard"))


# =========================================
# END OF AUTHENTICATED USERS
# =========================================

"""FLUTTER ROUTES"""

def generate_password(length=8):
    characters = string.ascii_letters + string.digits
    password = ''.join(random.choice(characters) for i in range(length))
    return password

@app.route('/submit-form', methods=['POST'])
def submit_form():
    data = request.json
    # Process the form data as needed
    ipoName = data.get('ipoName')
    seller_name = data.get('sellerName')
    extradetails = data.get('extradetails')
    number = data.get('sellerNumber')
    rate = data.get('rate')
    number_of_forms = data.get('numberOfForms')
    option = data.get('option')
    subject = data.get('subject')
    date_time = data.get('dateTime')
    date_time = datetime.fromisoformat(date_time)


    print(data)
    if len(number) > 10:
        number = number[-10:]
    
    seller = Seller.query.filter_by(phone_number=number).first()

    if not seller:
        print("Seller not found")
        # So Add that into Seller table
        # create a random 8 len password
        pass_word = generate_password()
        seller = Seller(
            first_name=seller_name,
            last_name = "",
            username = seller_name,
            email = pass_word+'@gmail.com',
            password_hash = pass_word,
            confirm_password = pass_word,
            phone_number=number,
            buyer_id=2,
        )
        db.session.add(seller)
        db.session.commit()
        print("Seller Added")
        seller = Seller.query.filter_by(phone_number=number).first()
    
    ipo = IPO.query.filter_by(name=ipoName).first()

    if not ipo:
        print("Ipo not found")
        # So Add that into Ipo table
        ipo = IPO(name=ipoName,
            status = "open",
            listing_date = date_time,
            open_date = date_time,
            close_date = date_time)
        db.session.add(ipo)
        db.session.commit()
        print("Ipo Added")
        ipo = IPO.query.filter_by(name=ipoName).first()
        
    # Now Add the details into the Details table
    details = Details(
        product_id=ipo.id,
        subject=subject,
        formtype=option,
        price=rate,
        quantity=number_of_forms,
        extra_details = extradetails,
        seller = seller,
    )
    db.session.add(details)
    db.session.commit()
    
    transaction = Transaction(
                    details_id=details.id,
                    product_id=ipo.id,
                    buyer_id=2,
                    seller_id=seller.id,
                )
    db.session.add(transaction)
    db.session.commit()
    # Process or save the data to the database here
    response = {
        'status': 'success',
        'message': 'Form submitted successfully',
        'data': data
    }
    print(response)
    return jsonify(response), 200


@app.route('/submit-contacts', methods=['POST'])
def submit_contacts():
    data = request.get_json()
    contacts = data.get('contacts', [])
    
    # Process the contacts as needed
    for contact in contacts:
        name = contact.get('name')
        number = contact.get('number')
        print("\n---------------------------------------------\n")
        print(f"Name: {name}, Number: {number}")
        print("\n---------------------------------------------\n")
    return jsonify({"message": "Contacts received successfully"}), 200


@app.route('/give-ipo',methods=['POST'])
def give_ipo():
    products = IPO.query.all()
    view_products = len(products)
    status_priority = {"open": 1, "closed": 2, "listed": 3}

    products.sort(
        key=lambda x: (status_priority.get(x.status, 4), x.listing_date)
    )
    product_list =[
                {
                    "name": product.name,
                }
                for product in products
            ]
    return jsonify({"products": product_list})


@app.route('/show-tables')
@login_required
def show_tables():
    if current_user.type == "admin":
        inspector = inspect(db.engine)
        metadata = MetaData()
        metadata.reflect(bind=db.engine)

        all_tables_data = {}

        # Get all table names
        table_names = inspector.get_table_names()

        for table_name in table_names:
            table = metadata.tables[table_name]

            # Fetch all rows from the table
            query = db.session.query(table).all()

            # Get column names
            columns = table.columns.keys()

            # Format rows as dictionaries
            table_data = [dict(zip(columns, row)) for row in query]
            all_tables_data[table_name] = table_data

        # Pass data to a template for display
        return render_template('show_tables.html', all_tables_data=all_tables_data)
    else:
        return flash_message()


# ================================================