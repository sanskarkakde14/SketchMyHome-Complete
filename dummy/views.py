from rest_framework import status,generics
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings
from django.core.files.base import ContentFile
from subprocess import run, PIPE
import json, os, uuid,ast,logging, shutil
from rest_framework.permissions import IsAuthenticated
from .serializers import *
import pandas as pd
from helper.SiteAnalyzer import main, soil_type
from helper.uuidGenerator import generate_short_uuid
from drf_yasg.utils import swagger_auto_schema
logger = logging.getLogger(__name__)

class CreateProjectView(CreateAPIView):
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

    def run_external_script(self, data, user):
        script_path = os.path.join(settings.BASE_DIR, 'dummy', 'PrototypeScript.py')
        if not os.path.exists(script_path):
            return self.error_response('Script path does not exist')
        result = run(['python', script_path, json.dumps(data)], 
                     stdout=PIPE, stderr=PIPE, text=True, cwd=os.path.join(settings.BASE_DIR, 'dummy'))
        if result.returncode != 0:
            return self.error_response('External script execution failed', result.stderr)

        return self.process_output(result.stdout.strip(), user)

    def process_output(self, output, user):
        info_data_list = []
        for line in output.split('\n'):
            if line.startswith("INFO:"):
                try:
                    dict_str = line.split("INFO:", 1)[1].strip()
                    logger.debug(f"Attempting to parse dict: {dict_str}")
                    info_data = ast.literal_eval(dict_str)
                    info_data_list.append(info_data)
                    logger.debug(f"Successfully parsed INFO: {info_data}")
                except (IndexError, ValueError, SyntaxError) as e:
                    logger.error(f"Error when parsing INFO line: {line}. Error: {str(e)}")
        
        if not info_data_list:
            return self.error_response('No valid INFO data returned', output)
        
        try:
            all_processed_files = []
            for info_data in info_data_list:
                processed_files = self.process_files(info_data, user)
                all_processed_files.extend(processed_files)
            
            return Response({
                'message': 'External script executed successfully and files processed',
                'processed_files': all_processed_files,
                'info_data': info_data_list,
            })
        except FileNotFoundError as e:
            return self.error_response('Error processing files', str(e))

    def process_files(self, info_data, user):
        processed_files = []
        for png_filename, floor_data in info_data.items():
            user_file = UserFile(
                user=user,
                info=floor_data
            )
            
            png_saved, png_name = self.save_file(png_filename, user_file, 'png_image', subfolder='png')
            
            dxf_filename = png_filename.replace('.png', '.dxf')
            dxf_saved, dxf_name = self.save_file(dxf_filename, user_file, 'dxf_file')
            
            floor_files_saved = []
            floor_file_keys = list(floor_data.keys())  # Make a copy of the keys to avoid modification during iteration
            for floor_file in floor_file_keys:
                floor_saved, floor_name = self.save_file(floor_file, user_file, 'floor_file', subfolder='png')
                if floor_saved:
                    floor_files_saved.append(floor_name)
            
            if png_saved or dxf_saved or floor_files_saved:
                user_file.save()
                logger.info(f"Saved UserFile: id={user_file.id}, png={png_name}, dxf={dxf_name}, info={user_file.info}")
                processed_files.append({
                    'png': png_name,
                    'dxf': dxf_name,
                    'floors': floor_files_saved
                })
            else:
                logger.warning(f"Failed to save files for {png_filename}")

        return processed_files



    def save_file(self, filename, user_file, file_type, subfolder=''):
        if not filename:
            return False, None
        
        # Define source path
        source_path = os.path.join(settings.BASE_DIR, 'dummy', 'dxf', subfolder, filename)
        
        # Determine the target subfolder based on file type
        if file_type == 'png_image' or file_type == 'floor_file':
            target_subfolder = 'pngs/'
        else:
            target_subfolder = 'dxfs/'
            
        # Define target path
        target_path = os.path.join(settings.MEDIA_ROOT, target_subfolder, filename)
        
        # Check if source file exists
        if not os.path.exists(source_path):
            logger.warning(f"File not found: {source_path}")
            return False, None

        try:
            # Ensure target directory exists
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # Move file to target location
            shutil.move(source_path, target_path)
            
            # Generate a short unique ID
            short_id = generate_short_uuid()
            
            # Split the filename and extension
            name, ext = os.path.splitext(filename)
            
            # Create a unique filename with the short ID
            unique_filename = f"{name}_{short_id}{ext}"
            
            # Rename the moved file with the unique filename
            final_target_path = os.path.join(settings.MEDIA_ROOT, target_subfolder, unique_filename)
            os.rename(target_path, final_target_path)
            
            with open(final_target_path, 'rb') as f:
                file_content = f.read()
            
            django_file = ContentFile(file_content, name=unique_filename)
            
            if file_type == 'floor_file':
                floor_file_path = f"{target_subfolder}{unique_filename}"
                if user_file.info is None:
                    user_file.info = {}
                user_file.info[floor_file_path] = user_file.info.pop(filename, {})
                user_file.save(update_fields=['info'])
                logger.info(f"Successfully saved {file_type}: {unique_filename}")
                return True, unique_filename
            else:
                getattr(user_file, file_type).save(unique_filename, django_file, save=False)
                logger.info(f"Successfully saved {file_type}: {unique_filename}")
                return True, unique_filename
        except Exception as e:
            logger.error(f"Error saving {file_type} {filename}: {str(e)}")
            return False, None



    def error_response(self, message, details=None):
        response = {'message': message}
        if details:
            response['details'] = details
        return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
class UserFileListView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    # @swagger_auto_schema(request_body=UserFileSerializer)
    def get(self, request):
        user_pdfs = UserFile.objects.filter(user=request.user)
        serializer = UserFileSerializer(user_pdfs, many=True)
        return Response(serializer.data)


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
