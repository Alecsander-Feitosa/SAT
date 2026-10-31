from django import forms

from organizadas.models import Torcida, Evento, Caravana
from .models import RegistroProntuario, Conversa, Mensagem, Denuncia, Reuniao, DocumentoBEPE

INPUT = "w-full fundo-app border border-suave rounded-xl px-4 py-3 text-sm texto-main font-medium focus:outline-none focus:border-tema"


def _estilizar(form, classe):
    for field in form.fields.values():
        field.widget.attrs.setdefault('class', classe)


class RegistroProntuarioForm(forms.ModelForm):
    class Meta:
        model = RegistroProntuario
        fields = ['tipo', 'titulo', 'descricao', 'data_fato', 'local', 'anexo']
        widgets = {
            'data_fato': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'descricao': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _estilizar(self, INPUT)


class NovaConversaForm(forms.ModelForm):
    texto = forms.CharField(label="Mensagem", widget=forms.Textarea(attrs={'rows': 4}))

    class Meta:
        model = Conversa
        fields = ['torcida', 'assunto']

    def __init__(self, *args, torcida_fixa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['torcida'].queryset = Torcida.objects.order_by('nome')
        if torcida_fixa:
            # Diretoria só abre conversa em nome da própria torcida
            del self.fields['torcida']
        _estilizar(self, INPUT)


class MensagemForm(forms.ModelForm):
    class Meta:
        model = Mensagem
        fields = ['texto', 'anexo']
        widgets = {'texto': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Escreva sua mensagem...'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _estilizar(self, INPUT)


class DenunciaForm(forms.ModelForm):
    class Meta:
        model = Denuncia
        fields = ['categoria', 'torcida', 'descricao', 'local', 'data_fato', 'anexo']
        widgets = {
            'data_fato': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'descricao': forms.Textarea(attrs={'rows': 6, 'placeholder': 'Descreva com o máximo de detalhes possível. Não se identifique.'}),
        }
        labels = {'torcida': 'Torcida envolvida (opcional)'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['torcida'].queryset = Torcida.objects.order_by('nome')
        _estilizar(self, INPUT)


class DenunciaGestaoForm(forms.ModelForm):
    class Meta:
        model = Denuncia
        fields = ['status', 'resposta_publica', 'nota_interna']
        widgets = {
            'resposta_publica': forms.Textarea(attrs={'rows': 3}),
            'nota_interna': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _estilizar(self, INPUT)


class ReuniaoForm(forms.ModelForm):
    class Meta:
        model = Reuniao
        fields = ['titulo', 'data_hora', 'duracao_min', 'torcidas', 'pauta', 'link_externo']
        widgets = {
            'data_hora': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'pauta': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Assuntos da reunião'}),
            'torcidas': forms.CheckboxSelectMultiple,
            'link_externo': forms.URLInput(attrs={'placeholder': 'https://meet.google.com/... ou https://zoom.us/j/...'}),
        }
        labels = {'torcidas': 'Diretorias convidadas', 'titulo': 'Título'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['torcidas'].queryset = Torcida.objects.order_by('nome')
        self.fields['torcidas'].required = True
        for nome, field in self.fields.items():
            if nome != 'torcidas':
                field.widget.attrs.setdefault('class', INPUT)


class DocumentoForm(forms.ModelForm):
    class Meta:
        model = DocumentoBEPE
        fields = ['titulo', 'evento', 'caravana', 'descricao', 'arquivo']
        widgets = {'descricao': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Informações para o BEPE (opcional)'})}
        labels = {'evento': 'Evento relacionado (opcional)', 'caravana': 'Caravana relacionada (opcional)'}

    def __init__(self, *args, torcida=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['evento'].queryset = Evento.objects.filter(torcida=torcida).order_by('-data')
        self.fields['caravana'].queryset = Caravana.objects.filter(torcida=torcida).order_by('-saida_horario')
        _estilizar(self, INPUT)
