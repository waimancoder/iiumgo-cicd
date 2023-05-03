from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login

import logging

logger = logging.getLogger(__name__)

# Create your views here.

from .forms import LoginForm


@login_required
def frontpage(request):
    return render(request, "landing.html")


def loginpage(request):
    return render(request, "loginpage.html")
