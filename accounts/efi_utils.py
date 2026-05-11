from django.conf import settings
from efipay import EfiPay
import uuid
from datetime import timedelta

def get_efi_credentials():
    return {
        'client_id': settings.EFI_CLIENT_ID,
        'client_secret': settings.EFI_CLIENT_SECRET,
        'sandbox': settings.EFI_SANDBOX,
        'certificate': settings.EFI_CERTIFICADO,
    }

def gerar_cobranca_pix(obj, tipo='fatura'):
    try:
        efi = EfiPay(get_efi_credentials())
        
        # Gera um txid único garantido
        txid = uuid.uuid4().hex[:35]
        
        valor_obj = obj.valor if tipo == 'fatura' else obj.total
        descricao = f'Fatura {obj.id} - {obj.assinatura.plano.nome}' if tipo == 'fatura' else f'Pedido Loja {obj.id}'
        
        # 1. Criar a cobrança PIX imediata
        body = {
            'calendario': {
                'expiracao': 3600
            },
            'valor': {
                'original': f"{valor_obj:.2f}"
            },
            'chave': 'sua_chave_pix_aqui@gmail.com', # Substitua pela sua chave registrada na Efí
            'infoAdicionais': [
                {
                    'nome': 'Descricao',
                    'valor': descricao
                }
            ]
        }
        
        # A API Pix da Efi exige put (txid é informado na URL)
        response = efi.pix_create_charge(params={'txid': txid}, body=body)
        
        if isinstance(response, Exception) or 'erro' in response:
            return {'sucesso': False, 'erro': str(response)}
            
        loc_id = response.get('loc', {}).get('id')
        
        # 2. Gerar o QR Code para essa location
        if loc_id:
            params = {'id': loc_id}
            qr_response = efi.pix_generate_qrcode(params=params)
            
            if isinstance(qr_response, Exception) or 'erro' in qr_response:
                return {'sucesso': False, 'erro': str(qr_response)}
                
            obj.txid = txid
            obj.loc_id = loc_id
            obj.pix_copia_e_cola = qr_response.get('qrcode')
            obj.pix_qrcode = qr_response.get('imagemQrcode')
            obj.save()
            
            return {
                'sucesso': True,
                'txid': txid,
                'qrcode_image': obj.pix_qrcode,
                'copia_e_cola': obj.pix_copia_e_cola
            }
            
        return {'sucesso': False, 'erro': 'Não foi possível obter o loc_id'}
        
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}

def configurar_webhook():
    """
    Função auxiliar para você rodar uma única vez quando for pra produção
    """
    efi = EfiPay(get_efi_credentials())
    
    headers = {
        'x-skip-mtls-checking': 'false' # true apenas no sandbox, se permitido
    }
    
    params = {
        'chave': 'sua_chave_pix_aqui@gmail.com'
    }
    
    body = {
        # O webhook exige HTTPS válido e certificado
        'webhookUrl': 'https://seu_dominio.com.br/api/webhooks/efi/'
    }
    
    try:
        response = efi.pix_config_webhook(params=params, body=body, headers=headers)
        return response
    except Exception as e:
        return {'erro': str(e)}
