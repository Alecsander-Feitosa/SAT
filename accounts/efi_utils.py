from django.conf import settings
from efipay import EfiPay
import uuid
from datetime import timedelta, date

def get_efi_credentials():
    return {
        'client_id': settings.EFI_CLIENT_ID,
        'client_secret': settings.EFI_CLIENT_SECRET,
        'sandbox': settings.EFI_SANDBOX,
        'certificate': settings.EFI_CERTIFICADO,
    }

def get_efi_credentials_charges():
    """Credenciais para a API de Cobranças (boleto/cartão) — sem certificado"""
    return {
        'client_id': settings.EFI_CLIENT_ID,
        'client_secret': settings.EFI_CLIENT_SECRET,
        'sandbox': settings.EFI_SANDBOX,
    }

# ==========================================
# PIX (já existente)
# ==========================================

def gerar_cobranca_pix(obj, tipo='fatura'):
    try:
        efi = EfiPay(get_efi_credentials())
        
        # Gera um txid único garantido
        txid = uuid.uuid4().hex[:35]
        
        if tipo == 'fatura':
            valor_obj = obj.valor
            descricao = f'Fatura {obj.id} - {obj.assinatura.plano.nome}'
        elif tipo == 'inscricao':
            valor_obj = obj.total
            descricao = f'Inscrição #{obj.id} - {obj.item_titulo()}'
        else:
            valor_obj = obj.total
            descricao = f'Pedido Loja {obj.id}'        
        # 1. Criar a cobrança PIX imediata
        body = {
            'calendario': {
                'expiracao': 3600
            },
            'valor': {
                'original': f"{valor_obj:.2f}"
            },
            'chave': settings.EFI_CHAVE_PIX,
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
        pix_copia_e_cola = response.get('pixCopiaECola')
        pix_qrcode = None
        
        if loc_id:
            params = {'id': loc_id}
            qr_response = efi.pix_generate_qrcode(params=params)
            
            if isinstance(qr_response, Exception) or 'erro' in qr_response or 'error' in qr_response:
                # O PIX foi criado, mas faltou permissão para a imagem do QR Code
                if 'error' in qr_response and qr_response.get('error') == 'insufficient_scope':
                    return {'sucesso': False, 'erro': 'A sua aplicação na Efí Bank não tem a permissão (Escopo) "loc.read" ou "pix.read". Vá ao painel da Efí, edite sua aplicação e marque TODAS as caixinhas de permissões da API Pix para gerar a imagem do QR Code.'}
                return {'sucesso': False, 'erro': f"Erro ao gerar QR Code: {qr_response}"}
                
            pix_copia_e_cola = qr_response.get('qrcode') or pix_copia_e_cola
            pix_qrcode = qr_response.get('imagemQrcode')
            
        obj.txid = txid
        obj.loc_id = loc_id
        obj.pix_copia_e_cola = pix_copia_e_cola
        obj.pix_qrcode = pix_qrcode
        obj.save()
            
        return {
            'sucesso': True,
            'txid': txid,
            'qrcode_image': obj.pix_qrcode,
            'copia_e_cola': obj.pix_copia_e_cola
        }
        
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


# ==========================================
# BOLETO BANCÁRIO
# ==========================================

def gerar_cobranca_boleto(pedido, cpf, nome, email):
    """
    Cria uma cobrança via boleto bancário na Efí Bank.
    Fluxo: create_charge → define_pay_method (banking_billet)
    """
    try:
        efi = EfiPay(get_efi_credentials_charges())
        
        valor_centavos = int(float(pedido.total) * 100)
        
        # Verifica se é InscricaoPagamento ou Pedido
        if hasattr(pedido, 'tipo'):
            nome_item = f'Inscrição #{pedido.id} - {pedido.item_titulo()}'
        else:
            nome_item = f'Pedido Loja #{pedido.id}'

        # 1. Criar a cobrança
        charge_body = {
            'items': [{
                'name': nome_item,
                'value': valor_centavos,
                'amount': 1
            }]
        }
        
        charge_response = efi.create_charge(body=charge_body)
        
        if 'code' not in charge_response or charge_response['code'] != 200:
            erro_msg = charge_response.get('message', str(charge_response))
            return {'sucesso': False, 'erro': f'Erro ao criar cobrança: {erro_msg}'}
        
        charge_id = charge_response['data']['charge_id']
        
        # 2. Definir método de pagamento como boleto
        vencimento = (date.today() + timedelta(days=5)).strftime('%Y-%m-%d')
        
        pay_body = {
            'payment': {
                'banking_billet': {
                    'expire_at': vencimento,
                    'customer': {
                        'name': nome,
                        'cpf': cpf.replace('.', '').replace('-', ''),
                        'email': email
                    }
                }
            }
        }
        
        pay_response = efi.define_pay_method(params={'id': charge_id}, body=pay_body)
        
        if 'code' not in pay_response or pay_response['code'] != 200:
            erro_msg = pay_response.get('message', str(pay_response))
            return {'sucesso': False, 'erro': f'Erro ao gerar boleto: {erro_msg}'}
        
        boleto_data = pay_response.get('data', {})
        
        # Salvar no pedido
        pedido.txid = str(charge_id)
        pedido.pix_copia_e_cola = boleto_data.get('barcode', '')  # Reutiliza campo para linha digitável
        pedido.pix_qrcode = boleto_data.get('pdf', {}).get('charge', '') or boleto_data.get('link', '')
        pedido.save()
        
        return {
            'sucesso': True,
            'charge_id': charge_id,
            'boleto_link': pedido.pix_qrcode,
            'boleto_barcode': pedido.pix_copia_e_cola,
            'vencimento': vencimento
        }
        
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


# ==========================================
# CARTÃO DE CRÉDITO
# ==========================================

def gerar_cobranca_cartao(pedido, payment_token, cpf, nome, email, nascimento, telefone, endereco_dados):
    """
    Cria uma cobrança via cartão de crédito na Efí Bank.
    O payment_token é gerado no frontend via JS SDK da Efí.
    Fluxo: create_charge → define_pay_method (credit_card)
    """
    try:
        efi = EfiPay(get_efi_credentials_charges())
        
        valor_centavos = int(float(pedido.total) * 100)
        
        # Verifica se é InscricaoPagamento ou Pedido
        if hasattr(pedido, 'tipo'):
            nome_item = f'Inscrição #{pedido.id} - {pedido.item_titulo()}'
        else:
            nome_item = f'Pedido Loja #{pedido.id}'

        # 1. Criar a cobrança
        charge_body = {
            'items': [{
                'name': nome_item,
                'value': valor_centavos,
                'amount': 1
            }]
        }
        
        charge_response = efi.create_charge(body=charge_body)
        
        if 'code' not in charge_response or charge_response['code'] != 200:
            erro_msg = charge_response.get('message', str(charge_response))
            return {'sucesso': False, 'erro': f'Erro ao criar cobrança: {erro_msg}'}
        
        charge_id = charge_response['data']['charge_id']
        
        # 2. Definir método de pagamento como cartão de crédito
        parcelas = 1  # Pode ser expandido futuramente
        
        pay_body = {
            'payment': {
                'credit_card': {
                    'installments': parcelas,
                    'payment_token': payment_token,
                    'billing_address': {
                        'street': endereco_dados.get('rua', ''),
                        'number': endereco_dados.get('numero', ''),
                        'neighborhood': endereco_dados.get('bairro', ''),
                        'zipcode': endereco_dados.get('cep', '').replace('-', ''),
                        'city': endereco_dados.get('cidade', ''),
                        'state': endereco_dados.get('estado', ''),
                    },
                    'customer': {
                        'name': nome,
                        'cpf': cpf.replace('.', '').replace('-', ''),
                        'email': email,
                        'birth': nascimento,
                        'phone_number': telefone.replace('(', '').replace(')', '').replace(' ', '').replace('-', '')
                    }
                }
            }
        }
        
        pay_response = efi.define_pay_method(params={'id': charge_id}, body=pay_body)
        
        if 'code' not in pay_response or pay_response['code'] != 200:
            erro_msg = pay_response.get('message', str(pay_response))
            return {'sucesso': False, 'erro': f'Erro ao processar cartão: {erro_msg}'}
        
        # Cartão aprovado: atualiza o pedido
        pedido.txid = str(charge_id)
        pedido.status = 'pago'
        pedido.save()
        
        return {
            'sucesso': True,
            'charge_id': charge_id,
            'installments': parcelas
        }
        
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


# ==========================================
# WEBHOOK
# ==========================================

def configurar_webhook():
    """
    Função auxiliar para você rodar uma única vez quando for pra produção
    """
    efi = EfiPay(get_efi_credentials())
    
    headers = {
        'x-skip-mtls-checking': 'false' # true apenas no sandbox, se permitido
    }
    
    params = {
        'chave': settings.EFI_CHAVE_PIX
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
