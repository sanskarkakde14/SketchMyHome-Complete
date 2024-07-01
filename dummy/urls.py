from django.urls import path
from .views import *


urlpatterns = [
    path('create-project/', CreateProjectView.as_view(), name='create-project'),
    path('pdf-list/', PDFListView.as_view(), name='pdf-list'),
    path('pdf/<str:filename>', PDFServeView.as_view(), name='pdf-serve'),
    path('generate-map-soil-data/', GenerateMapAndSoilDataView.as_view(), name='generate-map-soil-data'),
    path('map-files-list/', MapFileListView.as_view(), name='map-file-list'),

]





