# File: analysis/gee_utils.py
import ee
import geemap.foliumap as geemap
import os
import tempfile
import uuid
from django.conf import settings

# Initialize Earth Engine (in a production app, you would need a service account)
try:
    ee.Initialize(project='ee-chmilew')
except Exception as e:
    print(f"Error initializing Earth Engine: {e}")

def create_region_of_interest(lat, lon, buffer_km):
    """Convert a point and buffer into a circular region for analysis."""
    point = ee.Geometry.Point([lon, lat])
    buffer_m = buffer_km * 1000  # Convert km to m
    return point.buffer(buffer_m)

def calculate_wind_speed(image):
    """Calculate the magnitude of wind from u and v components."""
    u = image.select('u_component_of_wind_10m')
    v = image.select('v_component_of_wind_10m')
    return image.addBands(u.hypot(v).rename('wind_speed'))

def create_map(image, region, vis_params, title, landcover_legend=False, output_dir=None):
    """Create an interactive map for a specific analysis layer.
    
    Args:
        image: Earth Engine image
        region: Earth Engine geometry
        vis_params: Visualization parameters
        title: Title for the map
        landcover_legend: Whether to add a landcover legend
        output_dir: Directory to save map HTML file
        
    Returns:
        Map object and path to the saved HTML file
    """
    m = geemap.Map()
    m.centerObject(region, 9)
    m.addLayer(image, vis_params, title)
    
    # Add colorbar
    m.add_colorbar(vis_params=vis_params, label=title, orientation='horizontal', position='bottomright')
    
    # Add region boundary
    empty = ee.Image().byte()
    outline = empty.paint(featureCollection=ee.FeatureCollection([ee.Feature(region)]), color=1, width=2)
    m.addLayer(outline, {'palette': 'FF0000'}, 'Region Boundary')
    
    # Add Natura 2000 sites if available in the region
    try:
        natura_2000_sites = ee.FeatureCollection('projects/ee-chmilew/assets/sic')
        natura_2000_region = natura_2000_sites.filterBounds(region)
        sites_style = {'color': '0000FF', 'fillColor': '0000FF80'}  # Blue with transparency
        m.addLayer(natura_2000_region.style(**sites_style), {}, 'Natura 2000 Sites')
    except Exception as e:
        print(f"Could not load Natura 2000 sites: {e}")
    
    # Add a custom legend if the map is for land cover
    if landcover_legend:
        legend_dict = {
            "0: Unknown": "#282828",
            "20: Shrubs": "#ffbb22",
            "30: Herbaceous vegetation": "#ffff4c",
            "40: Cultivated / Agriculture": "#f096ff",
            "50: Urban / Built up": "#fa0000",
            "60: Bare / Sparse vegetation": "#b4b4b4",
            "70: Snow and Ice": "#f0f0f0",
            "80: Permanent water bodies": "#0032c8",
            "90: Herbaceous wetland": "#0096a0",
            "100: Moss and lichen": "#fae6a0",
            "111-126: Forest": "#009900",
            "200: Oceans, seas": "#000080"
        }
        m.add_legend(title="Land Cover Categories", legend_dict=legend_dict, position='bottomleft')
    
    # Save map to file if output_dir is provided
    map_path = None
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        unique_id = uuid.uuid4().hex[:8]
        safe_title = title.replace(' ', '_').replace('(', '').replace(')', '').replace('%', 'pct')
        map_path = os.path.join(output_dir, f"map_{safe_title}_{unique_id}.html")
        m.to_html(map_path)
    
    return m, map_path

def run_suitability_analysis(params):
    """Perform the complete wind farm suitability analysis for a given region.
    
    Args:
        params: AnalysisParameters object containing all necessary parameters
        
    Returns:
        Dictionary with results and map paths
    """
    # Extract parameters
    lat = params.latitude
    lon = params.longitude
    buffer_radius = params.buffer_radius
    
    # Get all weights and thresholds
    weight_slope = params.weight_slope
    weight_elevation = params.weight_elevation
    weight_wind = params.weight_wind
    weight_roads = params.weight_roads
    weight_landcover = params.weight_landcover
    weight_natura = params.weight_natura
    
    threshold_slope = params.threshold_slope
    threshold_elevation = params.threshold_elevation
    threshold_wind = params.threshold_wind
    threshold_roads = params.threshold_roads
    threshold_natura = params.threshold_natura
    
    # Create temporary directory for map files
    maps_output_dir = os.path.join(settings.BASE_DIR, 'static', 'maps', str(params.id))
    
    # Create region of interest
    region = create_region_of_interest(lat, lon, buffer_radius)
    
    # Create maps directory
    os.makedirs(maps_output_dir, exist_ok=True)
    
    # Dictionary to store results
    results = {
        'maps': {},
        'stats': {}
    }
    
    try:
        # Load elevation data
        elevation = ee.Image('USGS/SRTMGL1_003').select('elevation').clip(region)
        slope = ee.Terrain.slope(elevation)
        
        # Load wind speed data
        wind_speed = ee.ImageCollection('ECMWF/ERA5/MONTHLY') \
            .filter(ee.Filter.date('2018-01-01', '2021-01-01')) \
            .map(calculate_wind_speed) \
            .select('wind_speed') \
            .mean() \
            .clip(region)
        
        # Load urban areas and land cover data
        urban_areas = ee.ImageCollection("COPERNICUS/Landcover/100m/Proba-V-C3/Global") \
            .filter(ee.Filter.date('2019-01-01', '2020-01-01')) \
            .first() \
            .select('urban-coverfraction') \
            .clip(region)
        
        urban_distance = urban_areas.gt(20).Not().cumulativeCost(ee.Image.constant(1), 10000).clip(region)
        
        landcover = ee.ImageCollection("COPERNICUS/Landcover/100m/Proba-V-C3/Global") \
            .filter(ee.Filter.date('2019-01-01', '2020-01-01')) \
            .first() \
            .select('discrete_classification') \
            .clip(region)
        
        # Load road data
        roads = ee.FeatureCollection("TIGER/2016/Roads")
        roads_raster = roads.map(lambda f: f.set('constant', 1)).reduceToImage(
            properties=['constant'], reducer=ee.Reducer.first())
        distance_to_roads = roads_raster.Not().cumulativeCost(
            ee.Image.constant(1), maxDistance=500).clip(region)
        
        # Load Natura 2000 sites
        try:
            natura_2000_sites = ee.FeatureCollection('projects/ee-chmilew/assets/sic')
            natura_2000_region = natura_2000_sites.filterBounds(region)
            natura_2000_distance = natura_2000_region.distance(1000000).clip(region)
        except Exception as e:
            print(f"Could not load Natura 2000 sites: {e}")
            print("Using a placeholder for Natura 2000 distance.")
            natura_2000_distance = ee.Image.constant(threshold_natura).clip(region)
        
        # Create suitability map
        slope_suitable = slope.lte(threshold_slope).multiply(weight_slope)
        elevation_suitable = elevation.lte(threshold_elevation).multiply(weight_elevation)
        wind_suitable = wind_speed.gte(threshold_wind).multiply(weight_wind)
        roads_suitable = distance_to_roads.gte(threshold_roads).multiply(weight_roads)
        landcover_suitable = landcover.eq(40).Or(landcover.eq(30)).multiply(weight_landcover)
        natura_2000_suitable = natura_2000_distance.gte(threshold_natura).multiply(weight_natura)
        
        # Combine all factors
        suitability = slope_suitable \
            .add(elevation_suitable) \
            .add(wind_suitable) \
            .add(roads_suitable) \
            .add(landcover_suitable) \
            .add(natura_2000_suitable) \
            .rename('suitability')
        
        # Calculate maximum possible suitability score for normalization
        max_score = (weight_slope + weight_elevation + weight_wind + 
                    weight_roads + weight_landcover + weight_natura)
        
        # Normalize suitability to 0-100 scale for easier interpretation
        normalized_suitability = suitability.divide(max_score).multiply(100)
        
        # Create individual criterion maps
        _, slope_map_path = create_map(
            slope, 
            region, 
            {'min': 0, 'max': 20, 'palette': ['green', 'yellow', 'red']}, 
            'Slope (degrees)',
            output_dir=maps_output_dir
        )
        
        _, elevation_map_path = create_map(
            elevation, 
            region, 
            {'min': 0, 'max': 500, 'palette': ['green', 'yellow', 'red']}, 
            'Elevation (m)',
            output_dir=maps_output_dir
        )
        
        _, wind_speed_map_path = create_map(
            wind_speed, 
            region, 
            {'min': 0, 'max': 5, 'palette': ['blue', 'cyan', 'green', 'yellow', 'red']}, 
            'Wind Speed (ms)',
            output_dir=maps_output_dir
        )
        
        _, roads_map_path = create_map(
            distance_to_roads, 
            region, 
            {'min': 0, 'max': 1000, 'palette': ['green', 'yellow', 'red']}, 
            'Distance to Roads (m)',
            output_dir=maps_output_dir
        )
        
        _, landcover_map_path = create_map(
            landcover, 
            region, 
            {'min': 0, 'max': 200, 'palette': ['#282828', '#ffbb22', '#ffff4c', '#f096ff', 
                                              '#fa0000', '#b4b4b4', '#f0f0f0', '#0032c8', 
                                              '#0096a0', '#fae6a0', '#009900', '#000080']}, 
            'Land Cover', 
            landcover_legend=True,
            output_dir=maps_output_dir
        )
        
        _, natura_2000_map_path = create_map(
            natura_2000_distance, 
            region, 
            {'min': 0, 'max': 10000, 'palette': ['red', 'yellow', 'green']}, 
            'Distance from Natura 2000 Sites (m)',
            output_dir=maps_output_dir
        )
        
        # Create final suitability map
        _, suitability_map_path = create_map(
            normalized_suitability, 
            region, 
            {'min': 0, 'max': 100, 'palette': ['red', 'yellow', 'green']}, 
            'Wind Farm Suitability (%)',
            output_dir=maps_output_dir
        )
        
        # Get statistics for suitability
        try:
            stats = normalized_suitability.reduceRegion(
                reducer=ee.Reducer.mean().combine(ee.Reducer.minMax(), None, True),
                geometry=region,
                scale=100,
                maxPixels=1e9
            ).getInfo()
            
            mean_suitability = round(stats.get('suitability_mean', 0), 2)
            min_suitability = round(stats.get('suitability_min', 0), 2)
            max_suitability = round(stats.get('suitability_max', 0), 2)
            
            # Store statistics
            results['stats'] = {
                'mean_suitability': mean_suitability,
                'min_suitability': min_suitability,
                'max_suitability': max_suitability
            }
            
            # Update model with statistics
            params.mean_suitability = mean_suitability
            params.min_suitability = min_suitability
            params.max_suitability = max_suitability
        except Exception as e:
            print(f"Could not calculate statistics: {e}")
            results['stats'] = {'error': 'Statistics calculation failed'}
        
        # Convert paths to relative URLs for the template
        static_prefix = '/static/maps/' + str(params.id) + '/'
        
        # Update model with map paths
        params.suitability_map = static_prefix + os.path.basename(suitability_map_path)
        params.slope_map = static_prefix + os.path.basename(slope_map_path)
        params.elevation_map = static_prefix + os.path.basename(elevation_map_path)
        params.wind_speed_map = static_prefix + os.path.basename(wind_speed_map_path)
        params.roads_map = static_prefix + os.path.basename(roads_map_path)
        params.landcover_map = static_prefix + os.path.basename(landcover_map_path)
        params.natura_2000_map = static_prefix + os.path.basename(natura_2000_map_path)
        params.save()
        
        # Add URLs to results
        results['maps'] = {
            'suitability': static_prefix + os.path.basename(suitability_map_path),
            'slope': static_prefix + os.path.basename(slope_map_path),
            'elevation': static_prefix + os.path.basename(elevation_map_path),
            'wind_speed': static_prefix + os.path.basename(wind_speed_map_path),
            'roads': static_prefix + os.path.basename(roads_map_path),
            'landcover': static_prefix + os.path.basename(landcover_map_path),
            'natura_2000': static_prefix + os.path.basename(natura_2000_map_path)
        }
        
        # Success
        results['success'] = True
        
    except Exception as e:
        print(f"Error in analysis: {e}")
        results['success'] = False
        results['error_message'] = str(e)
    
    return results