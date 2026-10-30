from django.db import migrations


def preencher(apps, schema_editor):
    """Posts antigos com torcida eram do feed da torcida; os demais, globais."""
    Post = apps.get_model('social', 'Post')
    Post.objects.filter(torcida__isnull=False).update(visibilidade='torcida')
    Post.objects.filter(torcida__isnull=True).update(visibilidade='global')


class Migration(migrations.Migration):

    dependencies = [
        ('social', '0008_comentario_oculto_post_em_revisao_post_tipo_and_more'),
    ]

    operations = [
        migrations.RunPython(preencher, migrations.RunPython.noop),
    ]
