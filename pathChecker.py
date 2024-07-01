import os
from pathlib import Path
from django.conf import settings
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SKM.settings')
django.setup()
data_folder = settings.BASE_DIR / 'dummy' / 'SMH_PROTOTYPE_FILE/'

if os.path.exists(data_folder):
    print("The path exists.")
else:
    print("The path does not exist.")