from rest_framework import serializers
from account.models import *
from .models import *
class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['project_name', 'width', 'length', 'bedroom', 'bathroom', 'car', 'temple', 'garden', 'living_room', 'store_room']
        
class UserFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserFile
        fields = '__all__' 
        read_only_fields = ('user',)

class SoilDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SoilData
        fields = ['id', 'user', 'soil_type', 'ground_water_depth', 'foundation_type', 'created_at']

class MapFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MapFile
        fields = ['id', 'user', 'map_html', 'created_at']






        