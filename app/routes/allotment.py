import os
import json
import math
import time
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import render_template, url_for, flash, jsonify, send_file, abort, request
from flask_login import login_required, current_user
from flask_socketio import join_room
from werkzeug.utils import secure_filename
from sqlalchemy import MetaData, inspect
from .blueprint import bp as app
from app import db, socketio
from app.forms import AllotmentForm
from app.excel import process_excel_data, write_in_excel, process_excel, create_updated_excel_with_results
from app.allotment import scrape_data_from_websites, driver_path
from app.linkin import search_on_pan, get_company_name
from app.bigshare import big_company, big_pan
from app.maashitalta import search_on_maashilta, mashilta_company
from app.skyline import company_url, search_application
from app.tor import renew_ip
from app.models import Transaction, Seller
from .transactions import pannum_trans
from .common import flash_message
from app.kfintech import query_pan_status_tor, get_client_id_for_ipo


@app.route("/allotment/<product_id>/<ipo>", methods=["GET", "POST"], endpoint="allotment")
@login_required
def allotment(product_id, ipo, listing_On="bigshare"):
    if current_user.type == "buyer":
        if not os.path.exists(f"json_file/{ipo}/{current_user.id}.json"):
            buyer_id = current_user.id
            sellers = Seller.query.filter_by(buyer_id=buyer_id).all()
            usernames = []
            room = current_user.id
            for seller in sellers:
                transactions = Transaction.query.filter_by(
                    seller_id=seller.id, product_id=product_id
                ).all()
                if transactions:
                    transaction_pans = pannum_trans(transactions)
                    for transaction_pan in transaction_pans:
                        usernames.append(transaction_pan.pan.pan_number)
            if listing_On != "linkin":
                results = scrape_data_from_websites(
                    driver_path, listing_On, ipo, usernames, room, socketio, headless=False
                )
            if os.path.exists("json_file/{ipo}"):
                if not os.path.exists(f"json_file/{ipo}/{buyer_id}"):
                    with open(f"json_file/{ipo}/{buyer_id}", "w") as file:
                        json.dump(results, file)
            else:
                os.makedirs(f"json_file/{ipo}")
                with open(f"json_file/{ipo}/{buyer_id}.json", "w") as file:
                    json.dump(results, file)
            return jsonify(results)
        else:
            return jsonify({"message": "We have already checked the allotment for this product."})
    else:
        return flash_message()


def subject_to_index(subject):
    return {"Subject 1": 1, "Subject 2": 2, "Subject 3": 3}.get(subject, 0)


def build_company_data(transactions, category_params: dict, premium: float):
    result = {}
    for tx in transactions:
        detail = tx.details
        category = detail.formtype
        subject = detail.subject
        forms = detail.quantity
        price = detail.price
        sub_id = subject_to_index(subject)
        if sub_id == 0:
            continue
        if category not in result:
            result[category] = {}
            if category in category_params:
                result[category].update(category_params[category])
        result[category].setdefault(f"SUB_{sub_id}_FORMS", 0)
        result[category].setdefault(f"SUB_{sub_id}_TOTAL_PRICE", 0)
        result[category][f"SUB_{sub_id}_FORMS"] += forms
        result[category][f"SUB_{sub_id}_TOTAL_PRICE"] += forms * price
    for category in result:
        for i in (1, 2, 3):
            forms = result[category].get(f"SUB_{i}_FORMS", 0)
            total_price = result[category].get(f"SUB_{i}_TOTAL_PRICE", 0)
            if forms > 0:
                result[category][f"SUB_{i}_AVG_PRICE"] = round(total_price / forms, 2)
            result[category].pop(f"SUB_{i}_TOTAL_PRICE", None)
    result["premium"] = premium
    return result


def compute_category(data: Dict[str, Any]) -> Dict[str, Any]:
    premium = data.get("premium", 1)
    if all(key in data for key in ("LOT_SIZE", "REQUIRED", "EXPECTATION", "RATES/MARGIN")):
        sub_1_rate = round(premium * data["LOT_SIZE"] * data["REQUIRED"] / data["EXPECTATION"]) 
        sub_2_rate = round(data["LOT_SIZE"] * (data["RATES/MARGIN"] / 100) * premium)
    else:
        sub_1_rate = None
        sub_2_rate = None
    total_forms = sum(data.get(f"SUB_{i}_FORMS", 0) for i in (1, 2, 3))
    costings = {
        f"sub_{i}_cost": data.get(f"SUB_{i}_FORMS", 0) * data.get(f"SUB_{i}_AVG_PRICE", 0)
        for i in (1, 2, 3)
    }
    return {
        "total_forms": total_forms,
        **costings,
        "sub_1_rate": sub_1_rate,
        "sub_2_rate": sub_2_rate,
    }


def make_calculation(company_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    results_by_cat = {cat: compute_category(data) for cat, data in company_data.items() if cat != "premium"}
    expected_share = sum(
        math.ceil(
            results_by_cat[cat]["total_forms"] * company_data[cat]["LOT_SIZE"] * company_data[cat]["REQUIRED"] / company_data[cat]["EXPECTATION"]
        )
        for cat in ("Retail", "Small Hni", "B-Hni") if cat in results_by_cat
    )
    total_share_forms_cost = sum(results_by_cat.get("Shares", {}).get(f"sub_{i}_cost", 0) for i in (1, 2, 3))
    pending_share = total_share_forms_cost + expected_share
    expected_total_cost = sum(
        sum(results_by_cat[cat].get(f"sub_{i}_cost", 0) for i in (1, 2, 3)) for cat in results_by_cat
    )
    pending_total_cost = total_share_forms_cost + expected_share
    expected_per_share_cost = expected_total_cost / expected_share if expected_share else 0
    pending_per_share_cost = pending_total_cost / pending_share if pending_share else 0
    return {
        "results_by_category": results_by_cat,
        "expected_share": expected_share,
        "pending_share": pending_share,
        "expected_total_cost": expected_total_cost,
        "pending_total_cost": pending_total_cost,
        "expected_per_share_cost": expected_per_share_cost,
        "pending_per_share_cost": pending_per_share_cost,
    }


def make_dict(productId):
    transactions = Transaction.query.filter_by(product_id=productId).all()
    category_params = {
        "Retail": {"LOT_SIZE": 63, "REQUIRED": 46782, "EXPECTATION": 800000, "RATES/MARGIN": 80},
        "Small Hni": {"LOT_SIZE": 882, "REQUIRED": 1671, "EXPECTATION": 30000, "RATES/MARGIN": 80},
        "B-Hni": {"LOT_SIZE": 882, "REQUIRED": 3342, "EXPECTATION": 10000, "RATES/MARGIN": 80},
    }
    company_data = build_company_data(transactions=transactions, category_params=category_params, premium=1.2)
    result = make_calculation(company_data)
    print("Result ->", result)


@app.route("/checking-allotment", methods=["GET", "POST"], endpoint="checking_allotment")
@login_required
def checking_allotment():
    try:
        if current_user.is_authenticated:
            form = AllotmentForm()
            file_ready = False
            room = current_user.id
            if form.validate_on_submit():
                folder_path = os.path.join(os.path.dirname(__file__), "..", "upload_folder")
                folder_path = os.path.abspath(folder_path)
                for filename in os.listdir(folder_path):
                    file_path = os.path.join(folder_path, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                file = form.excel_file.data
                filename = secure_filename(file.filename)
                filepath = os.path.join(folder_path, filename)
                file.save(filepath)
                ipo = form.ipo.data.strip()
                listing_On = form.listing_On.data.strip()
                pan_Column = form.pan_Column.data.strip()
                if pan_Column.isdigit():
                    pan_Column = int(pan_Column) - 1
                start_Row = form.start_Row.data
                end_Row = form.end_Row.data
                usernames = process_excel_data(filepath, pan_Column, start_Row, end_Row)
                # make all the pans in the list capital and stripped of whitespace
                usernames = [u.upper().strip() for u in usernames if u and isinstance(u, str)]
                if listing_On == "kfintech":
                    results = {}
                    # determine client_id by fuzzy matching the IPO name
                    client_id = get_client_id_for_ipo(ipo)
                    if client_id:
                        print(f"Using client_id {client_id} for IPO '{ipo}'")
                    else:
                        print(f"No client_id match found for IPO '{ipo}'; using default client_id")

                    start_time = time.time()
                    start_time = time.time()
                    
                    # Batch processing of usernames (PANs)
                    batch_size = 50
                    username_chunks = [usernames[i:i + batch_size] for i in range(0, len(usernames), batch_size)]
                    
                    total_processed = 0
                    
                    for chunk_index, chunk in enumerate(username_chunks):
                        print(f"Processing batch {chunk_index + 1}/{len(username_chunks)} with {len(chunk)} PANs...")
                        
                        # Use fewer workers to reduce load on Tor
                        with ThreadPoolExecutor(max_workers=10) as executor:
                            futures = {executor.submit(kfintech_single_pan, normalize_pan(u), client_id, ipo): u for u in chunk}
                            
                            for future in as_completed(futures):
                                u = futures[future]
                                try:
                                    result = future.result()
                                    print(f"Processed {u}")
                                    results[u] = result
                                    total_processed += 1
                                except Exception as e:
                                    print(f"Error processing {u}: {e}")
                                    results[u] = {"error": str(e)}
                        
                        # Renew IP after each batch (except the last one)
                        if chunk_index < len(username_chunks) - 1:
                            print("Batch complete. Renewing Tor IP...")
                            renew_ip()
                            # Extra sleep to ensure stability
                            time.sleep(2)
                            
                    end_time = time.time()
                    print(f"Time taken for {total_processed} PANs (kfintech): {end_time - start_time:.2f} seconds")
                else:
                    if listing_On == "linkin":
                        company_name = form.ipo.data.strip()
                        company_id = get_company_name(company_name)
                        results = {}
                        start_time = time.time()
                        with ThreadPoolExecutor(max_workers=20) as executor:
                            futures = {executor.submit(search_on_pan, company_id, u): u for u in usernames}
                            for i, future in enumerate(as_completed(futures), 1):
                                u = futures[future]
                                try:
                                    result = future.result()
                                    results[u] = result
                                except Exception as e:
                                    print(f"Error processing {u}: {e}")
                                    results[u] = {"Error": str(e)}
                                if i % 500 == 0:
                                    renew_ip()
                        end_time = time.time()
                        print(f"Time taken for {len(usernames)} users: {end_time - start_time} seconds")
                    elif listing_On == "bigshare":
                        company_id = big_company(form.ipo.data.strip())
                        results = {}
                        start_time = time.time()
                        with ThreadPoolExecutor(max_workers=20) as executor:
                            futures = {executor.submit(big_pan, company_id, u): u for u in usernames}
                            for i, future in enumerate(as_completed(futures), 1):
                                u = futures[future]
                                result = future.result()
                                results[u] = result
                                if i % 50 == 0:
                                    renew_ip()
                    elif listing_On == "skyline":
                        results = {}
                        start_time = time.time()
                        with ThreadPoolExecutor(max_workers=1) as executor:
                            futures = {executor.submit(search_application, form.ipo.data.strip(), u): u for u in usernames}
                            for i, future in enumerate(as_completed(futures), 1):
                                u = futures[future]
                                try:
                                    result = future.result()
                                    results[u] = result
                                except Exception as e:
                                    print(f"Error processing {u}: {e}")
                                    results[u] = {"Error": str(e)}
                                time.sleep(0.5)
                                if i % 50 == 0:
                                    renew_ip()
                    else:
                        company_id = mashilta_company(form.ipo.data.strip())
                        results = {}
                        start_time = time.time()
                        with ThreadPoolExecutor(max_workers=20) as executor:
                            futures = {executor.submit(search_on_maashilta, company_id, u): u for u in usernames}
                            for i, future in enumerate(as_completed(futures), 1):
                                u = futures[future]
                                result = future.result()
                                results[u] = result
                                if i % 50 == 0:
                                    renew_ip()
                try:
                    if os.path.exists("json"):
                        with open(f"json/{ipo}.json", "w", encoding="utf-8") as file:
                            json.dump(results, file, ensure_ascii=False, indent=2)
                    else:
                        os.makedirs("json")
                        with open(f"json/{ipo}.json", "w", encoding="utf-8") as file:
                            json.dump(results, file, ensure_ascii=False, indent=2)
                except Exception as e:
                    print("An error occurred while saving the JSON file:", str(e))
                
                create_updated_excel_with_results(filepath, results)
                file_ready = True
                return download_updated_file(filepath)
            return render_template(
                "allotment/check_allotment.html",
                title="Checking Allotment",
                form=form,
                file_ready=file_ready,
                room=room,
            )
        else:
            return flash_message()
    except Exception as e:
        print("An error occurred:", str(e))
        import traceback
        traceback.print_exc()
        return f"Error : {e}", 400


@socketio.on("join")
def on_join(data):
    room = current_user.id
    join_room(room)


def download_updated_file(filepath):
    if filepath and os.path.exists(filepath):
        try:
            return send_file(filepath, as_attachment=True)
        except Exception as e:
            print(e)
            abort(404)
    else:
        return "Invalid download token or file does not exist", 404


def kfintech_single_pan(pan, client_id=None, ipo_name=None):
    # Query a single PAN using kfintech API with a specific client_id
    result = query_pan_status_tor([pan], client_id=client_id, ipo_name=ipo_name)
    return result.get(pan, {})


def normalize_pan(pan):
    # Remove all whitespace and non-alphanumeric characters, uppercase
    import re
    pan = re.sub(r'[^A-Za-z0-9]', '', pan)
    return pan.upper().strip()
