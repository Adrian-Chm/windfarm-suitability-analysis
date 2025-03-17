# File: analysis/forms.py
from django import forms
from .models import AnalysisParameters

class AnalysisForm(forms.ModelForm):
    """Form for collecting wind farm analysis parameters"""
    
    class Meta:
        model = AnalysisParameters
        fields = [
            'latitude', 'longitude', 'buffer_radius',
            'weight_slope', 'weight_elevation', 'weight_wind', 
            'weight_roads', 'weight_landcover', 'weight_natura',
            'threshold_slope', 'threshold_elevation', 'threshold_wind', 
            'threshold_roads', 'threshold_natura'
        ]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set default values
        if not args and not kwargs.get('instance'):
            self.fields['latitude'].initial = 50.5
            self.fields['longitude'].initial = 2.0
            self.fields['buffer_radius'].initial = 25
            
            self.fields['weight_slope'].initial = 0.3
            self.fields['weight_elevation'].initial = 0.2
            self.fields['weight_wind'].initial = 0.6
            self.fields['weight_roads'].initial = 0.2
            self.fields['weight_landcover'].initial = 0.4
            self.fields['weight_natura'].initial = 0.3
            
            self.fields['threshold_slope'].initial = 5
            self.fields['threshold_elevation'].initial = 200
            self.fields['threshold_wind'].initial = 2.0
            self.fields['threshold_roads'].initial = 50
            self.fields['threshold_natura'].initial = 2000
        
        # Add labels and help texts
        self.fields['latitude'].widget.attrs.update({'class': 'form-control'})
        self.fields['latitude'].help_text = 'Enter the latitude in decimal degrees'
        
        self.fields['longitude'].widget.attrs.update({'class': 'form-control'})
        self.fields['longitude'].help_text = 'Enter the longitude in decimal degrees'
        
        self.fields['buffer_radius'].widget.attrs.update({'class': 'form-control'})
        self.fields['buffer_radius'].help_text = 'Radius around the coordinates to analyze (km)'
        
        # Add min/max constraints to form fields
        self.fields['latitude'].widget.attrs.update({'min': -90, 'max': 90, 'step': 0.0001})
        self.fields['longitude'].widget.attrs.update({'min': -180, 'max': 180, 'step': 0.0001})
        self.fields['buffer_radius'].widget.attrs.update({'min': 5, 'max': 100, 'step': 5})
        
        weight_fields = ['weight_slope', 'weight_elevation', 'weight_wind', 
                         'weight_roads', 'weight_landcover', 'weight_natura']
        
        for field in weight_fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-range', 
                'min': 0.0, 
                'max': 1.0, 
                'step': 0.1,
                'type': 'range'
            })
            self.fields[field].help_text = f'Weight for {field.split("_")[1]} factor (0.0-1.0)'
        
        self.fields['threshold_slope'].widget.attrs.update({
            'class': 'form-range', 'min': 1, 'max': 20, 'type': 'range'
        })
        self.fields['threshold_slope'].help_text = 'Maximum suitable slope (degrees)'
        
        self.fields['threshold_elevation'].widget.attrs.update({
            'class': 'form-range', 'min': 50, 'max': 1000, 'type': 'range'
        })
        self.fields['threshold_elevation'].help_text = 'Maximum suitable elevation (m)'
        
        self.fields['threshold_wind'].widget.attrs.update({
            'class': 'form-range', 'min': 1.0, 'max': 10.0, 'step': 0.5, 'type': 'range'
        })
        self.fields['threshold_wind'].help_text = 'Minimum suitable wind speed (m/s)'
        
        self.fields['threshold_roads'].widget.attrs.update({
            'class': 'form-range', 'min': 0, 'max': 1000, 'step': 50, 'type': 'range'
        })
        self.fields['threshold_roads'].help_text = 'Minimum distance to roads (m)'
        
        self.fields['threshold_natura'].widget.attrs.update({
            'class': 'form-range', 'min': 500, 'max': 10000, 'step': 500, 'type': 'range'
        })
        self.fields['threshold_natura'].help_text = 'Minimum distance to Natura 2000 sites (m)'