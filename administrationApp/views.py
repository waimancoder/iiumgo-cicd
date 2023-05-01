from django.shortcuts import render

# Create your views here.


def frontpage(request):
    return render(request, "landing.html")


def loginpage(request):
    return render(request, "loginpage.html")
