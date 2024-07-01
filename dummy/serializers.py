from rest_framework import serializers
from account.models import *
from .models import *
class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['project_name', 'width', 'length', 'bedroom', 'bathroom', 'car', 'temple', 'garden', 'living_room', 'store_room']
        
class PDFSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPNG
        fields = '__all__'
        read_only_fields = ('user',)

