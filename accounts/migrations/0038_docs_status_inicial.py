from django.db import migrations


def preencher(apps, schema_editor):
    """Quem já enviou os 3 documentos entra na fila de análise da moderação."""
    Perfil = apps.get_model('accounts', 'Perfil')
    (Perfil.objects.exclude(doc_frente='').exclude(doc_frente__isnull=True)
     .exclude(doc_verso='').exclude(doc_verso__isnull=True)
     .exclude(doc_selfie='').exclude(doc_selfie__isnull=True)
     .update(docs_status='em_analise'))


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0037_perfil_docs_analisado_em_perfil_docs_analisado_por_and_more'),
    ]

    operations = [
        migrations.RunPython(preencher, migrations.RunPython.noop),
    ]
