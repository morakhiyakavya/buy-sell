from datetime import datetime
# from cryptography.fernet import Fernet
import json
import os
import re
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
from app.excel import process_excel_data, write_in_excel

from app import app, db, socketio


# =========================================
# USER AUTHENTICATION
# =========================================

# Checked
def flash_message():  # An base level error message function
    if current_user.is_authenticated:
        flash(f"As a {current_user.type} you are not authorized to view the page.")
        return redirect(url_for("dashboard"))
    else:
        flash("You are not authorized to view the page. Please Login first.")
        return redirect(url_for("login"))

# Checked
@app.route("/")
def home():
    if current_user.is_authenticated: 
        return redirect(url_for("dashboard"))
    return render_template("home.html")

@app.route("/all-links")
@login_required
def all_links():
    if current_user.is_authenticated:
        urls = {}
        with app.test_request_context():
            for rule in app.url_map.iter_rules():
                # Skip endpoints that require arguments.
                if "GET" in rule.methods and len(rule.arguments) == 0:
                    try:
                        urls[rule.endpoint] = url_for(rule.endpoint)
                    except Exception as e:
                        # Handle or log the error for endpoints that still can't be built
                        print(f"Error building URL for endpoint '{rule.endpoint}': {e}")
        return render_template("all_links.html", urls=urls)



# @app.route("/allotment_file")
# def allotment_file():
#     file_path = "C:\\Users\\kavya\\Documents\\My_programming\\buy-sell\\myflaskapp\\app\\upload_folder\\ENSER_COM_-_PANCARD_-_Copy.xlsx"
#     return send_file(file_path, as_attachment=True)

# Checked
@app.route("/dashboard")
def dashboard():
        if current_user.type == "buyer":
            return redirect(url_for("buyer_profile"))
        if current_user.type == "seller":
            return redirect(url_for("seller_profile"))
        if current_user.type == "admin":
            return redirect(url_for("admin_profile"))


# Login
# Checked
@app.route("/login", methods=["GET", "POST"])
def login():
    """Login logic"""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password")
            return redirect(url_for("login"))
        if not user.is_active:
            flash('Your account is not active. Please contact support.')
            return redirect(url_for('home'))
        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("dashboard")
        login_user(user, remember=form.remember_me.data)
        flash(f"Welcome {user.username}.")
        return redirect(next_page)
    return render_template("auth/login.html", title="Login", form=form)


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
        "auth/register_anonymous_user.html", title="Request Password Reset", form=form
    )


# Reset password
# Not Checked for Buyer and Seller
@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """
    Time-bound link to reset password requested by an active user sent to their inbox
    """
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


# Buyer registration
# Checked
# Potential Updates : We might need to give other field to be filled by buyer and might send direct otp or link to user.
@app.route("/register/buyer", methods=["GET", "POST"])
def register_buyer():
    """Buyer registration logic"""
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


# seller registration
# Checked
# Potential Update : We need to check weather there is same username or not.
@app.route("/register/seller", methods=["GET", "POST"])
@login_required
def register_seller():
    """Seller registration logic"""
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


# Admin registration
# Checked
@app.route("/register/admin", methods=["GET", "POST"])
@login_required
def register_admin():
    """Admin registration logic"""
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
    if current_user.type == "admin":
        return render_template("admin/profile.html", title="Admin Profile")
    else:
        return flash_message()

# Compose direct email to admin
# Not Checked
@app.route(
    "/dashboard/compose-direct-email-to-an-admin/<email>", methods=["GET", "POST"]
)
@login_required
def compose_direct_email_to_admin(email):
    """Write email to individual admin"""
    # Get the teacher
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
        "admin/email_admin.html", title="Compose Private Email", form=form, admin=admin
    )


# List of emails sent out to individual admin
# Not Checked
@app.route("/dashboard/emails-to-individual-admins")
@login_required
def emails_to_individual_admins():
    """Emails sent out to individual admins"""
    emails_sent_to_individual_admins = Email.query.filter_by(bulk="Admin Email").all()
    emails = len(emails_sent_to_individual_admins)
    return render_template(
        "admin/individual_admin_email.html",
        title="Emails Sent To Individual Admins",
        emails_sent_to_individual_admins=emails_sent_to_individual_admins,
        emails=emails,
    )


# List all admins
# Not Checked
@app.route("/dashboard/all-admins")
@login_required
def all_admins():
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


# Deactivate admin
# Not Checked
@app.route("/dashboard/deactivate-admin/<username>")
@login_required
def deactivate_admin(username):
    if current_user.department == "Super Admin":
        admin = Admin.query.filter_by(username=username).first_or_404()
        admin.active = False
        db.session.add(admin)
        db.session.commit()
        flash(f"{admin.username} has been deactivated as an admin")
        return redirect(url_for("all_admins"))
    else:
        return flash_message()

# Reactivate admin
# Not Checked
@app.route("/dashboard/reactivate-admin/<username>")
@login_required
def reactivate_admin(username):
    if current_user.department == "Super Admin":
        admin = Admin.query.filter_by(username=username).first_or_404()
        admin.active = True
        db.session.add(admin)
        db.session.commit()
        flash(f"{admin.username} has been reactivated as an admin")
        return redirect(url_for("all_admins"))
    else:
        return flash_message()

# Delete admin
# Not Checked
@app.route("/dashboard/delete-admin/<username>")
@login_required
def delete_admin(username):
    if current_user.department == "Super Admin":
        admin = Admin.query.filter_by(username=username).first_or_404()
        db.session.delete(admin)
        db.session.commit()
        flash(f"{admin.username} has been deleted as an admin")
        return redirect(url_for("all_admins"))
    else:
        return flash_message()
    
# Only for Initial Setup, Delete after use
@app.route("/del")
def delete_det():
    admin = Admin(
        first_name="kavya",
        last_name="Morakhiya",
        username="kavya",
        email="morakhiyakavya@gmail.com",
        phone_number="7016184560",
        current_residence="Ahmedabad,Gujarat",
        # confirm_password="kavyaarya123.",
        department = "Super Admin",
    )

    buyer = Buyer(
        first_name="Shrenik",
        last_name="Morakhiya",
        username="shrenik",
        email="shrenik888@gmail.com",
        phone_number="7016184560",
        current_residence="Ahmedabad,Gujarat",
        confirm_password="kavyaarya123.",
    )

    seller = Seller(
        first_name="arya",
        last_name="Morakhiya",
        username="arya",
        email="arya@gmail.com",
        phone_number="7016184560",
        current_residence="Ahmedabad,Gujarat",
        confirm_password="kavyaarya123.",
        buyer_id=2,
    )

    # Show actual admin password in registration email
    session["password"] = "kavyaarya123."
    user_password = session["password"]

    # Update the database
    admin.set_password(user_password)
    buyer.set_password(user_password)
    seller.set_password(user_password)
    db.session.add(admin)
    db.session.add(buyer)
    db.session.add(seller)
    db.session.commit()

    # Send admin an email with login credentials
    send_login_details(admin, user_password)
    send_login_details(buyer, user_password)
    send_login_details(seller, user_password)

    # Delete seller password session
    del session["password"]

    flash(
        f"Successfully registered your admin {admin.username}! "
        "An email has been sent to the admin on the next steps."
    )
    return "done"
    # product = Pan(
    #             name='shrenik',
    #             pan_number='omops4188o'.upper(),
    #             dp_id='258481551258',
    #             seller_id=4,
    #         )
    # db.session.add(product)
    # db.session.commit()
    # # flash("Product added successfully")
    # return "Done"


# Send email to individual admin
# Not Checked
@app.route("/send-email-to-admin/<id>")
@login_required
def send_admin_email(id):
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


# Edit sample email
# Not Checked
@app.route("/edit-admin-email/<id>", methods=["GET", "POST"])
@login_required
def edit_admin_email(id):
    """Edit email to admin from the database"""
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


# Delete email from database
# Not Checked
@app.route("/delete-email-sent-to-a-admin/<id>")
@login_required
def delete_admin_email(id):
    """Delete email to user from the database"""
    email = Email.query.filter_by(id=id).first()
    db.session.delete(email)
    db.session.commit()
    flash("Email successfully deleted")
    del session["admin_email"]
    del session["admin_first_name"]
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
    if current_user.type == "buyer":
        return render_template("buyer/profile.html", title="Buyer Profile")
    else :
        return flash_message()

# Deactivate own account
# Not Checked
@app.route("/buyer/deactivate-account")
@login_required
def buyer_deactivate_account():
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


# Compose direct email to buyer
# Not Checked
@app.route(
    "/dashboard/compose-direct-email-to-a-buyer/<email>", methods=["GET", "POST"]
)
@login_required
def compose_direct_email_to_buyer(email):
    """Write email to individual buyer"""
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
        "admin/email_buyer.html", title="Compose Private Email", form=form, buyer=buyer
    )


# List of emails sent out to individual buyer
# Not Checked
@app.route("/dashboard/emails-to-individual-buyers")
@login_required
def emails_to_individual_buyers():
    """Emails sent out to individual buyers"""
    emails_sent_to_individual_buyer = Email.query.filter_by(bulk="buyer Email").all()
    emails = len(emails_sent_to_individual_buyer)
    return render_template(
        "admin/individual_buyer_email.html",
        title="Emails Sent To Individual buyers",
        emails_sent_to_individual_buyer=emails_sent_to_individual_buyer,
        emails=emails,
    )


# List all buyers
# Not Checked
@app.route("/dashboard/all-buyers")
@login_required
def all_buyers():
    buyers = Buyer.query.all()
    all_registered_buyers = len(buyers)
    return render_template(
        "admin/all_buyers.html",
        title="All buyers",
        buyers=buyers,
        all_registered_buyers=all_registered_buyers,
    )


# Deactivate buyer
# Not Checked
@app.route("/dashboard/deactivate-buyer/<username>")
@login_required
def deactivate_buyer(username):
    buyer = Buyer.query.filter_by(username=username).first_or_404()
    buyer.active = False
    db.session.add(buyer)
    db.session.commit()
    flash(f"{buyer.username} has been deactivated as a buyer")
    return redirect(url_for("all_buyers"))


# Reactivate buyer
# Not Checked
@app.route("/dashboard/reactivate-buyer/<username>")
@login_required
def reactivate_buyer(username):
    buyer = Buyer.query.filter_by(username=username).first_or_404()
    buyer.active = True
    db.session.add(buyer)
    db.session.commit()
    flash(f"{buyer.username} has been reactivated as a buyer")
    return redirect(url_for("all_buyers"))


# Delete buyer
# Not Checked
@app.route("/dashboard/delete-buyer/<username>")
@login_required
def delete_buyer(username):
    buyer = Buyer.query.filter_by(username=username).first_or_404()
    db.session.delete(buyer)
    db.session.commit()
    flash(f"{buyer.username} has been deleted as a buyer")
    return redirect(url_for("all_buyers"))


# Send email to individual buyer
# Not Checked
@app.route("/send-email-to-buyer/<id>")
@login_required
def send_buyer_email(id):
    """Send email to buyer from the database"""
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


# Edit sample email
# Not Checked
@app.route("/edit-buyer-email/<id>", methods=["GET", "POST"])
@login_required
def edit_buyer_email(id):
    """Edit email to buyer from the database"""
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


# Delete email from database
# Not Checked
@app.route("/delete-email-sent-to-a-buyer/<id>")
@login_required
def delete_buyer_email(id):
    """Delete email to buyer from the database"""
    email = Email.query.filter_by(id=id).first()
    db.session.delete(email)
    db.session.commit()
    flash("Email successfully deleted")
    del session["buyer_email"]
    del session["buyer_first_name"]
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

# Deactivate seller
# Not Checked
@app.route("/seller/deactivate-account")
@login_required
def seller_deactivate_account():
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


# Compose direct email to seller
# Not Checked
@app.route(
    "/dashboard/compose-direct-email-to-a-seller/<email>", methods=["GET", "POST"]
)
@login_required
def compose_direct_email_to_seller(email):
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


# List of emails sent out to individual seller
# Not Checked
@app.route("/dashboard/emails-to-individual-sellers")
@login_required
def emails_to_individual_sellers():
    """Emails sent out to individual seller"""
    emails_sent_to_individual_seller = Email.query.filter_by(bulk="seller Email").all()
    emails = len(emails_sent_to_individual_seller)
    return render_template(
        "admin/individual_seller_email.html",
        title="Emails Sent To Individual sellers",
        emails_sent_to_individual_seller=emails_sent_to_individual_seller,
        emails=emails,
    )

# List all sellers
# Not Checked
@app.route("/dashboard/all-sellers")
@login_required
def all_sellers():
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


# Deactivate seller
# Checked
@app.route("/dashboard/deactivate-seller/<username>")
@login_required
def deactivate_seller(username):
    if current_user.type == "buyer" or current_user.type == "admin":
        seller = Seller.query.filter_by(username=username).first_or_404()
        seller.active = False
        db.session.add(seller)
        db.session.commit()
        flash(f"{seller.username} has been deactivated as a seller")
        return redirect(url_for("all_sellers"))
    else:
        return flash_message()

# Reactivate seller
# Checked
@app.route("/dashboard/reactivate-seller/<username>")
@login_required
def reactivate_seller(username):
    if current_user.type == "buyer" or current_user.type == "admin":
        seller = Seller.query.filter_by(username=username).first_or_404()
        seller.active = True
        db.session.add(seller)
        db.session.commit()
        flash(f"{seller.username} has been reactivated as a seller")
        return redirect(url_for("all_sellers"))
    else:
        return flash_message()

# Delete seller
# Checked
@app.route("/dashboard/delete-seller/<username>")
@login_required
def delete_seller(username):
    # if current_user.type == "admin" or current_user.type == "seller":
    if current_user.is_authenticated:
        seller = Seller.query.filter_by(username=username).first_or_404()
        db.session.delete(seller)
        db.session.commit()
        flash(f"{seller.username} has been deleted as a seller")
        return redirect(url_for("all_sellers"))
    else:
        return flash_message()

# Send email to individual seller
# Not Checked
@app.route("/send-email-to-seller/<id>")
@login_required
def send_seller_email(id):
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


# Edit sample email
# Not Checked
@app.route("/edit-seller-email/<id>", methods=["GET", "POST"])
@login_required
def edit_seller_email(id):
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


# Delete email from database
# Not Checked
@app.route("/delete-email-sent-to-a-seller/<id>")
@login_required
def delete_seller_email(id):
    """Delete email to seller from the database"""
    email = Email.query.filter_by(id=id).first()
    db.session.delete(email)
    db.session.commit()
    flash("Email successfully deleted")
    del session["seller_email"]
    del session["seller_first_name"]
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


# Creating Product
# Access to Buyer Only
# @app.route("/add-product", methods=["GET", "POST"])
# @login_required
# def add_product():
#     if current_user.type == "buyer":
#         form = ProductForm()
#         if form.validate_on_submit():
#             product = Product(
#                 name=form.name.data,
#                 description=form.description.data,
#                 buyer=current_user,
#             )
#             db.session.add(product)
#             db.session.commit()
#             flash("Product added successfully")
#             return redirect(url_for("all_product"))

#         return render_template(
#             "Product/add_product.html", title="Add Product", form=form
#         )

#     # Add a return statement for cases when the current user type is not 'buyer'
#     return flash_message()

# This Deletes Everything from the table, only for testing purpose delete after use
@app.route("/del-ipo-det")
def add_ipo_det():
    product = Pan.query.all()
    for i in product:
        db.session.delete(i)
        db.session.commit()
    return "Done"


# Getting current ipo from chittorgarh
# Checked
@app.route("/get-product") 
def get_product():
    scraper = IPODetailsScraper(driver_path, "chittorgarh", headless=True)

    ipo_details_green, ipo_details_lightyellow, ipo_details_aqua = (
        scraper.scrape_ipo_details()
    )
    process_ipo_details(ipo_details_green, ipo_details_lightyellow, ipo_details_aqua)
    return redirect(url_for("view_product"))

# ipo status and name assigninig
# Checked
# Potential Updates : Analysze more.
def process_ipo_details(ipo_details_green, ipo_details_lightyellow, ipo_details_aqua):
    # Process green IPOs - Add new
    # for ipo in ipo_details_green:
    #     if not IPO.query.filter_by(name=ipo["Name"]).first():
    #         open_date_sort = datetime.strptime(ipo["Open Date"], "%b %d, %Y")
    #         close_date_sort = datetime.strptime(ipo["Close Date"], "%b %d, %Y")
    #         listing_date_sort = datetime.strptime(ipo["Listing Date"], "%b %d, %Y")
    #         name = clean_name(ipo["Name"])
    #         status = "Open"
    #         new_ipo = IPO(
    #             name=name,
    #             price=ipo["Price"],
    #             issue_size=ipo["Issue Size"],
    #             lot_size=ipo["Lot Size"],
    #             open_date= open_date_sort,
    #             close_date= close_date_sort,
    #             listing_date= listing_date_sort,
    #             listing_at=ipo["Listing At"],
    #             status=status,
    #         )
    #         db.session.add(new_ipo)
    #         db.session.commit()

    # Process light yellow IPOs - Update existing
    update_ipo_status(ipo_details_green, "open")
    update_ipo_status(ipo_details_lightyellow, "closed")
    update_ipo_status(ipo_details_aqua, "listed")

# Update ipo status
# Checked
def update_ipo_status(ipo_details, status):
    for ipo in ipo_details:
        name = clean_name(ipo["Name"])
        ipo_db = IPO.query.filter_by(name=name).first()
        if ipo_db:
            if status != "open": 
                ipo_db.status = status
                db.session.commit()
        else :
            open_date_sort = datetime.strptime(ipo["Open Date"], "%b %d, %Y")
            close_date_sort = datetime.strptime(ipo["Close Date"], "%b %d, %Y")
            listing_date_sort = datetime.strptime(ipo["Listing Date"], "%b %d, %Y")
            # name = clean_name(ipo["Name"])
            new_ipo = IPO(
                name=name,
                price=ipo["Price"],
                issue_size=ipo["Issue Size"],
                lot_size=ipo["Lot Size"],
                open_date= open_date_sort,
                close_date= close_date_sort,
                listing_date= listing_date_sort,
                listing_at=ipo["Listing At"],
                status=status,
            )
            db.session.add(new_ipo)
            db.session.commit()

# Make the ipo name smaller
# Checked
def clean_name(name):
    # Combine all patterns, prioritizing longer/more specific patterns to ensure they're matched first
    pattern = r'( PUBLIC LIMITED IPO\.? ?| LIMITED IPO\.? ?| PUBLIC LIMITED\.? ?| LTD IPO\.? ?|LIMITED\.? ?| LTD\.? ?| IPO)$'
    # Use re.IGNORECASE to make the pattern case-insensitive
    cleaned_name = re.sub(pattern, '', name, flags=re.IGNORECASE)
    return cleaned_name


# # Update Product
# @app.route("/edit-product/<product_id>", methods=["GET", "POST"])
# @login_required
# def edit_product(product_id):
#     if current_user.type == "buyer":

#         return redirect(url_for("all_product"))


# Read All Product
# @app.route("/all-product")
# @login_required
# def all_product():
#     buyer_id = None  # Default value, for cases other than "buyer" or "seller"

#     if current_user.type == "seller":
#         buyer_id = current_user.buyer_id
#     elif current_user.type == "buyer":
#         buyer_id = current_user.id

#     if buyer_id is not None:
#         products = Product.query.filter_by(buyer_id=buyer_id).all()
#         all_products = len(products)
#         return render_template(
#             "transaction/available_products.html",
#             title="All Products",
#             products=products,
#             all_products=all_products,
#         )
#     elif current_user.type == "admin":
#         products = Product.query.all()
#         all_products = len(products)
#         return render_template(
#             "transaction/available_products.html",
#             title="All Products",
#             products=products,
#             all_products=all_products,
#         )
#     else:
#         return flash_message()


# View Product


# Shows all the ipo's
# Checked
@app.route("/view-product")
@login_required
def view_product():  # Testing Feature
    if session.get("temp_details") is not None:
        session.pop('temp_details', None)
        print("Session pop")
    
    if current_user.is_authenticated :

        products = IPO.query.all()
        view_products = len(products)
        status_priority = {"open": 1, "closed": 2, "listed": 3}
        
        products.sort(key=lambda x: (status_priority.get(x.status, 4), x.listing_date))
        return render_template(
            #"Product/all_products.html",
            "transaction/view_products.html",
            title="Running Ipo's ",
            products=products,
            view_products=view_products,
        )
    else:
        return flash_message()


# Delete Product
# @app.route("/delete-product/<id>")
# @login_required
# def delete_product(id):
#     if current_user.type == "buyer":
#         product = Product.query.filter_by(
#             buyer_id=current_user.id, id=id
#         ).first_or_404()
#         db.session.delete(product)
#         db.session.commit()
#         flash(f"The Ipo {product.name} has been deleted")
#         return redirect(url_for("all_product"))


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
    if current_user.type == "seller":
        form = PanForm()
        if form.validate_on_submit():
            # f = Fernet(current_user.encrypted_key)
            # encrypt = form.pan_number.data.upper().encode()
            # encrypted_data = f.encrypt(encrypt)
            pan = Pan(
                name=form.name.data,
                pan_number=form.pan_number.data.upper(),
                # encrypt_pan=encrypted_data,
                dp_id=form.dp_id.data,
                seller=current_user,
            )
            db.session.add(pan)
            db.session.commit()
            flash("Pan added successfully")
            return redirect(url_for("all_pan"))

        # Add the following return statement for cases when form validation fails
        flash("Pan addition failed. Please check the form.")
        return render_template("Pan/add_pan.html", title="Add Pan", form=form)

    # Add a return statement for cases when the current user type is not 'buyer'
    return flash_message()


# Update pan
# Not Checked(left)
@app.route("/edit-pan", methods=["GET", "POST"])
@login_required
def edit_pan():
    if current_user.type == "seller":
        form = PanForm()
        if form.validate_on_submit():
            pan = Pan(
                name=form.name.data,
                pan_number=form.pan_number.data.upper(),
                dp_id=form.dp_id.data,
                seller=current_user,
            )
            db.session.add(pan)
            db.session.commit()
            flash("Pan added successfully")
            return redirect(url_for("all_pan"))

        # Add the following return statement for cases when form validation fails
        flash("Pan addition failed. Please check the form.")
        return render_template("Pan/add_pan.html", title="Add Pan", form=form)
    return redirect(url_for("all-pan"))

# Multi Pan
# For Adding too many pans at once, for testing purpose only delete after use
@app.route("/multi-pan")
def multi_pan():
    for i in range(10):
        for j in range(10):
            import random
            import string
            from faker import Faker
            fake = Faker()
            name = fake.name()
            random_string = ''.join(random.choice(string.ascii_letters) for _ in range(4))
            random_number = random.randint(1000, 9999)
            one = ''.join(random.choice(string.ascii_letters) for _ in range(1))
            pan = Pan(
                name=f"{name}",
                pan_number= f"{random_string}{random_number}{one}".upper(),
                dp_id= random.randint(1000000000, 9999999999),
                seller_id=3,
        )
            db.session.add(pan)
            db.session.commit()
    return redirect(url_for("all_pan"))

# Read Pan
# Checked
# Potential Updates : Buyer can not see the pan's of seller so we need to give something else in navbar
@app.route("/all-pan")
@login_required
def all_pan():
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


# Delete Pan
# Checked
@app.route("/delete-pan/<id>")
@login_required
def delete_pan(id):
    if current_user.type == "seller":
        pan = Pan.query.filter_by(seller_id=current_user.id, id=id).first_or_404()
        db.session.delete(pan)
        db.session.commit()
        flash(f"The Pan {pan.name}({pan.pan_number}) has been deleted")
        return redirect(url_for("all_pan"))

    return flash_message()


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
            extra_details= Details.query.filter(Details.id.in_(session["temp_details"])).all(),
        )

    if current_user.type != "seller":
        return flash_message()
    
# @app.route("/delete-subject")
# @login_required
# def delete_subject():
#     if current_user.type == "seller":
#         subject = Details.query.all()
#         print("Subject ->",subject)
#         for i in subject:
#             db.session.delete(i)
#             db.session.commit()
#         # flash(f"The Subject {subject.name}({subject.subject_code}) has been deleted")
#         return redirect(url_for("all_subject"))

#     flash("You are not authorized to view this page.")
#     return redirect(url_for("dashboard"))



"""
# Update Subject
@app.route("/edit-subject", methods=["GET", "POST"])
@login_required
def edit_subject():
    if current_user.type == "seller":
        form = SubjectForm()
        if form.validate_on_submit():
            subject = Subject(subject_code=form.subject_code.data)
            db.session.add(subject)
            db.session.commit()
            flash("Subject edited ")
            return redirect(url_for("all_subject"))

        # Add the following return statement for cases when form validation fails
        flash("Subject addition failed. Please check the form.")
        return render_template(
            "Subject/add_subject.html", title="Add Subject", form=form
        )
    return redirect(url_for("all_subject"))


# Read Subject
@app.route("/all-subject")
@login_required
def all_subject():
    seller_id = None

    if current_user.type == "seller":
        seller_id = current_user.id
    elif current_user.type == "buyer":
        seller_id = current_user.id

    if seller_id is not None:
        subjects = Subject.query.filter_by(seller_id=seller_id).all()
        all_subjects = len(subjects)
        return render_template(
            "Subject/all_subjects.html",
            title="All Subjects",
            subjects=subjects,
            all_subjects=all_subjects,
        )
    # elif current_user.type == "admin":

    else:
        flash("You are not authorized to view this page.")
        return redirect(url_for("dashboard"))


# Delete Subject
@app.route("/delete-subject/<id>")
@login_required
def delete_subject(id):
    if current_user.type == "seller":
        subject = Subject.query.filter_by(
            seller_id=current_user.id, id=id
        ).first_or_404()
        db.session.delete(subject)
        db.session.commit()
        flash(f"The Subject {subject.name}({subject.subject_code}) has been deleted")
        return redirect(url_for("all_subject"))

    flash("You are not authorized to view this page.")
    return redirect(url_for("dashboard"))


# --------------------------------------
# End of Subject
# --------------------------------------

"""

# ----------
# End Of Curd On Subject
# ----------

# ----------
# Curd On Transaction
# ----------


# Read Transaction
# Checked
@app.route("/all-transactions")
@login_required
def all_transaction():
    if session.get("temp_details") is not None:
        session.pop("temp_details", None)
        print("Session pop")
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

def count_pan(transaction_id):
    count = TransactionPan.query.filter_by(transaction_id=transaction_id).count()
    return count

# ----------
# End Of Curd On Transaction
# ----------

# Available Pans for transaction
# Checked
@app.route("/available-pans", methods=["GET", "POST"])
@login_required
def available_pans():
    if current_user.type == "seller":
        transaction_id = request.args.get("transaction_id", type=int)
        transaction = Transaction.query.get_or_404(transaction_id)
        count = count_pan(transaction_id)
        if request.method == "GET":
            pans = Pan.query.filter_by(seller_id=current_user.id).all()
            all_pans = len(pans)
            return render_template(
                "transaction/available_pans.html",
                title="All Pans",
                pans=pans,
                all_pans=all_pans,
                transaction=transaction  # Pass transaction to template to use its details
            )
        elif request.method == "POST":
            selected_ids = request.form.getlist("ID[]")
            print("Selected Ids ->", selected_ids)
            required_pans = transaction.details.quantity
            print("Required Pans ->", required_pans)
            
            if len(selected_ids) > required_pans:
                # Redirect back with an error message if the selected pans don't match required quantity exactly
                flash(f"You must select exactly {required_pans} pans. You selected {len(selected_ids)}.")
                return redirect(url_for("available_pans", transaction_id=transaction_id))
            elif len(selected_ids) <= required_pans:
                # Process exactly matched number of selected pans
                for selected_id in selected_ids:
                    print("transaction_id ->", transaction_id)
                    transaction_pan = TransactionPan(
                        transaction_id=transaction_id,
                        pan_id=int(selected_id)
                    )
                    db.session.add(transaction_pan)
                db.session.commit()
                flash("The transaction has been updated successfully.")
                return redirect(url_for("all_transaction"))
    else:
        # Handle non-seller users or redirect as needed
        flash("You are not authorized to view this page.")
        return redirect(url_for("index")) 
# --------------------------------------
# End of Related To Transaction
# --------------------------------------


# --------------------------------------
# Related To Checking allotment
# --------------------------------------

# Checking Allotment
# Checked
@app.route("/checking-allotment", methods=["GET", "POST"])
@login_required
def checking_allotment():
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
            # # Scraping the website
            print("Socket ->", socketio)
            results = scrape_data_from_websites(
                driver_path, listing_On, ipo, usernames, room, socketio, headless=False
            )
            with open(f"json/{ipo}.json", "w") as file:
                json.dump(results, file)  # Save the results to a JSON file
            # Saving the results
            write_in_excel(filepath, results, pan_Column)
            file_ready = True
            return download_updated_file(filepath)
        return render_template(
            "allotment/check_allotment.html",
            title="Checking Allotment",
            form=form,
            file_ready=file_ready,
            room = room
        )
    else:
        return flash_message()

@socketio.on('join')
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


# Bulk emails to all admins
# Not Checked
@app.route("/dashboard/bulk-emails/admins")
@login_required
def bulk_emails_admins():
    bulk_emails_sent_to_all_admins = Email.query.filter_by(bulk="Admin Email").all()
    emails = len(bulk_emails_sent_to_all_admins)
    return render_template(
        "admin/bulk_emails_admins.html",
        title="Bulk Emails Sent To All Admins",
        bulk_emails_sent_to_all_admins=bulk_emails_sent_to_all_admins,
        emails=emails,
    )


# Bulk emails to all buyers
# Not Checked
@app.route("/dashboard/bulk-emails/buyers")
@login_required
def bulk_emails_buyers():
    bulk_emails_sent_to_all_buyers = Email.query.filter_by(bulk="buyer Email").all()
    emails = len(bulk_emails_sent_to_all_buyers)
    return render_template(
        "admin/bulk_emails_buyers.html",
        title="Bulk Emails Sent To All buyers",
        bulk_emails_sent_to_all_buyers=bulk_emails_sent_to_all_buyers,
        emails=emails,
    )


# Bulk emails to all sellers
# Not Checked
@app.route("/dashboard/bulk-emails/sellers")
@login_required
def bulk_emails_sellers():
    bulk_emails_sent_to_all_sellers = Email.query.filter_by(bulk="buyer Email").all()
    emails = len(bulk_emails_sent_to_all_sellers)
    return render_template(
        "admin/bulk_emails_sellers.html",
        title="Bulk Emails Sent To All sellers",
        bulk_emails_sent_to_all_sellers=bulk_emails_sent_to_all_sellers,
        emails=emails,
    )


# --------------------------------------
# End of bulk emails
# --------------------------------------

# ==========
# END OF DASHBOARD
# ==========


# =========================================
# END OF AUTHENTICATED USERS
# =========================================
