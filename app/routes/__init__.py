"""
Blueprint-backed routes package.

Split the original monolithic routes into focused modules and
register them on a single Blueprint at import time.
"""

from .blueprint import bp  # The shared blueprint

# Import modules so their @bp.route decorators execute
from . import common  # noqa: F401
from . import public  # noqa: F401
from . import auth  # noqa: F401
from . import dashboard  # noqa: F401
from . import admin  # noqa: F401
from . import buyer  # noqa: F401
from . import seller  # noqa: F401
from . import products  # noqa: F401
from . import pans  # noqa: F401
from . import transactions  # noqa: F401
from . import allotment  # noqa: F401
from . import bulk  # noqa: F401
from . import api  # noqa: F401
from . import sockets  # noqa: F401

def register_endpoint_aliases(app):
    """Create bare endpoint aliases for legacy url_for('name') calls.

    Blueprint endpoints are namespaced as 'routes.<name>'. This helper
    adds additional endpoint names without the 'routes.' prefix pointing
    to the same view functions, preserving existing url_for usage.
    """
    try:
        from werkzeug.routing import Rule
        prefix = f"{bp.name}."
        rules = list(app.url_map.iter_rules())
        for rule in rules:
            if not rule.endpoint.startswith(prefix):
                continue
            bare = rule.endpoint[len(prefix) :]
            if bare in app.view_functions:
                continue
            view_func = app.view_functions[rule.endpoint]
            methods = set(rule.methods or set()) - {"HEAD", "OPTIONS"}
            app.add_url_rule(
                rule.rule,
                endpoint=bare,
                view_func=view_func,
                methods=list(methods) if methods else None,
                defaults=rule.defaults,
            )
    except Exception as e:
        # Non-fatal: app still works with namespaced endpoints
        print(f"Endpoint alias registration skipped: {e}")

__all__ = ["bp", "register_endpoint_aliases"]
