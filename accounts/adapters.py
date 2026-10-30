from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.urls import reverse

from organizadas.models import Torcida

from .models import Perfil


class ContaAdapter(DefaultAccountAdapter):
    def get_signup_redirect_url(self, request):
        # Conta nova criada pelo Google/Apple/Facebook: escolhe time e torcida na Etapa 2
        if request.session.get('novo_usuario_id'):
            return reverse('cadastro_etapa2')
        return super().get_signup_redirect_url(request)


class SocialAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        # O Perfil não é criado por signal; o cadastro normal também cria na mão (CadastroForm.save)
        perfil, _ = Perfil.objects.get_or_create(user=user)

        # Mesmo comportamento do cadastro normal: se veio do link de uma torcida, já vincula
        torcida_id = request.session.get('torcida_pre_selecionada')
        torcida_pre = Torcida.objects.filter(id=torcida_id).first() if torcida_id else None
        if torcida_pre:
            perfil.torcida = torcida_pre
            perfil.aprovado = torcida_pre.aprovacao_automatica
            perfil.save()

        # A Etapa 2 usa este ID para saber quem está completando o cadastro
        request.session['novo_usuario_id'] = user.id
        request.session.modified = True
        return user
