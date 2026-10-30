from django.db import migrations


def preencher(apps, schema_editor):
    """Quem já está numa torcida ganha o registro de entrada (data de cadastro como aproximação)."""
    Perfil = apps.get_model('accounts', 'Perfil')
    PassagemTorcida = apps.get_model('accounts', 'PassagemTorcida')
    for perfil in Perfil.objects.exclude(torcida__isnull=True).select_related('torcida', 'user'):
        if not PassagemTorcida.objects.filter(perfil=perfil, saida__isnull=True).exists():
            PassagemTorcida.objects.create(
                perfil=perfil, torcida=perfil.torcida, torcida_nome=perfil.torcida.nome,
                entrada=perfil.user.date_joined,
            )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0034_passagemtorcida'),
    ]

    operations = [
        migrations.RunPython(preencher, migrations.RunPython.noop),
    ]
