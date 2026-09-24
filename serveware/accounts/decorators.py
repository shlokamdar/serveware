from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden


def _role_required(role, login_url):
    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url=login_url)
        def _wrapped(request, *args, **kwargs):
            if getattr(request.user, "user_type", None) != role:
                return HttpResponseForbidden("You do not have access to this page.")
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


restaurant_required = _role_required("restaurant", "accounts:restaurant_signin")
customer_required = _role_required("customer", "accounts:customer_signin")
