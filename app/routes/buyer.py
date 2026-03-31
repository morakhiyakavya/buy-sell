from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from .blueprint import bp as app
from app import db
from app.forms import EmailForm
from app.models import Buyer, Admin, Email
from app.my_email import request_account_deletion, send_user_private_email
from .common import flash_message


@app.route("/buyer/profile", endpoint="buyer_profile")
@login_required
def buyer_profile():
    try:
        if current_user.type == "buyer":
            return render_template("buyer/profile.html", title="Buyer Profile")
        else:
            return flash_message()
    except Exception as e:
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


@app.route("/buyer/deactivate-account", endpoint="buyer_deactivate_account")
@login_required
def buyer_deactivate_account():
    try:
        buyer = Buyer.query.filter_by(username=current_user.username).first()

        admins = Admin.query.all()
        for admin in admins:
            request_account_deletion(admin, buyer)

        flash(
            "Your request has been sent to the admins. You will receive an email notification if approved"
        )
        return redirect(url_for("buyer_profile"))
    except Exception as e:
        flash("An error occurred while deactivating your account. Please try again later.")
        print(f"An error occurred: {e}")
        return redirect(url_for("buyer_profile"))


@app.route("/dashboard/compose-direct-email-to-a-buyer/<email>", methods=["GET", "POST"], endpoint="compose_direct_email_to_buyer")
@login_required
def compose_direct_email_to_buyer(email):
    """Write email to individual buyer"""
    try:
        buyer = Buyer.query.filter_by(email=email).first()
        buyer_username = buyer.email.split("@")[0].capitalize()
        session["buyer_email"] = buyer.email
        session["buyer_first_name"] = buyer.first_name

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
                bulk="buyer Email",
                author=current_user,
            )
            db.session.add(email_obj)
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


@app.route("/dashboard/emails-to-individual-buyers", endpoint="emails_to_individual_buyers")
@login_required
def emails_to_individual_buyers():
    """Emails sent out to individual buyers"""
    try:
        emails_sent_to_individual_buyer = Email.query.filter_by(bulk="buyer Email").all()
        emails = len(emails_sent_to_individual_buyer)
        return render_template(
            "admin/individual_buyer_email.html",
            title="Emails Sent To Individual buyers",
            emails_sent_to_individual_buyer=emails_sent_to_individual_buyer,
            emails=emails,
        )
    except Exception as e:
        flash("An error occurred while retrieving emails.", "danger")
        print(f"An error occurred: {e}")
        return redirect(url_for("dashboard"))


@app.route("/dashboard/all-buyers", endpoint="all_buyers")
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
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


@app.route("/dashboard/deactivate-buyer/<username>", endpoint="deactivate_buyer")
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


@app.route("/dashboard/reactivate-buyer/<username>", endpoint="reactivate_buyer")
@login_required
def reactivate_buyer(username):
    try:
        buyer = Buyer.query.filter_by(username=username).first_or_404()
        buyer.active = True
        db.session.add(buyer)
        db.session.commit()
        flash(f"{buyer.username} has been reactivated as a buyer")
        return redirect(url_for("all_buyers"))
    except Exception:
        flash("An error occurred while reactivating the buyer")
        return redirect(url_for("all_buyers"))


@app.route("/dashboard/delete-buyer/<username>", endpoint="delete_buyer")
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


@app.route("/send-email-to-buyer/<id>", endpoint="send_buyer_email")
@login_required
def send_buyer_email(id):
    """Send email to buyer from the database"""
    try:
        email = Email.query.filter_by(id=id).first()
        buyer_email = session["buyer_email"]
        buyer_first_name = session["buyer_first_name"]

        email.allow = True
        db.session.add(email)
        db.session.commit()

        send_user_private_email(email, buyer_email, buyer_first_name)

        flash(f"Email successfully sent to the teacher {buyer_email}")
        del session["buyer_email"]
        del session["buyer_first_name"]
        return redirect(url_for("emails_to_individual_buyers"))
    except Exception as e:
        flash(f"An error occurred while sending the email: {str(e)}")
        print(f"An error occurred: {e}")
        return redirect(url_for("emails_to_individual_buyers"))


@app.route("/edit-buyer-email/<id>", methods=["GET", "POST"], endpoint="edit_buyer_email")
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


@app.route("/delete-email-sent-to-a-buyer/<id>", endpoint="delete_buyer_email")
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
