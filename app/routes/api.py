import logging
import random
import string
import os
from datetime import datetime
from flask import jsonify, render_template
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy import inspect, MetaData
from .blueprint import bp as app
from app import db
from app.models import IPO, Seller, Details, Transaction


def generate_password(length=8):
    characters = string.ascii_letters + string.digits
    password = "".join(random.choice(characters) for _ in range(length))
    return password


@app.route("/submit-form", methods=["POST"], endpoint="submit_form")
def submit_form():
    try:
        from flask import request

        data = request.json
        ipoName = data.get("ipoName")
        seller_name = data.get("sellerName")
        extradetails = data.get("extradetails")
        number = data.get("sellerNumber")
        rate = data.get("rate")
        number_of_forms = data.get("numberOfForms")
        option = data.get("option")
        subject = data.get("subject")
        date_time = data.get("dateTime")
        buysell = data.get("buysell")
        if buysell == "Sell":
            number_of_forms = -number_of_forms
        date_time = datetime.fromisoformat(date_time)
        seller_name = seller_name.split("(")[0].strip()

        if len(number) > 10:
            number = number[-10:]
        try:
            seller = Seller.query.filter_by(phone_number=number).first()
            if not seller:
                pass_word = generate_password()
                seller = Seller(
                    first_name=seller_name,
                    last_name="",
                    username=seller_name,
                    email=pass_word + "@gmail.com",
                    confirm_password=pass_word,
                    phone_number=number,
                    buyer_id=2,
                )
                seller.set_password(pass_word)
                db.session.add(seller)
                db.session.commit()
                seller = Seller.query.filter_by(phone_number=number).first()
        except IntegrityError:
            db.session.rollback()
            pass_word = generate_password()
            seller = Seller(
                first_name=seller_name,
                last_name="",
                username=seller_name + "_" + str(random.randint(1000, 9999)),
                email=pass_word + "@gmail.com",
                confirm_password=pass_word,
                phone_number=number,
                buyer_id=2,
            )
            seller.set_password(pass_word)
            db.session.add(seller)
            db.session.commit()

        ipo = IPO.query.filter_by(name=ipoName).first()
        if not ipo:
            ipo = IPO(
                name=ipoName,
                status="open",
                listing_date=date_time,
                open_date=date_time,
                close_date=date_time,
            )
            db.session.add(ipo)
            db.session.commit()
            ipo = IPO.query.filter_by(name=ipoName).first()

        details = Details(
            product_id=ipo.id,
            subject=subject,
            formtype=option,
            price=rate,
            quantity=number_of_forms,
            extra_details=extradetails,
            seller=seller,
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

        response = {
            "status": "success",
            "message": "Form submitted successfully",
            "data": data,
        }
        return jsonify(response), 200
    except Exception as e:
        tb_str = logging.Formatter().formatException(e.__traceback__)
        logging.error(tb_str)
        return (
            jsonify(
                {
                    "error": {
                        "code": "server_error",
                        "message": "An unexpected error occurred.",
                        "details": tb_str,
                    }
                }
            ),
            500,
        )


@app.route("/submit-contacts", methods=["POST"], endpoint="submit_contacts")
def submit_contacts():
    from flask import request

    data = request.get_json()
    contacts = data.get("contacts", [])
    for contact in contacts:
        name = contact.get("name")
        number = contact.get("number")
        print("\n---------------------------------------------\n")
        print(f"Name: {name}, Number: {number}")
        print("\n---------------------------------------------\n")
    return jsonify({"message": "Contacts received successfully"}), 200


@app.route("/give-ipo", methods=["POST"], endpoint="give_ipo")
def give_ipo():
    try:
        products = IPO.query.all()
        status_priority = {"open": 1, "closed": 2, "listed": 3}
        products.sort(key=lambda x: (status_priority.get(x.status, 4), x.listing_date))
        product_list = [{"name": product.name} for product in products]
        return jsonify({"products": product_list})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/show-tables", endpoint="show_tables")
@login_required
def show_tables():
    if current_user.type == "admin":
        inspector = inspect(db.engine)
        metadata = MetaData()
        metadata.reflect(bind=db.engine)

        all_tables_data = {}
        table_names = inspector.get_table_names()
        for table_name in table_names:
            table = metadata.tables[table_name]
            query = db.session.query(table).all()
            columns = table.columns.keys()
            table_data = [dict(zip(columns, row)) for row in query]
            all_tables_data[table_name] = table_data
        return render_template("show_tables.html", all_tables_data=all_tables_data)
    else:
        from .common import flash_message

        return flash_message()


@app.route("/download_db", methods=["GET"], endpoint="download_db")
@login_required
def download_db():
    try:
        if current_user.type == "admin":
            basedir = os.path.abspath(os.path.dirname(__file__))
            basedir = os.path.abspath(os.path.join(basedir, os.pardir))
            from flask import send_file

            return send_file(
                os.path.join(basedir, "app.db"),
                as_attachment=True,
                download_name="app.db",
            )
    except Exception as e:
        return str(e)
