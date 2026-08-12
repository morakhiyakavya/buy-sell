from app import app, db
from app.models import Admin, Buyer, Seller


DEMO_USERS = {
    "admin": {
        "first_name": "Asha",
        "last_name": "Admin",
        "username": "admin_demo",
        "email": "admin_demo@example.com",
        "phone_number": "9000000001",
        "password": "Admin@123",
        "department": "Administration",
    },
    "buyer": {
        "first_name": "Bharat",
        "last_name": "Buyer",
        "username": "buyer_demo",
        "email": "buyer_demo@example.com",
        "phone_number": "9000000002",
        "password": "Buyer@123",
        "current_residence": "Ahmedabad, Gujarat",
    },
    "seller": {
        "first_name": "Sana",
        "last_name": "Seller",
        "username": "seller_demo",
        "email": "seller_demo@example.com",
        "phone_number": "9000000003",
        "password": "Seller@123",
        "current_residence": "Ahmedabad, Gujarat",
    },
}


def get_or_create_admin():
    admin = Admin.query.filter_by(username=DEMO_USERS["admin"]["username"]).first()
    if admin:
        return admin, False

    admin = Admin(
        first_name=DEMO_USERS["admin"]["first_name"],
        last_name=DEMO_USERS["admin"]["last_name"],
        username=DEMO_USERS["admin"]["username"],
        email=DEMO_USERS["admin"]["email"],
        phone_number=DEMO_USERS["admin"]["phone_number"],
        department=DEMO_USERS["admin"]["department"],
    )
    admin.set_password(DEMO_USERS["admin"]["password"])
    db.session.add(admin)
    return admin, True


def get_or_create_buyer():
    buyer = Buyer.query.filter_by(username=DEMO_USERS["buyer"]["username"]).first()
    if buyer:
        return buyer, False

    buyer = Buyer(
        first_name=DEMO_USERS["buyer"]["first_name"],
        last_name=DEMO_USERS["buyer"]["last_name"],
        username=DEMO_USERS["buyer"]["username"],
        email=DEMO_USERS["buyer"]["email"],
        phone_number=DEMO_USERS["buyer"]["phone_number"],
        current_residence=DEMO_USERS["buyer"]["current_residence"],
    )
    buyer.set_password(DEMO_USERS["buyer"]["password"])
    db.session.add(buyer)
    return buyer, True


def get_or_create_seller(buyer):
    seller = Seller.query.filter_by(username=DEMO_USERS["seller"]["username"]).first()
    if seller:
        return seller, False

    seller = Seller(
        first_name=DEMO_USERS["seller"]["first_name"],
        last_name=DEMO_USERS["seller"]["last_name"],
        username=DEMO_USERS["seller"]["username"],
        email=DEMO_USERS["seller"]["email"],
        phone_number=DEMO_USERS["seller"]["phone_number"],
        current_residence=DEMO_USERS["seller"]["current_residence"],
        buyer=buyer,
    )
    seller.set_password(DEMO_USERS["seller"]["password"])
    db.session.add(seller)
    return seller, True


def main():
    with app.app_context():
        db.create_all()

        admin, admin_created = get_or_create_admin()
        buyer, buyer_created = get_or_create_buyer()
        seller, seller_created = get_or_create_seller(buyer)

        db.session.commit()

        print("Demo users ready:")
        print(f"- Admin:  {DEMO_USERS['admin']['username']} / {DEMO_USERS['admin']['password']}")
        print(f"- Buyer:  {DEMO_USERS['buyer']['username']} / {DEMO_USERS['buyer']['password']}")
        print(f"- Seller: {DEMO_USERS['seller']['username']} / {DEMO_USERS['seller']['password']}")
        print(f"Created this run: admin={admin_created}, buyer={buyer_created}, seller={seller_created}")


if __name__ == "__main__":
    main()