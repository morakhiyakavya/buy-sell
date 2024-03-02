from app import app, db
from app.models import User, Buyer, Seller, Admin, Email


@app.shell_context_processor
def make_shell_context():
    return dict(
        db=db,
        User=User,
        Admin=Admin,
        Buyer=Buyer,
        Seller=Seller,
        Email=Email,
    )
