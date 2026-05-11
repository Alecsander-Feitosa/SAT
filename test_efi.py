import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sat_core.settings')
django.setup()

from django.conf import settings
from accounts.efi_utils import EfiPay

def get_efi_credentials():
    return {
        'client_id': settings.EFI_CLIENT_ID,
        'client_secret': settings.EFI_CLIENT_SECRET,
        'sandbox': False, # FORCING TO FALSE FOR TEST
        'certificate': settings.EFI_CERTIFICADO,
    }

print("--- EFI SETTINGS ---")
print(f"CLIENT_ID: {settings.EFI_CLIENT_ID[:5]}...")
print(f"CERTIFICADO PATH: {settings.EFI_CERTIFICADO}")
print(f"CERTIFICADO EXISTS: {os.path.exists(settings.EFI_CERTIFICADO)}")

print("\n--- ATTEMPTING CONNECTION ---")
try:
    efi = EfiPay(get_efi_credentials())
    response = efi.pix_create_charge(params={'txid': 'teste123'}, body={})
    print("Response:", response)
except Exception as e:
    print("ERROR:", str(e))
    import traceback
    traceback.print_exc()
