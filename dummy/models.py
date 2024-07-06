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



class UserFile(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    png_image = models.ImageField(upload_to='pngs/',null=True, blank=True)
    dxf_file = models.FileField(upload_to='dxfs/',null=True, blank=True)
    avg_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    area_info = models.JSONField(null=True, blank=True)
    def __str__(self):
        return f"UserFile(user={self.user}, png_image={self.png_image}, dxf_file={self.dxf_file})"
    

class SoilData(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    soil_type = models.CharField(max_length=255)
    ground_water_depth = models.CharField(max_length=255)
    foundation_type = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"user={self.user}, created_at={self.created_at}"

class MapFile(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    map_html = models.FileField(upload_to='maps/')
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"user={self.user}, created_at={self.created_at}), file={self.map_html}"
    




    