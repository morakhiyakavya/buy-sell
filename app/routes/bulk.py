from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from .blueprint import bp as app
from app import db
from app.excel import process_excel
from app.models import Pan, Email


@app.route("/add-pan-from-excel", methods=["GET", "POST"], endpoint="add_pan_from_excel")
def add_pan_from_excel():
    try:
        if current_user.type == "seller":
            file = request.files["file"]
            filename = secure_filename(file.filename)
            print("Filename ->", filename)
            content = file.read()
            df = process_excel(content)
            if df["pan"].isnull().any():
                raise ValueError("Pan column contains null values, which are not allowed.")
            records = df.to_dict(orient="records")
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


@app.route("/dashboard/bulk-emails/admins", endpoint="bulk_emails_admins")
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
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


@app.route("/dashboard/bulk-emails/buyers", endpoint="bulk_emails_buyers")
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
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400


@app.route("/dashboard/bulk-emails/sellers", endpoint="bulk_emails_sellers")
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
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400
