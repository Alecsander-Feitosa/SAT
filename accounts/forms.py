from django import forms
from django.contrib.auth.models import User
from .models import Perfil

class CadastroForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control sat-input', 'placeholder': 'Crie uma senha'}))
    cpf = forms.CharField(max_length=14, widget=forms.TextInput(attrs={'class': 'form-control sat-input', 'placeholder': '000.000.000-00'}))
    whatsapp = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'form-control sat-input', 'placeholder': '(00) 00000-0000'}))

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control sat-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-control sat-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control sat-input', 'placeholder': 'Nome completo'}),
        }

    def save(self, commit=True):
        # 1. Guarda o utilizador primeiro
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        
        if commit:
            user.save()
            # 2. Cria ou atualiza o Perfil com os dados extras do formulário
            # Usamos update_or_create para evitar o erro de "UNIQUE constraint"
            Perfil.objects.update_or_create(
                user=user,
                defaults={
                    'cpf': self.cleaned_data.get('cpf'),
                    'whatsapp': self.cleaned_data.get('whatsapp'), # Confirme se no seu model é 'telefone' ou 'whatsapp'
                }
            )
        return user

class PerfilCompletoForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = [
            'foto',
            'data_nascimento', 'rg_cnh', 
            'orgao_expedidor', 

            'cep', 
            'rua', 
            'numero', 
            'complemento', 
            'bairro',
            'cidade', 
            'uf',
            'doc_frente', 
            'doc_verso', 
            'doc_selfie',
            'vulgo', 
            'pelotao',
            'rede_social'
        ]
        widgets = {
            field: forms.TextInput(attrs={'class': 'form-control sat-input'}) 
            for field in fields if field not in ['data_nascimento', 'foto', 'foto_documento_frente', 'foto_documento_verso', 'verificacao_facial']
        }