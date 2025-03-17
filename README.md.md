# Wind Farm Suitability Analysis Tool

A Django web application that analyzes potential wind farm locations based on GPS coordinates. The tool evaluates multiple geographic factors to determine site suitability.

## Features

- Input GPS coordinates through a user-friendly interface
- Analysis of key geographical factors that affect wind farm placement:
  - Wind Speed (m/s)
  - Elevation (m)
  - Slope (degrees)
  - Land Cover classification
  - Distance to Roads (m)
  - Distance from Natura 2000 Sites (m)
- Generation of interactive maps for each factor
- Calculation of overall wind farm suitability (percentage)
- Visualization of results through interactive HTML maps

## Technology Stack

- **Backend**: Django (Python)
- **Database**: SQLite
- **GIS Processing**: Google Earth Engine (via `gee_utils.py`)
- **Map Visualization**: Leaflet.js/Folium

## Setup and Installation

### Prerequisites

- Python 3.8+
- Django 3.0+
- Google Earth Engine account (for spatial data access)

### Installation

1. Clone this repository
```bash
git clone https://github.com/yourusername/windfarm-suitability.git
cd windfarm-suitability
```

2. Create and activate a virtual environment
```bash
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Apply migrations
```bash
python manage.py migrate
```

5. Run the development server
```bash
python manage.py runserver
```

6. Open your browser and navigate to http://127.0.0.1:8000/

## Usage

1. Enter the latitude and longitude coordinates for your area of interest
2. Submit the form and wait for the analysis to complete
3. Explore the generated maps for each geographical factor
4. View the overall suitability map to assess the location's viability for wind farm development

## Project Structure

```
windfarm_project/        # Main Django project folder
├── analysis/            # Main application
│   ├── migrations/      # Database migrations
│   ├── templates/       # HTML templates
│   ├── admin.py         # Admin configuration
│   ├── forms.py         # Form definitions
│   ├── gee_utils.py     # Google Earth Engine utilities
│   ├── models.py        # Database models
│   ├── views.py         # View functions
│   └── urls.py          # URL routing
├── static/              # Static files
│   ├── maps/            # Generated map files
│   └── preview_maps/    # Preview map templates
├── staticfiles/         # Collected static files
└── manage.py            # Django management script
```

## License

[Specify your license here]

## Acknowledgements

- [List any data sources, libraries, or other resources you used]