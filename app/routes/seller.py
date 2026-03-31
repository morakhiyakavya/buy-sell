from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from .blueprint import bp as app
from app import db
from app.forms import EditUsernameForm, EditEmailForm, EditPhoneForm, EmailForm
from app.models import Seller, Buyer, Email
from app.my_email import request_account_deletion, send_user_private_email
from .common import flash_message


@app.route("/seller/profile", methods=["GET", "POST"], endpoint="seller_profile")
@login_required
def seller_profile():
    try:
        if current_user.type == "seller":
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
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


@app.route("/seller/deactivate-account", endpoint="seller_deactivate_account")
@login_required
def seller_deactivate_account():
    try:
        seller = Seller.query.filter_by(username=current_user.username).first()
        buyer = Buyer.query.filter_by(id=seller.buyer_id).first()
        request_account_deletion(buyer, seller)
        flash(
            "Your request has been sent to the admins. You will receive an email notification if approved"
        )
        return redirect(url_for("seller_profile"))
    except Exception as e:
        flash("An error occurred while deactivating your account. Please try again later.")
        print(f"An error occurred: {e}")
        return redirect(url_for("seller_profile"))


@app.route("/dashboard/compose-direct-email-to-a-seller/<email>", methods=["GET", "POST"], endpoint="compose_direct_email_to_seller")
@login_required
def compose_direct_email_to_seller(email):
    try:
        seller = Seller.query.filter_by(email=email).first()
        seller_username = seller.email.split("@")[0].capitalize()
        session["seller_email"] = seller.email
        session["seller_first_name"] = seller.first_name

        form = EmailForm()
        form.signature.choices = [
            (current_user.first_name.capitalize(), current_user.first_name.capitalize())
        ]
        if form.validate_on_submit():
            email_obj = Email(
                subject=form.subject.data,
                body=form.body.data,
                closing=form.closing.data,
                signature=form.signature.data,
                bulk="seller Email",
                author=current_user,
            )
            db.session.add(email_obj)
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
        print(f"An error occurred: {e}")
        flash(f"An error occurred: {str(e)}")
        return redirect(url_for("emails_to_individual_sellers"))


@app.route("/dashboard/emails-to-individual-sellers", endpoint="emails_to_individual_sellers")
@login_required
def emails_to_individual_sellers():
    try:
        emails_sent_to_individual_seller = Email.query.filter_by(bulk="seller Email").all()
        emails = len(emails_sent_to_individual_seller)
        return render_template(
            "admin/individual_seller_email.html",
            title="Emails Sent To Individual sellers",
            emails_sent_to_individual_seller=emails_sent_to_individual_seller,
            emails=emails,
        )
    except Exception as e:
        print(f"An error occurred: {e}")
        flash("An error occurred while retrieving emails.")
        return redirect(url_for("dashboard"))


@app.route("/dashboard/all-sellers", endpoint="all_sellers")
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
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


@app.route("/dashboard/deactivate-seller/<username>", endpoint="deactivate_seller")
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
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


@app.route("/dashboard/reactivate-seller/<username>", endpoint="reactivate_seller")
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
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


@app.route("/dashboard/delete-seller/<username>", endpoint="delete_seller")
@login_required
def delete_seller(username):
    try:
        if current_user.is_authenticated:
            seller = Seller.query.filter_by(username=username).first_or_404()
            if current_user.type == "buyer":
                if (
                    seller.buyer_id == current_user.id
                    or current_user.department == "Super Admin"
                    or current_user.id == seller.id
                ):
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
        print(f"Error deleting seller: {e}")
        return f"Error : {e}", 400


@app.route("/send-email-to-seller/<id>", endpoint="send_seller_email")
@login_required
def send_seller_email(id):
    try:
        email = Email.query.filter_by(id=id).first()
        seller_email = session["seller_email"]
        seller_first_name = session["seller_first_name"]

        email.allow = True
        db.session.add(email)
        db.session.commit()

        send_user_private_email(email, seller_email, seller_first_name)

        flash(f"Email successfully sent to the teacher {seller_email}")
        del session["seller_email"]
        del session["seller_first_name"]
        return redirect(url_for("emails_to_individual_sellers"))
    except Exception as e:
        flash(f"An error occurred while sending the email: {str(e)}")
        print(f"An error occurred: {e}")
        return redirect(url_for("emails_to_individual_sellers"))


@app.route("/edit-seller-email/<id>", methods=["GET", "POST"], endpoint="edit_seller_email")
@login_required
def edit_seller_email(id):
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
            return redirect(url_for("emails_to_individual_sellers"))
        if request.method == "GET":
            form.subject.data = email.subject
            form.body.data = email.body
            form.signature.data = email.signature
        return render_template(
            "admin/edit_email.html", title="Edit Sample Email", form=form
        )
    except Exception as e:
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


@app.route("/delete-email-sent-to-a-seller/<id>", endpoint="delete_seller_email")
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
