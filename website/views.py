from django.shortcuts import render

# Create your views here.

def admin_home(request):
    return render(request=request,template_name='website/admin_home.html')