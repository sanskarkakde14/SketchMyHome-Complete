from django.urls import path
from .views import *

urlpatterns = [
    path('create-project/', CreateProjectView.as_view(), name='create-project'),
    path('pdf-list/', PDFListView.as_view(), name='pdf-list'),
    path('pdf/<str:filename>', PDFServeView.as_view(), name='pdf-serve'),

]





