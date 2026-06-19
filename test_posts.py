import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sat_core.settings')
django.setup()

from social.models import Post

print("Total posts:", Post.objects.count())
for p in Post.objects.all()[:5]:
    print(p.id, p.titulo, "Torcida:", p.torcida)
