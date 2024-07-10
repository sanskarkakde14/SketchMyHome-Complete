from django.urls import path
from .views import *


urlpatterns = [
    path('create-project/', CreateProjectView.as_view(), name='create-project'),
    path('user-projects/', UserProjectsView.as_view(), name='user-projects'),
    path('projects/<int:project_id>/', ProjectDetailView.as_view(), name='project-detail'),
    path('generate-map-soil-data/', GenerateMapAndSoilDataView.as_view(), name='generate-map-soil-data'),
    path('map-files-list/', MapFileListView.as_view(), name='map-file-list'),

]



