from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView
from rest_framework import generics
from rest_framework.views import APIView
from django.conf import settings
from django.core.files.base import ContentFile
from subprocess import run, PIPE
from django.http import HttpResponse,FileResponse
from pathlib import Path
import json, os
from rest_framework.permissions import IsAuthenticated
from django.core.files import File
from urllib.parse import urljoin
from .serializers import *
import time, uuid
import pandas as pd
from helper.SiteAnalyzer import main, soil_type

class CreateProjectView(CreateAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            user = request.user
            return self.run_external_script(serializer.validated_data, user)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def run_external_script(self, data, user):
        script_path = settings.BASE_DIR / 'dummy' / 'PrototypeScript.py'
        data_folder = settings.BASE_DIR / 'dummy' / 'SMH_PROTOTYPE_FILE'

        if not script_path.exists():
            return Response({'message': 'Error: Script path does not exist'}, 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        json_data = json.dumps(data)

        result = run(
            ['python', str(script_path), json_data], 
            stdout=PIPE, stderr=PIPE, text=True, cwd=settings.BASE_DIR / 'dummy'
        )

        if result.returncode == 0:
            output_data = result.stdout.strip()
            filepaths = self.extract_filepaths(output_data)
            avg_values = self.extract_avg_value(output_data)
            area_info = self.extract_area_info(output_data)
            if filepaths and avg_values:
                try:
                    moved_files = self.move_files_to_media(filepaths, user, avg_values, area_info)
                    return Response({
                        'message': 'External script executed successfully and files moved',
                        'moved_files': moved_files,
                        'output': result.stdout,
                        'avg_values': avg_values,
                        'area_info': area_info
                    })
                except FileNotFoundError as e:
                    return Response({
                        'message': 'Error moving files',
                        'error': str(e),
                        'filepaths': filepaths,
                        'avg_values': avg_values,
                        'area_info': area_info
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                return Response({
                    'message': 'External script executed successfully but no filenames or AVG values returned',
                    'output': result.stdout,
                    'filepaths': filepaths,
                    'avg_values': avg_values,
                    'area_info': area_info
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Fallback response if none of the above conditions are met
        return Response({
            'message': 'External script execution failed',
            'output': result.stdout,
            'error': result.stderr
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def extract_filepaths(self, output_data):
        try:
            lines = output_data.split('\n')
            filepaths = []
            for line in lines:

                if line.startswith("Hello"):
                    filepath = line.split("Hello", 1)[1].strip()
                    filepaths.append(filepath)
            print("Extracted filepaths:", filepaths)
            return filepaths
        except Exception as e:
            print(f"Error extracting file paths: {e}")
            print(f"Output data: {output_data}")
            return []

    def move_files_to_media(self, filepaths, user, avg_values, area_info):
        moved_files = []
        file_pairs = {}

        for filepath in filepaths:
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
            try:
                avg_value = avg_values[i] if i < len(avg_values) else None
                user_file = UserFile(user=user, avg_value=avg_value, area_info=area_info)
                print(f"Saving file pair with AVG value: {avg_value} and Area info: {area_info}")
                if 'png' in files:
                    self.save_png_file(files['png'], user_file)
                if 'dxf' in files:
                    self.save_dxf_file(files['dxf'], user_file)
                user_file.save()
                moved_files.extend([files.get('png', ''), files.get('dxf', '')])
            except FileNotFoundError as e:
                print(f"Error moving files for {name}: {str(e)}")
        
        return moved_files

    def save_png_file(self, filename, user_file):
        source_path = os.path.join(settings.BASE_DIR, 'dummy', 'dxf', 'png', filename)
        print(f"Looking for PNG file: {source_path}")

        if os.path.exists(source_path):
            try:
                with open(source_path, 'rb') as f:
                    file_content = f.read()
                django_file = ContentFile(file_content, name=filename)
                user_file.png_image.save(filename, django_file, save=False)
                print(f"Successfully added PNG: {filename}")
            except Exception as e:
                print(f"Error saving PNG {filename}: {str(e)}")
        else:
            raise FileNotFoundError(f"PNG not found: {source_path}")

    def save_dxf_file(self, filename, user_file):
        source_path = os.path.join(settings.BASE_DIR, 'dummy', 'dxf', filename)
        print(f"Looking for DXF file: {source_path}")

        if os.path.exists(source_path):
            try:
                with open(source_path, 'rb') as f:
                    file_content = f.read()
                django_file = ContentFile(file_content, name=filename)
                user_file.dxf_file.save(filename, django_file, save=False)
                print(f"Successfully added DXF: {filename}")
            except Exception as e:
                print(f"Error saving DXF {filename}: {str(e)}")
        else:
            raise FileNotFoundError(f"DXF file not found: {source_path}")
    def extract_avg_value(self, output_data):
        print(f"Full output data: {output_data}")
        avg_values = []
        for line in output_data.split('\n'):
            if "AVG:" in line:
                print(f"Found AVG line: {line}")
                try:
                    avg_str = line.split("AVG:", 1)[1].strip()
                    avg_value = float(avg_str)
                    print(f"Extracted AVG value: {avg_value}")
                    avg_values.append(avg_value)
                except (IndexError, ValueError) as e:
                    print(f"Error parsing AVG value from line: {line}. Error: {e}")
        if not avg_values:
            print("No valid AVG values found")
            return None
        print(f"All extracted AVG values: {avg_values}")
        return avg_values
    
    def extract_area_info(self, output_data):
        area_info = {}
        for line in output_data.split('\n'):
            if line.startswith("AREA:"):
                try:
                    area_json = line.split("AREA:", 1)[1].strip()
                    area_info = json.loads(area_json)
                    print(f"Extracted area info: {area_info}")
                except (IndexError, json.JSONDecodeError) as e:
                    print(f"Error parsing area info from line: {line}. Error: {e}")
        return area_info
            
class UserFileListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_pdfs = UserFile.objects.filter(user=request.user)
        serializer = UserFileSerializer(user_pdfs, many=True)
        return Response(serializer.data)



#SiteMap Analysis Code
class GenerateMapAndSoilDataView(APIView):
    permission_classes = [IsAuthenticated]

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
    serializer_class = MapFileSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        user = self.request.user  # Assuming user is authenticated
        return MapFile.objects.filter(user=user).order_by('-created_at')
    

