import json
import os
from flask import (render_template, redirect, url_for, flash, request,
                    session, jsonify, send_file, abort)
from flask_login import current_user, login_user, logout_user, login_required
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
    User,
    Buyer,
    Seller,
    Admin,
    Email,
    Product,
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

from app import app, db
  

# =========================================
# USER AUTHENTICATION
# =========================================


def flash_message(): # An base level error message function
    if current_user.is_authenticated:
        flash(f"As a {current_user.type} you are not authorized to view the page.")
        return redirect(url_for("dashboard"))
    else:
        flash("You are not authorized to view the page. Please Login first.")
        return redirect(url_for("login"))


@app.route("/")
def home():
    return render_template("home.html", title="Home")


@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_authenticated:
        if current_user.type == "buyer":
            return redirect(url_for("buyer_profile"))
        if current_user.type == "seller":
            return redirect(url_for("seller_profile"))
        if current_user.type == "admin":
            return redirect(url_for("admin_profile"))


# Login


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login logic"""
    if current_user.is_authenticated:
        if current_user.type == "buyer":
            return redirect(url_for("dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password")
            return redirect(url_for("login"))
        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("dashboard")
        login_user(user, remember=form.remember_me.data)
        flash(f"Welcome {user.username}.")
        return redirect(next_page)
    return render_template("auth/login.html", title="Login", form=form)


# Logout


@app.route("/logout")
@login_required
def logout():
    """Logged in user can log out"""
    logout_user()
    return redirect(url_for("login"))


# Request password reset


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


@app.route("/register/buyer", methods=["GET", "POST"])
def register_buyer():
    """Buyer registration logic"""
    if current_user.is_authenticated:
        if current_user.type == "buyer":
            return redirect(url_for("dashboard"))
        if current_user.type == "seller":
            return redirect(url_for("dashboard"))
        if current_user.type == "admin":
            form = BuyerRegistrationForm()
            if form.validate_on_submit():
                buyer = Buyer(
                    first_name=form.first_name.data,
                    last_name=form.last_name.data,
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
                "auth/register_current_user.html", title="Register As A Buyer", form=form
            )
    else:
        return flash_message()


# seller registration


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

@app.route("/register/admin", methods=["GET", "POST"])
@login_required
def register_admin():
    """Admin registration logic"""
    if current_user.type == "admin":
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


@app.route("/admin/profile")
@login_required
def admin_profile():
    return render_template("admin/profile.html", title="Admin Profile")


# Compose direct email to admin


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


@app.route("/dashboard/all-admins")
@login_required
def all_admins():
    admins = Admin.query.all()
    all_registered_admins = len(admins)
    return render_template(
        "admin/all_admins.html",
        title="All Admins",
        admins=admins,
        all_registered_admins=all_registered_admins,
    )


# Deactivate admin


@app.route("/dashboard/deactivate-admin/<username>")
@login_required
def deactivate_admin(username):
    admin = Admin.query.filter_by(username=username).first_or_404()
    admin.active = False
    db.session.add(admin)
    db.session.commit()
    flash(f"{admin.username} has been deactivated as an admin")
    return redirect(url_for("all_admins"))


# Reactivate admin


@app.route("/dashboard/reactivate-admin/<username>")
@login_required
def reactivate_admin(username):
    admin = Admin.query.filter_by(username=username).first_or_404()
    admin.active = True
    db.session.add(admin)
    db.session.commit()
    flash(f"{admin.username} has been reactivated as an admin")
    return redirect(url_for("all_admins"))


# Delete admin


@app.route("/dashboard/delete-admin/<username>")
@login_required
def delete_admin(username):
    admin = Admin.query.filter_by(username=username).first_or_404()
    db.session.delete(admin)
    db.session.commit()
    flash(f"{admin.username} has been deleted as an admin")
    return redirect(url_for("all_admins"))

@app.route("/del")
def delete_det():
    admin = Seller(
                first_name='Shrenik',
                last_name='Morakhiya',
                username='shrenik',
                email='shrenik888@gmail.com',
                phone_number='7016184560',
                current_residence='Ahmedabad,Gujarat',
                confirm_password='kavyaarya123.',
                buyer_id = 2
            )

    # Show actual admin password in registration email
    session["password"] = 'kavyaarya123.'
    user_password = session["password"]

    # Update the database
    admin.set_password(user_password)
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


@app.route("/buyer/profile")
@login_required
def buyer_profile():
    return render_template("buyer/profile.html", title="Buyer Profile")


# Deactivate own account


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


@app.route("/dashboard/delete-buyer/<username>")
@login_required
def delete_buyer(username):
    buyer = Buyer.query.filter_by(username=username).first_or_404()
    db.session.delete(buyer)
    db.session.commit()
    flash(f"{buyer.username} has been deleted as a buyer")
    return redirect(url_for("all_buyers"))


# Send email to individual buyer


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



@app.route("/seller/deactivate-account")
@login_required
def seller_deactivate_account():
    # Get current user
    seller = Seller.query.filter_by(username=current_user.username).first()

    # Send email to all admins about the request to delete account
    admins = Admin.query.all()
    for admin in admins:
        request_account_deletion(admin, seller)

    flash(
        "Your request has been sent to the admins."
        " You will receive an email notification if approved"
    )
    return redirect(url_for("seller_profile"))


# Compose direct email to seller


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
        return redirect(url_for("emails_to_individual_seller"))
    return render_template(
        "admin/email_seller.html",
        title="Compose Private Email",
        form=form,
        seller=seller,
    )


# List of emails sent out to individual seller


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


@app.route("/dashboard/all-sellers")
@login_required
def all_sellers():
    sellers = Seller.query.all()
    all_registered_sellers = len(sellers)
    return render_template(
        "admin/all_sellers.html",
        title="All sellers",
        sellers=sellers,
        all_registered_sellers=all_registered_sellers,
    )


# Deactivate seller


@app.route("/dashboard/deactivate-seller/<username>")
@login_required
def deactivate_seller(username):
    seller = Seller.query.filter_by(username=username).first_or_404()
    seller.active = False
    db.session.add(seller)
    db.session.commit()
    flash(f"{seller.username} has been deactivated as a seller")
    return redirect(url_for("all_sellers"))


# Reactivate seller


@app.route("/dashboard/reactivate-seller/<username>")
@login_required
def reactivate_seller(username):
    seller = Seller.query.filter_by(username=username).first_or_404()
    seller.active = True
    db.session.add(seller)
    db.session.commit()
    flash(f"{seller.username} has been reactivated as a seller")
    return redirect(url_for("all_sellers"))


# Delete seller


@app.route("/dashboard/delete-seller/<username>")
@login_required
def delete_seller(username):
    seller = Seller.query.filter_by(username=username).first_or_404()
    db.session.delete(seller)
    db.session.commit()
    flash(f"{seller.username} has been deleted as a seller")
    return redirect(url_for("all_sellers"))


# Send email to individual seller


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
@app.route("/add-product", methods=["GET", "POST"])
@login_required
def add_product():
    if current_user.type == "buyer":
        form = ProductForm()
        if form.validate_on_submit():
            product = Product(
                name=form.name.data,
                description=form.description.data,
                buyer=current_user,
            )
            db.session.add(product)
            db.session.commit()
            flash("Product added successfully")
            return redirect(url_for("all_product"))

        return render_template(
            "Product/add_product.html", title="Add Product", form=form
        )

    # Add a return statement for cases when the current user type is not 'buyer'
    return flash_message()

@app.route("/del-ipo-det")
def add_ipo_det():
    product = IPO.query.all()
    for i in product:
        db.session.delete(i)
        db.session.commit()
    return "Done"

@app.route("/get-product")
def get_product():
    scraper = IPODetailsScraper(driver_path, 'chittorgarh', headless=True)

    ipo_details_green,ipo_details_lightyellow,ipo_details_aqua = scraper.scrape_ipo_details()
    # ipo_details_aqua = {'Name': 'Juniper Hotels Limited IPO', 'Open Date': '2021-09-30', 'Close Date': '2021-10-05', 'Listing Date': '2021-10-14', 'Price': '₹ 0', 'Issue Size': '₹ 0', 'Lot Size': '0', 'Listing At': 'BSE SME', 'Status': 'listed'}
    process_ipo_details(ipo_details_green, ipo_details_lightyellow, ipo_details_aqua)
    return "DOne"

def process_ipo_details(ipo_details_green, ipo_details_lightyellow, ipo_details_aqua):
    # Process green IPOs - Add new
    for ipo in ipo_details_green:
        if not IPO.query.filter_by(name=ipo['Name']).first():
            new_ipo = IPO(name=ipo['Name'], open_date=ipo['Open Date'], close_date=ipo['Close Date'],
                          listing_date=ipo['Listing Date'], price=ipo['Price'], issue_size=ipo['Issue Size'],
                          lot_size=ipo['Lot Size'], listing_at=ipo['Listing At'], status='Open')
            db.session.add(new_ipo)

    # Update status for lightyellow and aqua IPOs
    for status, ipos in [('closed', ipo_details_lightyellow), ('listed', ipo_details_aqua)]:
        for ipo in ipos:
            existing_ipo = IPO.query.filter_by(name=ipo['Name']).first()
            if existing_ipo:
                existing_ipo.status = status

    # Delete IPOs that are no longer aqua
    listed_ipos_names = [ipo['Name'] for ipo in ipo_details_aqua]
    for ipo in IPO.query.filter_by(status='listed').all():
        if ipo.name not in listed_ipos_names:
            db.session.delete(ipo)

    db.session.commit()

# Update Product
@app.route("/edit-product/<product_id>", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    if current_user.type == "buyer":

        return redirect(url_for("all_product"))


# Read All Product
@app.route("/all-product")
@login_required
def all_product():
    buyer_id = None  # Default value, for cases other than "buyer" or "seller"

    if current_user.type == "seller":
        buyer_id = current_user.buyer_id
    elif current_user.type == "buyer":
        buyer_id = current_user.id

    if buyer_id is not None:
        products = Product.query.filter_by(buyer_id=buyer_id).all()
        all_products = len(products)
        return render_template(
            "transaction/available_products.html",
            title="All Products",
            products=products,
            all_products=all_products,
        )
    elif current_user.type == "admin":
        products = Product.query.all()
        all_products = len(products)
        return render_template(
            "transaction/available_products.html",
            title="All Products",
            products=products,
            all_products=all_products,
        )
    else:
        return flash_message()

# View Product

# Read All Product
@app.route("/view-product")
@login_required
def view_product(): # Testing Feature
    buyer_id = None  # Default value, for cases other than "buyer" or "seller"

    if current_user.type == "seller":
        buyer_id = current_user.buyer_id
    elif current_user.type == "buyer":
        buyer_id = current_user.id

    if buyer_id is not None:
        products = IPO.query.all()
        view_products = len(products)
        return render_template(
            "transaction/view_products.html",
            title="All Products",
            products=products,
            view_products=view_products,
        )
    elif current_user.type == "admin":
        products = IPO.query.all()
        view_products = len(products)
        return render_template(
            "transaction/view_products.html",
            title="All Products",
            products=products,
            view_products=view_products,
        )
    else:
        return flash_message()


# Delete Product
@app.route("/delete-product/<id>")
@login_required
def delete_product(id):
    if current_user.type == "buyer":
        product = Product.query.filter_by(
            buyer_id=current_user.id, id=id
        ).first_or_404()
        db.session.delete(product)
        db.session.commit()
        flash(f"The Ipo {product.name} has been deleted")
        return redirect(url_for("all_product"))


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
@app.route("/add-pan", methods=["GET", "POST"])
@login_required
def add_pan():
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

    # Add a return statement for cases when the current user type is not 'buyer'
    return flash_message()



# Update pan
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


# Read Pan
@app.route("/all-pan")
@login_required
def all_pan():
    seller_id = None  # Delfault value, for cases other than "buyer" or "seller"

    if current_user.type == "seller":
        seller_id = current_user.id
    elif current_user.type == "buyer":
        seller_id = current_user.id

    if seller_id is not None:
        pans = Pan.query.filter_by(seller_id=seller_id).all()
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
@app.route("/add-details", methods=["GET", "POST"])
@login_required
def add_details():
    if current_user.type == "seller":
        print("Current ->",current_user)
        product_id = request.args.get('product_id', default=None, type=int)
        product_name = Product.query.filter_by(id=product_id).first_or_404()
        if product_id is None:
            flash("No Product Selected")
            return redirect(url_for("all_product"))
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
            print(details.id)
            transaction = Transaction(
                details_id=details.id,
                product_id = product_id,
                buyer_id = current_user.buyer_id,
                seller_id = current_user.id,
            )
            db.session.add(transaction)
            db.session.commit()
            flash("Details added successfully")
            return redirect(url_for("add_details",product_id=product_id))

        return render_template(
            "Details/add_details.html", title="Add Details", form=form,product_name=product_name
        )

    if current_user.type != "seller":
        return flash_message()

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
@app.route("/all-transactions")
@login_required
def all_transaction():
    if current_user.type == "seller":
        transactions = Transaction.query.filter_by(seller_id=current_user.id).all()
        all_transactions = len(transactions)
        return render_template(
            "transaction/all_transactions.html",
            title="All Transactions",
            transactions=transactions,
            all_transactions=all_transactions,
        )
    

# ----------
# End Of Curd On Transaction
# ----------



@app.route("/available-pans", methods=["GET", "POST"])
@login_required
def available_pans():
    if request.method == "POST":
        selected_ids = request.form.getlist('ID[]')
        print("Select ->",selected_ids)
        return jsonify({'status': 'success', 'selected_ids': selected_ids})
    else:
        if current_user.type == "seller":
            pans = Pan.query.filter_by(seller_id=current_user.id).all()
            all_pans = len(pans)
            return render_template(
                "transaction/available_pans.html",
                title="All Pans",
                pans=pans,
                all_pans=all_pans,
            )
        else:
            return flash_message()    
    
# --------------------------------------
# End of Related To Transaction
# --------------------------------------


# --------------------------------------
# Related To Checking allotment
# --------------------------------------

@app.route("/checking-allotment", methods=["GET", "POST"])
# @login_required
def checking_allotment():
    if current_user.is_authenticated:
        form = AllotmentForm()
        file_ready = False
        if form.validate_on_submit():
            folder_path = 'C:\\Users\\kavya\\Documents\\My_programming\\buy-sell\\myflaskapp\\app\\upload_folder'
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
            usernames = process_excel_data(filepath,pan_Column,start_Row,end_Row)
            # # Scraping the website
            results = scrape_data_from_websites(driver_path, listing_On, ipo, usernames, headless=False)
            with open(f"{ipo}.json", "w") as file:
               json.dump(results, file) # Save the results to a JSON file
            # Saving the results
            write_in_excel(filepath, results, pan_Column)
            file_ready = True
            return download_updated_file(filepath)
        return render_template(
            "allotment/check_allotment.html",
            title="Checking Allotment",
            form=form,
            file_ready=file_ready,
        )
    else:
        return flash_message()

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
