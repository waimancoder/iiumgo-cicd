from django.shortcuts import render
from django.template.context_processors import media
from django.templatetags.static import static
from django.conf import settings


# Create your views here.
def landing_page(request):
    return render(request, "landingpage.html")
