from django.db import models
from django.contrib.auth import get_user_model
from .models import *

class Project(models.Model):
    project_name = models.CharField(max_length=255)
    width = models.IntegerField()
    length = models.IntegerField()
    bedroom = models.IntegerField()
    bathroom = models.IntegerField()
    car = models.IntegerField()
    temple = models.IntegerField()
    garden = models.IntegerField()
    living_room = models.IntegerField()
    store_room = models.IntegerField()

    def __str__(self):
        return self.project_name



class UserPNG(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    image = models.ImageField(upload_to='pngs/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.name} - {self.image.name}"
    

class SoilData(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    soil_type = models.CharField(max_length=255)
    ground_water_depth = models.CharField(max_length=255)
    foundation_type = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

class MapFile(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    map_html = models.FileField(upload_to='maps/')
    created_at = models.DateTimeField(auto_now_add=True)