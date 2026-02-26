from rest_framework import serializers
from .models import Perfil

class PerfilSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Perfil
        # Usei 'foto' porque é o nome que está no seu models.py
        fields = ['username', 'vulgo', 'foto']