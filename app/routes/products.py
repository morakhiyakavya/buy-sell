from datetime import datetime
import re
from flask import render_template, redirect, url_for, flash, session
from flask_login import login_required, current_user
from .blueprint import bp as app
from app import db
from app.models import IPO
from app.allotment import IPODetailsScraper, driver_path


@app.route("/get-product", endpoint="get_product")
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
        print(f"An error occurred: {str(e)}")
        return "An error occurred while getting the product"


def process_ipo_details(ipo_details_green, ipo_details_lightyellow, ipo_details_aqua):
    all_names = [
        item["Name"]
        for item in ipo_details_green + ipo_details_aqua + ipo_details_lightyellow
    ]
    all_names_set = set(all_names)
    perfect_names = []
    db_names_set = {ipo.name for ipo in IPO.query.all()}
    for i in all_names_set:
        name = clean_name(i)
        perfect_names.append(name)
    names_not_in_dicts = db_names_set - set(perfect_names)
    for name in names_not_in_dicts:
        ipo = IPO.query.filter_by(name=name).first()
        if ipo:
            ipo.status = "complete"
            db.session.commit()
    update_ipo_status(ipo_details_green, "open")
    update_ipo_status(ipo_details_lightyellow, "closed")
    update_ipo_status(ipo_details_aqua, "listed")


def update_ipo_status(ipo_details, status):
    new_ipos = []
    collected_names = set()

    for ipo in ipo_details:
        name = clean_name(ipo["Name"])
        collected_names.add(name)

        ipo_db = IPO.query.filter_by(name=name).first()
        if ipo_db:
            if status != "open":
                ipo_db.status = status
        else:
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

    if new_ipos:
        db.session.bulk_save_objects(new_ipos)

    if status == "listed":
        IPO.query.filter(IPO.status == "listed", IPO.name.notin_(collected_names)).update(
            {IPO.status: "complete"}, synchronize_session=False
        )

    db.session.commit()


def clean_name(name):
    pattern = r"( PUBLIC LIMITED IPO\.? ?| LIMITED FPO\.? ?| LIMITED IPO\.? ?| PUBLIC LIMITED\.? ?| LTD IPO\.? ?| LIMITED\.? ?| LTD\.? ?| IPO)$"
    cleaned_name = re.sub(pattern, "", name, flags=re.IGNORECASE)
    return cleaned_name


@app.route("/view-product", endpoint="view_product")
@login_required
def view_product():
    try:
        if session.get("temp_details") is not None:
            session.pop("temp_details", None)

        if current_user.is_authenticated:
            products = IPO.query.all()
            view_products = len(products)
            status_priority = {"open": 1, "closed": 2, "listed": 3}
            products.sort(
                key=lambda x: (status_priority.get(x.status, 4), x.listing_date)
            )
            return render_template(
                "Product/all_products.html",
                title="Running Ipo's ",
                products=products,
                view_products=view_products,
            )
        else:
            from .common import flash_message

            return flash_message()
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return f"Error : {e}", 400


@app.route("/delete-product/<int:id>", endpoint="delete_product")
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
            from .common import flash_message

            return flash_message()
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return f"Error : {e}", 400
