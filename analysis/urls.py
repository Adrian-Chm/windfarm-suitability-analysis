# File: analysis/urls.py
from django.urls import path
from . import views

app_name = 'analysis'

urlpatterns = [
    path('', views.index, name='index'),
    path('results/<uuid:analysis_id>/', views.results, name='results'),
    path('preview/', views.preview_area, name='preview'),
    path('export/<uuid:analysis_id>/', views.export_analysis, name='export'),
    path('test-static/', views.test_static_file, name='test_static'),
    path('simple-preview/', views.simple_preview, name='simple_preview'),

]