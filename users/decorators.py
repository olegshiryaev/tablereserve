from django.http import HttpResponseForbidden


def admin_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin():
            return HttpResponseForbidden()
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def owner_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_owner():
            return HttpResponseForbidden()
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def user_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_user():
            return HttpResponseForbidden()
        return view_func(request, *args, **kwargs)

    return _wrapped_view
