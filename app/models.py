from app import db, login, app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import jwt
from time import time
from hashlib import md5
from sqlalchemy import UniqueConstraint

@login.user_loader
def load_user(id):
    return User.query.get(int(id))


# =================
# Application Users
# =================


class User(db.Model, UserMixin):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(64), index=True, default="First Name", nullable=False)
    last_name = db.Column(db.String(64), index=True, default="Last Name", nullable=False)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(128), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    confirm_password = db.Column(db.String(128))
    phone_number = db.Column(db.String(20), default="7016184560", nullable=False)
    verification_phone = db.Column(db.String(20))
    active = db.Column(db.Boolean, nullable=False, default=True)
    delete_account = db.Column(db.Boolean, default=False)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    emails = db.relationship("Email", backref="author", lazy="dynamic")

    type = db.Column(db.String(64))

    __mapper_args__ = {"polymorphic_identity": "user", "polymorphic_on": "type"}

    def __repr__(self):
        return f"User: {self.username} {self.verification_phone}"

    def two_factor_enabled(self):
        return self.verification_phone is not None

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        # override UserMixin property which always returns true
        # return the value of the active column instead
        return self.active

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {"reset_password": self.id, "exp": time() + expires_in},
            app.config["SECRET_KEY"],
            algorithm="HS256",
        )

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])[
                "reset_password"
            ]
        except:
            return
        return User.query.get(id)

    def avatar(self, size):
        digest = md5(self.email.lower().encode("utf-8")).hexdigest()
        return f"https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}"


class Seller(User):
    __tablename__ = "seller"

    id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    current_residence = db.Column(db.String(64), default="Ahmedabad, Gujarat")
    buyer_id = db.Column(db.Integer, db.ForeignKey("buyer.id", ondelete="CASCADE"))
    buyer = db.relationship(
        "Buyer", backref="buyer", foreign_keys=[buyer_id], passive_deletes=True
    )

    __mapper_args__ = {"polymorphic_identity": "seller", "polymorphic_load": "inline"}

    def __repr__(self):
        return f"Seller: {self.username}"


class Buyer(User):
    __tablename__ = "buyer"

    id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    current_residence = db.Column(db.String(64), default="Ahmedabad, Gujarat")
    # registered_by_superadmin = db.relationship('BuyerRegistration', backref='registered_buyer', lazy='dynamic')
    # sellers = db.relationship('Seller', backref='buyer', lazy='dynamic')

    __mapper_args__ = {"polymorphic_identity": "buyer", "polymorphic_load": "inline"}

    def __repr__(self):
        return f"Buyer: {self.username}"


class Admin(User):
    __tablename__ = "admin"

    id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    current_residence = db.Column(db.String(64), default="Ahmedabad, Gujarat")
    department = db.Column(db.String(64), default="Administration")

    __mapper_args__ = {"polymorphic_identity": "admin", "polymorphic_load": "inline"}

    def __repr__(self):
        return f"Admin: {self.first_name} | {self.department}"


# =================
# End of Application Users
# =================
    
# =================
# Application Users Purchase and Sell
# =================

#product detail
class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(64), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    buyer_id = db.Column(db.Integer, db.ForeignKey("buyer.id", ondelete="CASCADE"), nullable=False)
    buyer = db.relationship("Buyer", backref="products", foreign_keys=[buyer_id], passive_deletes=True)
    price_combinations = db.relationship('Details', backref='product', lazy=True)
    # Add a unique constraint on name and buyer_id
    __table_args__ = (UniqueConstraint('name', 'buyer_id'),)


class IPO(db.Model):
    __tablename__ = 'ipos'
    id = db.Column(db.Integer, primary_key=True, name='pk_ipo_id')
    name = db.Column(db.String(255), nullable=False, unique=True, name='uq_ipo_name')
    open_date = db.Column(db.String(255), nullable=True)
    close_date = db.Column(db.String(255), nullable=True)
    listing_date = db.Column(db.String(255), nullable=True)
    price = db.Column(db.String(255), nullable=True)
    issue_size = db.Column(db.String(255), nullable=True)
    lot_size = db.Column(db.String(255), nullable=True)
    listing_at = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(255), nullable=False)


# Subject Detail
class Details(db.Model):
    __tablename__ = "details"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable = False)
    subject = db.Column(db.String(10), nullable=False)
    formtype = db.Column(db.String(8), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    seller_id = db.Column(db.Integer, db.ForeignKey("seller.id", ondelete="CASCADE"), nullable=False)
    seller = db.relationship("Seller", backref="details", foreign_keys=[seller_id], passive_deletes=True)


# Pan Detail
class Pan(db.Model):
    __tablename__ = "pan"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    pan_number = db.Column(db.String(64), nullable=False, unique = True)
    dp_id = db.Column(db.String(64), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    seller_id = db.Column(db.Integer, db.ForeignKey("seller.id", ondelete="CASCADE"), nullable=False)
    seller = db.relationship("Seller", backref="pan", foreign_keys=[seller_id], passive_deletes=True)


#transaction detail
class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    settled = db.Column(db.Boolean, default=False)

    # Relationships
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product = db.relationship('Product', backref='transactions')

    details_id = db.Column(db.Integer, db.ForeignKey('details.id'), nullable=False)
    details = db.relationship('Details', backref='transactions')

    seller_id = db.Column(db.Integer, db.ForeignKey("seller.id", ondelete="CASCADE"), nullable=False)
    seller = db.relationship("Seller", backref="transactions", foreign_keys=[seller_id], passive_deletes=True)

    buyer_id = db.Column(db.Integer, db.ForeignKey("buyer.id", ondelete="CASCADE"), nullable=False)
    buyer = db.relationship("Buyer", backref="transactions", foreign_keys=[buyer_id], passive_deletes=True)


class TransactionPan(db.Model):
    __tablename__ = "transaction_pan"
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), primary_key=True)
    pan_id = db.Column(db.Integer, db.ForeignKey('pan.id'), primary_key=True)

    transaction = db.relationship('Transaction', backref=db.backref('transaction_pans', cascade='all, delete-orphan'))
    pan = db.relationship('Pan', backref=db.backref('pan_transactions', cascade='all, delete-orphan', overlaps = "pans, transactions"))


# =================
# End of Application Users Purchase and Sell
# =================


# =================
# Emails sent out
# =================


class Email(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(128), nullable=False)
    body = db.Column(db.String(500), nullable=False)
    closing = db.Column(db.String(50), nullable=False)
    bulk = db.Column(db.String(30), default="Bulk")
    signature = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    allow = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"))

    def __repr__(self):
        return f"Subject: {self.subject}"


# =================
# End of emails sent out
# =================