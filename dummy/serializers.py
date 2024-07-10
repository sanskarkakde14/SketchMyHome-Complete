from rest_framework import serializers
from account.models import *
from .models import *

class ProjectFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserFile
        fields = ['id', 'file_name', 'file_type', 'file', 'avg_value', 'area_info', 'created_at']


class UserFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserFile
        fields = '__all__'
        read_only_fields = ('user',)
class ProjectSerializer(serializers.ModelSerializer):
    files = UserFileSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ['id', 'project_name', 'width', 'length', 'bedroom', 'bathroom', 'car', 'temple', 'garden', 'living_room', 'store_room', 'created_at', 'files']
        read_only_fields = ['created_at', 'files']      
class ProjectDetailSerializer(serializers.ModelSerializer):
    files = UserFileSerializer(many=True)

    class Meta:
        model = Project
        fields = ['id', 'project_name', 'width', 'length', 'bedroom', 'bathroom', 'car', 'temple', 'garden', 'living_room', 'store_room', 'created_at', 'files']


class SoilDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SoilData
        fields = ['id', 'user', 'soil_type', 'ground_water_depth', 'foundation_type', 'created_at']

class MapFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MapFile
        fields = ['id', 'user', 'map_html', 'created_at']