from django.shortcuts import render

# Create your views here.
# File: analysis/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from .forms import AnalysisForm
from .models import AnalysisParameters
from .gee_utils import run_suitability_analysis, create_region_of_interest
import ee
import geemap.foliumap as geemap
import json
import os
from django.conf import settings

BASE_DIR = settings.BASE_DIR

def index(request):
    """Home page with analysis form"""
    if request.method == 'POST':
        form = AnalysisForm(request.POST)
        if form.is_valid():
            # Save parameters
            params = form.save()
            
            # Redirect to results page with ID
            return redirect('analysis:results', analysis_id=params.id)
    else:
        form = AnalysisForm()
    
    # For GET requests or invalid forms
    return render(request, 'analysis/index.html', {'form': form})

def results(request, analysis_id):
    """Results page showing analysis results"""
    # Get analysis parameters
    params = get_object_or_404(AnalysisParameters, id=analysis_id)
    
    # Check if analysis has been run (based on whether maps exist)
    if not params.suitability_map:
        # Run analysis
        results = run_suitability_analysis(params)
        
        if not results['success']:
            messages.error(request, f"Analysis failed: {results.get('error_message', 'Unknown error')}")
            return redirect('analysis:index')
    
    # Prepare context for template
    context = {
        'params': params,
        'maps': {
            'suitability': params.suitability_map,
            'slope': params.slope_map,
            'elevation': params.elevation_map,
            'wind_speed': params.wind_speed_map,
            'roads': params.roads_map,
            'landcover': params.landcover_map,
            'natura_2000': params.natura_2000_map
        },
        'stats': {
            'mean_suitability': params.mean_suitability,
            'min_suitability': params.min_suitability,
            'max_suitability': params.max_suitability
        }
    }
    
    return render(request, 'analysis/results.html', context)

def preview_area(request):
    """AJAX endpoint to generate a simplified preview of the analysis area"""
    if request.method == 'GET':
        try:
            # Get parameters from request
            lat = float(request.GET.get('latitude', 50.5))
            lon = float(request.GET.get('longitude', 2.0))
            buffer_radius = int(request.GET.get('buffer_radius', 25))
            
            # Create a simple HTML representation of the preview using Leaflet
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Analysis Region Preview</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
                <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
                <style>
                    body {{ margin: 0; padding: 0; }}
                    html, body, #map {{ height: 100%; width: 100%; }}
                    .info-box {{
                        background: white;
                        padding: 8px;
                        border-radius: 4px;
                        box-shadow: 0 0 15px rgba(0,0,0,0.2);
                        position: absolute;
                        bottom: 10px;
                        left: 10px;
                        z-index: 1000;
                        font-family: Arial, sans-serif;
                        font-size: 12px;
                    }}
                </style>
            </head>
            <body>
                <div id="map"></div>
                <div class="info-box">
                    <strong>Analysis Region</strong><br>
                    Center: {lat}, {lon}<br>
                    Radius: {buffer_radius} km
                </div>
                <script>
                    // Create the map centered at the specified coordinates
                    var map = L.map('map').setView([{lat}, {lon}], 9);
                    
                    // Add satellite imagery layer
                    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                        attribution: 'Imagery &copy; Esri'
                    }}).addTo(map);
                    
                    // Add a terrain/topo layer
                    var topoLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                        attribution: 'Imagery &copy; Esri'
                    }});
                    
                    // Add layer control
                    var baseLayers = {{
                        "Satellite": map.getPane('tilePane').lastChild,
                        "Topographic": topoLayer
                    }};
                    L.control.layers(baseLayers).addTo(map);
                    
                    // Create a circle representing the analysis area
                    var circle = L.circle([{lat}, {lon}], {{
                        color: 'red',
                        fillColor: '#f03',
                        fillOpacity: 0.2,
                        radius: {buffer_radius * 1000}  // Convert km to meters
                    }}).addTo(map);
                    
                    // Add a marker at the center
                    L.marker([{lat}, {lon}]).addTo(map)
                        .bindPopup("<strong>Analysis Center</strong><br>Lat: {lat}, Lon: {lon}")
                        .openPopup();
                </script>
            </body>
            </html>
            """
            
            # Save the HTML to a file
            preview_path = os.path.join(BASE_DIR, 'static', 'preview_maps')
            os.makedirs(preview_path, exist_ok=True)
            
            map_filename = f"preview_{lat}_{lon}_{buffer_radius}.html"
            map_path = os.path.join(preview_path, map_filename)
            
            with open(map_path, 'w') as f:
                f.write(html)
                
            # Return URL to preview map
            map_url = f'/static/preview_maps/{map_filename}'
            print(f"Generated preview map at: {map_url}")
            
            return JsonResponse({
                'success': True,
                'map_url': map_url
            })
            
        except Exception as e:
            print(f"Error generating preview: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

def export_analysis(request, analysis_id):
    """Endpoint to export analysis results"""
    params = get_object_or_404(AnalysisParameters, id=analysis_id)
    
    # Generate a JSON export of the parameters and results
    export_data = {
        'id': str(params.id),
        'created_at': params.created_at.isoformat(),
        'parameters': {
            'region': {
                'latitude': params.latitude,
                'longitude': params.longitude,
                'buffer_radius_km': params.buffer_radius
            },
            'weights': {
                'slope': params.weight_slope,
                'elevation': params.weight_elevation,
                'wind': params.weight_wind,
                'roads': params.weight_roads,
                'landcover': params.weight_landcover,
                'natura_2000': params.weight_natura
            },
            'thresholds': {
                'slope_degrees': params.threshold_slope,
                'elevation_meters': params.threshold_elevation,
                'wind_speed_ms': params.threshold_wind,
                'roads_distance_m': params.threshold_roads,
                'natura_2000_distance_m': params.threshold_natura
            }
        },
        'results': {
            'mean_suitability': params.mean_suitability,
            'min_suitability': params.min_suitability,
            'max_suitability': params.max_suitability
        }
    }
    
    # Create response with JSON file
    response = HttpResponse(json.dumps(export_data, indent=2), content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="windfarm_analysis_{params.id}.json"'
    
    return response

def test_static_file(request):
    """Create and return a simple test file"""
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Static Test</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
                margin-top: 50px;
                background-color: #f0f0f0;
            }
            .test-box {
                display: inline-block;
                padding: 20px;
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
            }
        </style>
    </head>
    <body>
        <div class="test-box">
            <h1>Static File Test</h1>
            <p>If you can see this, static files are working properly.</p>
        </div>
    </body>
    </html>
    """
    
    # Save this simple HTML file
    test_path = os.path.join(BASE_DIR, 'static', 'test.html')
    with open(test_path, 'w') as f:
        f.write(test_html)
    
    return JsonResponse({
        'success': True,
        'test_url': '/static/test.html'
    })

def simple_preview(request):
    """Generate a map preview with satellite imagery"""
    if request.method == 'GET':
        try:
            # Get parameters from request
            lat = float(request.GET.get('latitude', 50.5))
            lon = float(request.GET.get('longitude', 2.0))
            buffer_radius = int(request.GET.get('buffer_radius', 25))
            
            # Create an enhanced HTML file with Leaflet and satellite imagery
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Satellite Preview</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
                <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
                <style>
                    body, html, #map {{
                        height: 100%;
                        margin: 0;
                        padding: 0;
                    }}
                    .info-box {{
                        background: white;
                        padding: 8px;
                        border-radius: 4px;
                        box-shadow: 0 0 15px rgba(0,0,0,0.2);
                        position: absolute;
                        bottom: 10px;
                        right: 10px;
                        z-index: 1000;
                        font-family: Arial, sans-serif;
                        font-size: 12px;
                        max-width: 180px;
                        line-height: 1.4;
                    }}
                    .circle-label {{
                        background: rgba(255,255,255,0.8);
                        border: none;
                        border-radius: 50%;
                        text-align: center;
                    }}
                </style>
            </head>
            <body>
                <div id="map"></div>
                <div class="info-box">
                    <strong>Analysis Region</strong><br>
                    Center: {lat:.4f}, {lon:.4f}<br>
                    Radius: {buffer_radius} km
                </div>
                <script>
                    // Initialize map centered at the specified coordinates
                    var map = L.map('map').setView([{lat}, {lon}], 10);
                    
                    // Add Esri satellite imagery layer (no API key required)
                    var satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                        attribution: 'Imagery &copy; Esri',
                        maxZoom: 19
                    }}).addTo(map);
                    
                    // Add OpenStreetMap as an alternative layer
                    var streetsLayer = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                        attribution: '&copy; OpenStreetMap contributors',
                        maxZoom: 19
                    }});
                    
                    // Add Esri Topographic map as another option
                    var topoLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                        attribution: 'Imagery &copy; Esri',
                        maxZoom: 19
                    }});
                    
                    // Create layer control for basemaps
                    var baseLayers = {{
                        "Satellite": satelliteLayer,
                        "Streets": streetsLayer,
                        "Topographic": topoLayer
                    }};
                    
                    L.control.layers(baseLayers).addTo(map);
                    
                    // Create a circle representing the analysis area
                    // Using a bright color with border that will be visible on satellite imagery
                    var circle = L.circle([{lat}, {lon}], {{
                        color: 'red',
                        weight: 3,
                        fillColor: 'yellow',
                        fillOpacity: 0.15,
                        radius: {buffer_radius * 1000}  // Convert km to meters
                    }}).addTo(map);
                    
                    // Add a marker at the center
                    var marker = L.marker([{lat}, {lon}]).addTo(map);
                    marker.bindPopup("<strong>Analysis Center</strong><br>Latitude: {lat:.4f}<br>Longitude: {lon:.4f}");
                    
                    // Display radius on the circle (approximate position calculation)
                    var radiusLabelPos = getPointOnCircle({lat}, {lon}, {buffer_radius * 1000}, 45);
                    var radiusLabel = L.marker(radiusLabelPos, {{
                        icon: L.divIcon({{
                            className: 'circle-label',
                            html: '<div style="padding:3px 6px;background:white;border-radius:3px;font-size:11px;font-weight:bold;box-shadow:0 0 3px rgba(0,0,0,0.3);">{buffer_radius} km</div>',
                            iconSize: [40, 20],
                            iconAnchor: [20, 10]
                        }})
                    }}).addTo(map);
                    
                    // Helper function to calculate a point on the circle edge
                    function getPointOnCircle(lat, lng, radiusMeters, angleDegrees) {{
                        // Earth radius in meters
                        var earthRadius = 6378137;
                        
                        // Convert angle from degrees to radians
                        var angleRadians = angleDegrees * Math.PI / 180;
                        
                        // Convert latitude and longitude to radians
                        var latRad = lat * Math.PI / 180;
                        var lngRad = lng * Math.PI / 180;
                        
                        // Calculate distance in radians
                        var distanceRadians = radiusMeters / earthRadius;
                        
                        // Calculate new latitude
                        var newLatRad = Math.asin(
                            Math.sin(latRad) * Math.cos(distanceRadians) + 
                            Math.cos(latRad) * Math.sin(distanceRadians) * Math.cos(angleRadians)
                        );
                        
                        // Calculate new longitude
                        var newLngRad = lngRad + Math.atan2(
                            Math.sin(angleRadians) * Math.sin(distanceRadians) * Math.cos(latRad),
                            Math.cos(distanceRadians) - Math.sin(latRad) * Math.sin(newLatRad)
                        );
                        
                        // Convert back to degrees
                        var newLat = newLatRad * 180 / Math.PI;
                        var newLng = newLngRad * 180 / Math.PI;
                        
                        return [newLat, newLng];
                    }}
                </script>
            </body>
            </html>
            """
            
            # Save the file
            filename = f"satellite_preview_{lat}_{lon}.html"
            file_path = os.path.join(BASE_DIR, 'static', filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html)
            
            return JsonResponse({
                'success': True,
                'url': f'/static/{filename}'
            })
            
        except Exception as e:
            print(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})