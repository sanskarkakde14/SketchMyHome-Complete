from rest_framework import status,generics
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView,ListAPIView,RetrieveAPIView
from rest_framework.views import APIView
from django.db.models import Max
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings
from django.core.files.base import ContentFile
from subprocess import run, PIPE
import json, os, uuid
from django.db.models import F
from rest_framework.permissions import IsAuthenticated
from .serializers import *
import pandas as pd
from helper.SiteAnalyzer import main, soil_type
from helper.uuidGenerator import generate_short_uuid
from drf_yasg.utils import swagger_auto_schema


class CreateProjectView(generics.CreateAPIView):
    serializer_class = ProjectSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=ProjectSerializer)
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        return self.run_external_script(serializer.validated_data, request.user)
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    def run_external_script(self, data, user):
        script_path = os.path.join(settings.BASE_DIR, 'dummy', 'PrototypeScript.py')
        if not os.path.exists(script_path):
            return self.error_response('Script path does not exist')
        result = run(['python', script_path, json.dumps(data)], 
                     stdout=PIPE, stderr=PIPE, text=True, cwd=os.path.join(settings.BASE_DIR, 'dummy'))
        if result.returncode != 0:
            return self.error_response('External script execution failed', result.stderr)

        return self.process_output(result.stdout.strip(), user, data)

    def process_output(self, output, user, project_data):
        files_info = []
        avg_values = []
        area_infos = []
        for line in output.split('\n'):
            if line.startswith("Hello"):
                files_info.append(line.split("Hello", 1)[1].strip())
            elif "AVG:" in line:
                try:
                    avg_values.append(float(line.split("AVG:", 1)[1].strip()))
                except (IndexError, ValueError):
                    pass
            elif line.startswith("AREA:"):
                try:
                    area_infos.append(json.loads(line.split("AREA:", 1)[1].strip()))
                except (IndexError, json.JSONDecodeError):
                    pass
        if not files_info or not avg_values:
            return self.error_response('No filenames or AVG values returned', output)
        try:
            project = Project.objects.create(
                user=user,
                project_name=project_data['project_name'],
                width=project_data['width'],
                length=project_data['length'],
                bedroom=project_data['bedroom'],
                bathroom=project_data['bathroom'],
                car=project_data['car'],
                temple=project_data['temple'],
                garden=project_data['garden'],
                living_room=project_data['living_room'],
                store_room=project_data['store_room']
            )
            moved_files = self.process_files(files_info, user, project, avg_values, area_infos)
            return self.construct_response(project)
        except FileNotFoundError as e:
            return self.error_response('Error moving files', str(e))

    def process_files(self, files_info, user, project, avg_values, area_infos):
        moved_files = []
        file_pairs = {}
        for filepath in files_info:
            filename = os.path.basename(filepath)
            name_without_ext = os.path.splitext(filename)[0]
            if filename.lower().endswith('.png'):
                if name_without_ext not in file_pairs:
                    file_pairs[name_without_ext] = {'png': filename}
                else:
                    file_pairs[name_without_ext]['png'] = filename
            elif filename.lower().endswith(('.dxf', '.dxftrimmed')):
                if name_without_ext not in file_pairs:
                    file_pairs[name_without_ext] = {'dxf': filename}
                else:
                    file_pairs[name_without_ext]['dxf'] = filename
        for i, (name, files) in enumerate(file_pairs.items()):
            avg_value = avg_values[i] if i < len(avg_values) else None
            area_info = area_infos[i] if i < len(area_infos) else None
            user_file = UserFile(
                user=user,
                project=project,
                avg_value=avg_value,
                area_info=area_info
            )
            png_saved, png_filename = self.save_file(files.get('png'), user_file, 'png_image', subfolder='png')
            dxf_saved, dxf_filename = self.save_file(files.get('dxf'), user_file, 'dxf_file')
            if png_saved or dxf_saved:
                user_file.save()
                moved_files.append({
                    "id": user_file.id,
                    "png_name": png_filename,
                    "dxf_name": dxf_filename,
                    "png_img": user_file.png_image.url if png_saved else None,
                    "dxf_file": user_file.dxf_file.url if dxf_saved else None,
                    "avg_value": user_file.avg_value,
                    "area_info": user_file.area_info,
                    "created_at": user_file.created_at
                })
        return moved_files

    def save_file(self, filename, user_file, file_type, subfolder=''):
        if not filename:
            return False, None
        source_path = os.path.join(settings.BASE_DIR, 'dummy', 'dxf', subfolder, filename)
        if not os.path.exists(source_path):
            print(f"File not found: {source_path}")
            return False, None
        try:
            with open(source_path, 'rb') as f:
                file_content = f.read()

            short_id = generate_short_uuid()
            name, ext = os.path.splitext(filename)
            unique_filename = f"{name}_{short_id}{ext}"
            django_file = ContentFile(file_content, name=unique_filename)
            getattr(user_file, file_type).save(unique_filename, django_file, save=False)
            print(f"Successfully saved {file_type}: {unique_filename}")
            return True, unique_filename
        except Exception as e:
            print(f"Error saving {file_type} {filename}: {str(e)}")
            return False, None

    def error_response(self, message, details=None):
        response = {'message': message}
        if details:
            response['details'] = details
        return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def construct_response(self, project):
        response_data = {
            "id": project.id,
            "project_name": project.project_name,
            "width": project.width,
            "length": project.length,
            "bedroom": project.bedroom,
            "bathroom": project.bathroom,
            "car": project.car,
            "temple": project.temple,
            "garden": project.garden,
            "living_room": project.living_room,
            "store_room": project.store_room,
            "created_at": project.created_at,
            "files": [
                {
                    "id": user_file.id,
                    "png_name": os.path.basename(user_file.png_image.name) if user_file.png_image else None,
                    "dxf_name": os.path.basename(user_file.dxf_file.name) if user_file.dxf_file else None,
                    "png_img": user_file.png_image.url if user_file.png_image else None,
                    "dxf_file": user_file.dxf_file.url if user_file.dxf_file else None,
                    "avg_value": user_file.avg_value,
                    "area_info": user_file.area_info,
                    "created_at": user_file.created_at
                } for user_file in project.files.all()
            ]
        }
        return Response(response_data, status=status.HTTP_201_CREATED)
            

class UserProjectsView(ListAPIView):
    serializer_class = ProjectSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user).order_by('-created_at')

class ProjectDetailView(RetrieveAPIView):
    serializer_class = ProjectDetailSerializer
    queryset = Project.objects.all()
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'project_id'  # Adjust this to match your URL configuration

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)
    
#SiteMap Analysis Code
class GenerateMapAndSoilDataView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(request_body=MapFileSerializer)
    def post(self, request, *args, **kwargs):
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        if not latitude or not longitude:
            return Response({'error': 'Latitude and longitude are required.'}, status=status.HTTP_400_BAD_REQUEST)
        # Generate a unique filename
        unique_filename = f'map_{uuid.uuid4().hex}.html'
        latitude = float(latitude)
        longitude = float(longitude)
        # Run the external script to generate the map and get soil data
        map_file_rel_path = main(unique_filename, latitude, longitude)
        if not map_file_rel_path:
            return Response({'error': 'Failed to generate map.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # Save the map HTML file path in the database
        map_file = MapFile.objects.create(user=request.user, map_html=map_file_rel_path)
        map_file_serializer = MapFileSerializer(map_file)
        base_dir = settings.BASE_DIR / 'assets'
        excel_path = base_dir / 'soil_type.xlsx'    
        # Fetch and save the soil data
        soil_data = soil_type(pd.read_excel(excel_path), latitude, longitude).iloc[0]
        soil_data_instance = SoilData.objects.create(
            user=request.user,
            soil_type=soil_data['Soil Type'],
            ground_water_depth=soil_data['Ground Water Depth'],
            foundation_type=soil_data['Foundation Type']
        )
        soil_data_serializer = SoilDataSerializer(soil_data_instance)
        # Return the serialized data
        return Response({
            'map_file': map_file_serializer.data,
            'soil_data': soil_data_serializer.data
        }, status=status.HTTP_201_CREATED)
    

class MapFileListView(generics.ListAPIView):
    authentication_classes = [JWTAuthentication]
    serializer_class = MapFileSerializer
    # permission_classes = [IsAuthenticated]
    @swagger_auto_schema(request_body=MapFileSerializer)
    def get_queryset(self):
        user = self.request.user  # Assuming user is authenticated
        return MapFile.objects.filter(user=user).order_by('-created_at')
    



