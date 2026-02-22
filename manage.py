#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    """Run administrative tasks."""
    # Define o arquivo de configurações do projeto (sat_core)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sat_core.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

# ATENÇÃO: As linhas abaixo NÃO podem ter espaços no início.
# Elas devem estar encostadas na margem esquerda.
if __name__ == '__main__':
    main()