# sat_core/migracoes.py
"""Operações de migration que não quebram se a coluna/tabela já existir no banco.

Usadas nas migrations que, em produção, encontraram colunas criadas fora do controle
do Django (o banco tinha a coluna, mas a migration não estava registrada).
"""
from django.db import migrations


def _colunas(schema_editor, tabela):
    conexao = schema_editor.connection
    with conexao.cursor() as cursor:
        return {c.name for c in conexao.introspection.get_table_description(cursor, tabela)}


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
        if modelo._meta.db_table in schema_editor.connection.introspection.table_names():
            return
        super().database_forwards(app_label, schema_editor, from_state, to_state)
