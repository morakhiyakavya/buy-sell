from flask_mail import Message
from flask import render_template
from app import mail, app, db

# from app.models import Newsletter_Subscriber


def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    mail.send(msg)


# Email user individually


def send_user_private_email(email, user_email, user_first_name):
    """Send user a private email"""
    send_email(
        subject=email.subject,
        sender=app.config["MAIL_DEFAULT_SENDER"],
        recipients=[user_email],
        text_body=render_template(
            "emails/private_email.txt", email=email, user_first_name=user_first_name
        ),
        html_body=render_template(
            "emails/private_email.html", email=email, user_first_name=user_first_name
        ),
    )


# ================================================
# Authentication
# ================================================


# Password reset email


def send_password_reset_email(user):
    """Send password reset email"""
    token = user.get_reset_password_token()
    send_email(
        "[somaSOMA] Reset Your Password",
        sender=app.config["MAIL_DEFAULT_SENDER"],
        recipients=[user.email],
        text_body=render_template("emails/reset_password.txt", user=user, token=token),
        html_body=render_template("emails/reset_password.html", user=user, token=token),
    )


def send_login_details(user, user_password):
    """Once registered, users (teacher, buyer, admin) will be notified via email"""
    send_email(
        "[somaSOMA] You have been registered!",
        sender=app.config["MAIL_DEFAULT_SENDER"],
        recipients=[user.email],
        text_body=render_template(
            "/emails/auth/send_login_details.txt",
            user=user,
            user_password=user_password,
        ),
        html_body=render_template(
            "/emails/auth/send_login_details.html",
            user=user,
            user_password=user_password,
        ),
    )


# ================================================
# Authentication
# ================================================


# ==================================================
# DEACTIVATE OWN ACCOUNT
# ==================================================


def request_account_deletion(admin, seller):
    """Request to delete seller account sent to all admins"""
    send_email(
        subject="[somaSOMA] Request to Deactivate Account",
        sender=app.config["MAIL_DEFAULT_SENDER"],
        recipients=[admin.email],
        text_body=render_template(
            "/emails/deactivate_account/seller_email.txt", admin=admin, seller=seller
        ),
        html_body=render_template(
            "/emails/deactivate_account/seller_email.html", admin=admin, seller=seller
        ),
    )


# ==================================================
# END OF DEACTIVATE OWN ACCOUNT
# ==================================================
