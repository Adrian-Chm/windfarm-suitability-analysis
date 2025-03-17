from django.db import models

# Create your models here.

from django.db import models
from django.contrib.auth.models import User
import uuid
import datetime

class AnalysisParameters(models.Model):
    """Store analysis parameters and results for revisiting later"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Region parameters
    latitude = models.FloatField()
    longitude = models.FloatField()
    buffer_radius = models.IntegerField()
    
    # Weight parameters
    weight_slope = models.FloatField()
    weight_elevation = models.FloatField()
    weight_wind = models.FloatField()
    weight_roads = models.FloatField()
    weight_landcover = models.FloatField()
    weight_natura = models.FloatField()
    
    # Threshold parameters
    threshold_slope = models.IntegerField()
    threshold_elevation = models.IntegerField()
    threshold_wind = models.FloatField()
    threshold_roads = models.IntegerField()
    threshold_natura = models.IntegerField()
    
    # Results
    mean_suitability = models.FloatField(null=True, blank=True)
    min_suitability = models.FloatField(null=True, blank=True)
    max_suitability = models.FloatField(null=True, blank=True)
    
    # Map URLs - these would be links to saved map images or folium HTML files
    suitability_map = models.TextField(null=True, blank=True)
    slope_map = models.TextField(null=True, blank=True)
    elevation_map = models.TextField(null=True, blank=True)
    wind_speed_map = models.TextField(null=True, blank=True)
    roads_map = models.TextField(null=True, blank=True)
    landcover_map = models.TextField(null=True, blank=True)
    natura_2000_map = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"Analysis at ({self.latitude}, {self.longitude}) on {self.created_at.strftime('%Y-%m-%d')}"
