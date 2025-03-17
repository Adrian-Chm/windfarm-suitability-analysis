from django.contrib import admin

# Register your models here.
# File: analysis/admin.py
from django.contrib import admin
from .models import AnalysisParameters

class AnalysisParametersAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'latitude', 'longitude', 'buffer_radius', 'mean_suitability')
    list_filter = ('created_at',)
    search_fields = ('id', 'latitude', 'longitude')
    readonly_fields = ('id', 'created_at')

admin.site.register(AnalysisParameters, AnalysisParametersAdmin)