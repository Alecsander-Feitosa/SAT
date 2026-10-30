from decimal import Decimal

from django.db import migrations

# Planos oficiais SAT — valem para todas as torcidas. Os benefícios são editáveis no /admin.
PLANOS = [
    ('gratis', 'Grátis', Decimal('0.00'), False,
     "Carteirinha digital SAT\nMural, eventos e notícias da torcida\nCanal Fale com o BEPE"),
    ('bronze', 'Bronze', Decimal('14.90'), False,
     "Tudo do plano Grátis\nClube de benefícios: nível Bronze"),
    ('prata', 'Prata', Decimal('34.90'), True,
     "Tudo do plano Bronze\nClube de benefícios: nível Prata"),
    ('ouro', 'Ouro', Decimal('59.90'), False,
     "Tudo do plano Prata\nClube de benefícios: nível Ouro"),
]


def criar_planos(apps, schema_editor):
    PlanoSocio = apps.get_model('accounts', 'PlanoSocio')
    for nivel, nome, preco, destaque, beneficios in PLANOS:
        PlanoSocio.objects.update_or_create(
            torcida=None, nivel=nivel,
            defaults={'nome': nome, 'preco': preco, 'destaque': destaque, 'beneficios': beneficios, 'ativo': True},
        )
    # Planos livres antigos das torcidas saem da vitrine (não são apagados por segurança)
    PlanoSocio.objects.filter(nivel__isnull=True).update(ativo=False)


def desfazer(apps, schema_editor):
    PlanoSocio = apps.get_model('accounts', 'PlanoSocio')
    PlanoSocio.objects.filter(torcida=None, nivel__isnull=False, assinatura__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0032_assinatura_valida_ate_planosocio_nivel_and_more'),
    ]

    operations = [
        migrations.RunPython(criar_planos, desfazer),
    ]
