# accounts/clube_ben.py
"""
Integração com o club_ben (clube de benefícios externo).

PONTO ÚNICO de integração: toda vez que o plano de um sócio muda (ativou, renovou, venceu,
trocou), `sincronizar_membro` é chamado. Enquanto CLUBE_BEN_API_URL / CLUBE_BEN_API_KEY
não estiverem configurados no .env, nada é enviado.

PENDENTE: implementar `_enviar` conforme a documentação da API do club_ben
(endpoint, autenticação, formato do cadastro e do nível do plano).
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def configurado():
    return bool(getattr(settings, 'CLUBE_BEN_API_URL', '') and getattr(settings, 'CLUBE_BEN_API_KEY', ''))


def dados_membro(perfil):
    """Dados do sócio que serão enviados ao club_ben."""
    user = perfil.user
    return {
        'id_externo': str(user.id),
        'nome': user.get_full_name() or user.username,
        'email': user.email,
        'cpf': perfil.cpf,
        'telefone': perfil.whatsapp or perfil.telefone,
        'nivel': perfil.nivel_plano,  # gratis | bronze | prata | ouro
        'torcida': perfil.torcida.nome if perfil.torcida else None,
    }


def sincronizar_membro(perfil):
    """Envia o nível atual do sócio ao club_ben. Nunca derruba o fluxo de pagamento."""
    if not configurado():
        logger.info("club_ben não configurado; sincronização de %s ignorada.", perfil.user.username)
        return False
    try:
        return _enviar(dados_membro(perfil))
    except Exception:
        logger.exception("Falha ao sincronizar %s com o club_ben.", perfil.user.username)
        return False


def _enviar(dados):
    raise NotImplementedError("Integração com a API do club_ben aguardando documentação.")
