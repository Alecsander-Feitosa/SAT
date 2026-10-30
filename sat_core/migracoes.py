# sat_core/migracoes.py
"""Operações de migration que não quebram se a coluna/tabela já existir no banco.

Usadas nas migrations que, em produção, encontraram colunas e tabelas criadas fora do
controle do Django (o banco tinha a coluna/tabela, mas a migration não estava registrada).
Quando a tabela que já existe tem outra estrutura, o conteúdo dela é guardado em
"<tabela>_legado" e a tabela é recriada do jeito que o modelo espera.
"""
from django.db import migrations


def _colunas(schema_editor, tabela):
    conexao = schema_editor.connection
    with conexao.cursor() as cursor:
        return {c.name: c for c in conexao.introspection.get_table_description(cursor, tabela)}


def _tabela_existe(schema_editor, tabela):
    return tabela in schema_editor.connection.introspection.table_names()


def _tabela_compativel(schema_editor, modelo):
    existentes = _colunas(schema_editor, modelo._meta.db_table)
    esperadas = {f.column for f in modelo._meta.local_concrete_fields}
    if esperadas - set(existentes):
        return False
    # Coluna antiga obrigatória e sem valor padrão faria todo INSERT falhar
    return all(c.null_ok or getattr(c, 'default', None) is not None
               for nome, c in existentes.items() if nome not in esperadas)


def _guardar_tabela_antiga(schema_editor, tabela):
    """Copia o conteúdo para <tabela>_legado e remove a tabela incompatível."""
    q = schema_editor.quote_name
    legado, n = f'{tabela[:50]}_legado', 1
    while _tabela_existe(schema_editor, legado):
        n += 1
        legado = f'{tabela[:50]}_legado{n}'
    schema_editor.execute(f'CREATE TABLE {q(legado)} AS SELECT * FROM {q(tabela)}')
    cascade = ' CASCADE' if schema_editor.connection.vendor == 'postgresql' else ''
    schema_editor.execute(f'DROP TABLE {q(tabela)}{cascade}')


def garantir_tabela(schema_editor, modelo):
    """True se a tabela já existe com a estrutura certa; senão a (re)cria e retorna False."""
    tabela = modelo._meta.db_table
    if _tabela_existe(schema_editor, tabela):
        if _tabela_compativel(schema_editor, modelo):
            return True
        _guardar_tabela_antiga(schema_editor, tabela)
    schema_editor.create_model(modelo)
    return False


def reconciliar_tabelas(*rotulos):
    """RunPython que confere tabelas já criadas (ex: 'gamification.MedalhaUsuario')."""
    def executar(apps, schema_editor):
        for rotulo in rotulos:
            garantir_tabela(schema_editor, apps.get_model(rotulo))
    return executar


class AddFieldSeNaoExiste(migrations.AddField):
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        modelo = to_state.apps.get_model(app_label, self.model_name)
        campo = modelo._meta.get_field(self.name)
        if campo.column in _colunas(schema_editor, modelo._meta.db_table):
            return
        super().database_forwards(app_label, schema_editor, from_state, to_state)


class CreateModelSeNaoExiste(migrations.CreateModel):
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        modelo = to_state.apps.get_model(app_label, self.name)
        if self.allow_migrate_model(schema_editor.connection.alias, modelo):
            garantir_tabela(schema_editor, modelo)
