# Em produção algumas destas tabelas já existiam (criadas fora das migrations) com outra
# estrutura — ex: gamification_medalhausuario sem a coluna "codigo". Confere cada uma e,
# se for incompatível, guarda o conteúdo em "<tabela>_legado" e recria do jeito certo.
from django.db import migrations

from sat_core.migracoes import reconciliar_tabelas


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0038_docs_status_inicial'),
        ('bepe', '0004_planorota_reuniao'),
        ('gamification', '0006_medalhausuario'),
        ('social', '0009_visibilidade_posts_existentes'),
    ]

    operations = [
        migrations.RunPython(reconciliar_tabelas(
            'accounts.BeneficioTorcida', 'accounts.PassagemTorcida', 'accounts.DispositivoSessao',
            'bepe.Conversa', 'bepe.Denuncia', 'bepe.Mensagem', 'bepe.RegistroProntuario',
            'bepe.LocalizacaoTorcedor', 'bepe.PlanoRota', 'bepe.Reuniao',
            'gamification.RegistroXP', 'gamification.MedalhaUsuario',
            'social.CPFBloqueado', 'social.Notificacao', 'social.Penalidade', 'social.DenunciaPost',
        ), migrations.RunPython.noop),
    ]
