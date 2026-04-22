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
    
class CaravanaForm(forms.ModelForm):
    class Meta:
        model = Caravana
        fields = ['titulo', 'destino', 'data_viagem', 'valor', 'vagas_totais', 'descricao', 'imagem_capa']
        widgets = {
            'data_viagem': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'destino': forms.TextInput(attrs={'class': 'form-control'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control'}),
            'vagas_totais': forms.NumberInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }