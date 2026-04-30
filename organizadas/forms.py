from django import forms
from .models import Torcida

class TorcidaForm(forms.ModelForm):
    class Meta:
        model = Torcida
        fields = ['titulo', 'local', 'data', 'data_fim', 'categoria',
                   'valor', 'max_participantes', 'raio_checkin', 
                  'xp_recompensa', 'informativo', 'imagem_capa', 'ativo'
                ]
        widgets = {
            'valor': forms.NumberInput(attrs={
                'class': 'w-full bg-black/5 border-2 border-suave rounded-2xl shadow-inner px-4 py-3 text-sm font-bold texto-main focus:border-tema outline-none transition-colors',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Ex: 25.50 ou 0.00 para Grátis'
            }),
            'fundacao': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'cor_primaria': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
            'cor_secundaria': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
            'cor_terciaria': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
            'cor_fundo': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
        }
    
