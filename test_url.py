import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sat_core.settings')
django.setup()

from django.test.client import Client
from django.contrib.auth.models import User

# Try to get a user and login
c = Client()
user = User.objects.first()
if user:
    c.force_login(user)
    response = c.get('/gamification/dashboard/')
    with open("response.html", "w") as f:
        f.write(response.content.decode("utf-8"))
    print("Dashboard fetched")
else:
    print("No user found")
