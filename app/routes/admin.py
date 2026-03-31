from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from .blueprint import bp as app
from app import db
from app.forms import EmailForm
from app.models import Admin, Email
from app.my_email import send_user_private_email
from .common import flash_message


@app.route("/admin/profile", endpoint="admin_profile")
@login_required
def admin_profile():
    try:
        if current_user.type == "admin":
            return render_template("admin/profile.html", title="Admin Profile")
        else:
            return flash_message()
    except Exception as e:
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


@app.route("/dashboard/compose-direct-email-to-an-admin/<email>", methods=["GET", "POST"], endpoint="compose_direct_email_to_admin")
@login_required
def compose_direct_email_to_admin(email):
    """Write email to individual admin"""
    try:
        admin = Admin.query.filter_by(email=email).first()
        admin_username = admin.email.split("@")[0].capitalize()
        session["admin_email"] = admin.email
        session["admin_first_name"] = admin.first_name

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
                bulk="Admin Email",
                author=current_user,
            )
            db.session.add(email_obj)
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


@app.route("/dashboard/emails-to-individual-admins", endpoint="emails_to_individual_admins")
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
        print(f"Error occurred: {e}")
        return f"Error : {e}", 400


@app.route("/dashboard/all-admins", endpoint="all_admins")
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
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


@app.route("/dashboard/deactivate-admin/<username>", endpoint="deactivate_admin")
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
        flash("An error occurred while deactivating the admin")
        print(f"An error occurred: {e}")
        return redirect(url_for("all_admins"))


@app.route("/dashboard/reactivate-admin/<username>", endpoint="reactivate_admin")
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
        flash("An error occurred while reactivating the admin")
        print(f"An error occurred: {e}")
        return redirect(url_for("all_admins"))


@app.route("/dashboard/delete-admin/<username>", endpoint="delete_admin")
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
        flash("An error occurred while deleting the admin")
        print(f"An error occurred: {e}")
        return redirect(url_for("all_admins"))


@app.route("/send-email-to-admin/<id>", endpoint="send_admin_email")
@login_required
def send_admin_email(id):
    try:
        email = Email.query.filter_by(id=id).first()
        admin_email = session["admin_email"]
        admin_first_name = session["admin_first_name"]

        email.allow = True
        db.session.add(email)
        db.session.commit()

        send_user_private_email(email, admin_email, admin_first_name)

        flash(f"Email successfully sent to the teacher {admin_email}")
        del session["admin_email"]
        del session["admin_first_name"]
        return redirect(url_for("emails_to_individual_admins"))
    except Exception as e:
        flash(f"Error sending email: {str(e)}")
        return redirect(url_for("emails_to_individual_admins"))


@app.route("/edit-admin-email/<id>", methods=["GET", "POST"], endpoint="edit_admin_email")
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


@app.route("/delete-email-sent-to-a-admin/<id>", endpoint="delete_admin_email")
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
