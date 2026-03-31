from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from .blueprint import bp as app
from app import db
from app.forms import PanForm
from app.models import Pan
from .common import flash_message


@app.route("/add-pan", methods=["GET", "POST"], endpoint="add_pan")
@login_required
def add_pan():
    try:
        if current_user.type == "seller":
            form = PanForm()
            if form.validate_on_submit():
                try:
                    pan = Pan(
                        name=form.name.data,
                        pan_number=form.pan_number.data.upper(),
                        dp_id=form.dp_id.data,
                        seller=current_user,
                    )
                    db.session.add(pan)
                    db.session.commit()
                    flash(f"Pan {pan.name}({pan.pan_number}) added . Add More.")
                    return redirect(url_for("add_pan"))
                except IntegrityError:
                    db.session.rollback()
                    flash("You Already have a pan with this number")
                    return redirect(url_for("add_pan"))
                except Exception as e:
                    print(e)
                    return f"Error: {str(e)}", 400
            return render_template("Pan/add_pan.html", title="Add Pan", form=form)

        return flash_message()
    except Exception as e:
        print(e)
        return f"Error: {str(e)}", 400


@app.route("/edit-pans", methods=["POST"], endpoint="edit_pans")
@login_required
def edit_pans():
    try:
        if current_user.type == "seller":
            data = request.get_json()
            record_id = data["id"]
            new_value = data["newValue"]
            new_column = data["column"]

            try:
                pan = Pan.query.filter_by(id=record_id).first()
                if not pan:
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "message": "No record found with the given ID",
                            }
                        ),
                        404,
                    )

                if new_column == "dp_id":
                    pan.dp_id = new_value
                elif new_column == "name":
                    pan.name = new_value
                elif new_column == "pan_number":
                    new_value = new_value.upper()
                    pan.pan_number = new_value
                else:
                    return (
                        jsonify({"status": "error", "message": "Invalid column name"}),
                        400,
                    )

                db.session.commit()
                return jsonify({"status": "success", "message": "Cell updated successfully"})

            except IntegrityError:
                db.session.rollback()
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "You Already have a pan with this number ",
                        }
                    ),
                    400,
                )
            except Exception as e:
                db.session.rollback()
                print(e)
                return jsonify({"status": "error", "message": str(e)}), 500
        else:
            return flash_message()
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/all-pan", endpoint="all_pan")
@login_required
def all_pan():
    try:
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
    except Exception as e:
        return str(e)


@app.route("/delete-pan/<id>", endpoint="delete_pan")
@login_required
def delete_pan(id):
    try:
        if current_user.type == "seller":
            pan = Pan.query.filter_by(seller_id=current_user.id, id=id).first_or_404()
            db.session.delete(pan)
            db.session.commit()
            flash(f"The Pan {pan.name}({pan.pan_number}) has been deleted")
            return redirect(url_for("all_pan"))
        return flash_message()
    except Exception as e:
        print(f"An error occurred: {e}")
        return f"Error : {e}", 400
