from django import forms
from .models import Torcida

class TorcidaForm(forms.ModelForm):
    class Meta:
        model = Torcida
        fields = [
            'nome', 'sigla', 'fundacao', 'mascote', 'lema', 'historia', 
            'logo', 'imagem_fundo', 'cor_primaria', 'cor_secundaria', 
            'cor_terciaria', 'cor_fundo'
        ]
        widgets = {
            'fundacao': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'cor_primaria': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
            'cor_secundaria': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
            'cor_terciaria': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
            'cor_fundo': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
        }