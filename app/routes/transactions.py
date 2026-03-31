from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from .blueprint import bp as app
from app import db
from app.forms import DetailForm
from app.models import TransactionPan, Transaction, IPO, Details, Seller, Pan
from .common import flash_message


@app.route("/add-details/<int:product_id>", methods=["GET", "POST"], endpoint="add_details")
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
                db.session.add(details)
                db.session.commit()
                session["temp_details"].append(details.id)
                session.modified = True
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
        print(f"An error occurred: {str(e)}")


@app.route("/all-transactions", endpoint="all_transaction")
@login_required
def all_transaction():
    if session.get("temp_details") is not None:
        session.pop("temp_details", None)
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


@app.route("/delete-transaction/<int:id>", methods=["GET", "POST"], endpoint="delete_transaction")
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


@app.route("/available-pans", methods=["GET", "POST"], endpoint="available_pans")
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


@app.route("/transaction-details/<int:product_id>", endpoint="transaction_details")
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
            return render_template(
                "transaction/details_transaction.html",
                title="Transaction Details",
                details=transactions[0].product.name,
                transactions=transaction_pans,
                total_transaction=len(transaction_pans),
            )
        elif current_user.type == "buyer":
            sellers = Seller.query.filter_by(buyer_id=current_user.id).all()
            seller_pans = []
            for seller in sellers:
                transactions = Transaction.query.filter_by(
                    seller_id=seller.id, product_id=product_id
                ).all()
                if transactions:
                    transaction_pans = pannum_trans(transactions)
                    seller_pans.extend(transaction_pans)
            if seller_pans:
                return render_template(
                    "transaction/details_transaction.html",
                    title="Transaction Details",
                    details=seller_pans[0].transaction.product.name,
                    transactions=seller_pans,
                    total_transaction=len(seller_pans),
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


def pannum_trans(transactions):
    transaction_pans = []
    for transaction in transactions:
        transaction_pan = TransactionPan.query.filter_by(
            transaction_id=transaction.id
        ).all()
        transaction_pans.extend(transaction_pan)
    return transaction_pans


@app.route("/seller-transaction/<int:product_id>", endpoint="seller_transaction")
def seller_transaction(product_id):
    try:
        if current_user.type == "buyer":
            sellers = Seller.query.filter_by(buyer_id=current_user.id).all()
        elif current_user.type == "admin":
            sellers = Seller.query.all()
        else:
            return flash_message()

        transactions = []
        for seller in sellers:
            seller_transactions = Transaction.query.filter_by(
                seller_id=seller.id, product_id=product_id
            ).all()
            transactions.extend(seller_transactions)

        if not transactions:
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
