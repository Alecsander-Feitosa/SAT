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

import uuid

print("\n--- ATTEMPTING CONNECTION ---")
try:
    efi = EfiPay(get_efi_credentials())
    txid = uuid.uuid4().hex[:35]
    body = {
        'calendario': {
            'expiracao': 3600
        },
        'valor': {
            'original': "15.00"
        },
        'chave': settings.EFI_CHAVE_PIX,
        'infoAdicionais': [
            {
                'nome': 'Descricao',
                'valor': 'Pedido Teste'
            }
        ]
    }
    response = efi.pix_create_charge(params={'txid': txid}, body=body)
    print("Charge Response:", response)
    
    loc_id = response.get('loc', {}).get('id')
    if loc_id:
        print("\nFetching QR Code for loc_id:", loc_id)
        qr_response = efi.pix_generate_qrcode(params={'id': loc_id})
        print("QR Response keys:", qr_response.keys())
        print("QR Response dict:", qr_response)
    else:
        print("No loc_id found.")
        
except Exception as e:
    print("ERROR:", str(e))
    import traceback
    traceback.print_exc()
