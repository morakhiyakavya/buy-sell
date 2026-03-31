from flask import Blueprint


# Single blueprint to host all legacy routes under the same URLs
# We'll preserve original endpoint names via explicit endpoint=...
bp = Blueprint("routes", __name__)

