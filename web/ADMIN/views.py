from django.shortcuts import render
from django.http import FileResponse, JsonResponse
from django.shortcuts import render, HttpResponse, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse

def auth_view(request):
    if not request.user.is_anonymous:
        return redirect('Admin:management')
    if request.POST:
        user = authenticate(email=request.POST['email'], password=request.POST['password'])
        if user is not None:
            if user.is_manager:
                login(request, user)
                return redirect('Admin:management')
        else:
            print('bad auth')
        return redirect('Admin:auth')
    return render(request, 'CRM_ADMIN/auth.html')

def login_required_admin(view_func):
    """ Декоратор для админ функций """

    def test(user):
        if not user.is_anonymous:
            return True
        return False

    test = user_passes_test(test, login_url='Api:main', redirect_field_name=None)
    return login_required(test(view_func))

@login_required_admin
def index_view(request):
    return redirect('Admin:management')


@login_required_admin
def management_view(request):
    data = {

    }
    return render(request, 'CRM_ADMIN/management.html', data)


@login_required_admin
def whitelist_view(request):
    data = {

    }
    return render(request, 'ADMIN/whitelist.html', data)


@login_required_admin
def items_view(request):
    data = {

    }
    return render(request, 'ADMIN/items.html', data)


