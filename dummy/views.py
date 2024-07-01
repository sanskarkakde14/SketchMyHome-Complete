from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView
from rest_framework.views import APIView
from django.conf import settings
from subprocess import run, PIPE
from django.http import HttpResponse
from pathlib import Path
import json, os
from rest_framework.permissions import IsAuthenticated
from django.core.files import File
from urllib.parse import urljoin
from .serializers import *
import time
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

        print(f"Script path: {script_path}")
        print(f"Data folder: {data_folder}")
        print(f"JSON data: {json_data}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Files in data folder: {os.listdir(data_folder)}")

        result = run(
            ['python', str(script_path), json_data], 
            stdout=PIPE, stderr=PIPE, text=True, cwd=settings.BASE_DIR / 'dummy'
        )

        print(f"Script stdout: {result.stdout}")
        print(f"Script stderr: {result.stderr}")

        if result.returncode == 0:
            output_data = result.stdout.strip()
            png_filepaths = self.extract_png_filepaths(output_data)
            if png_filepaths:
                try:
                    self.move_pngs_to_media(png_filepaths, user)
                    return Response({
                        'message': 'External script executed successfully and PNGs moved',
                        'output': result.stdout
                    })
                except FileNotFoundError as e:
                    return Response({
                        'message': 'Error moving PNG files',
                        'error': str(e),
                        'filepaths': png_filepaths
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                return Response({
                    'message': 'External script executed successfully but no PNG filenames returned',
                    'output': result.stdout
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({
                'message': 'Error running external script',
                'error': result.stderr
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def extract_png_filepaths(self, output_data):
        try:
            start = output_data.index('[')
            end = output_data.index(']') + 1
            filepaths = json.loads(output_data[start:end].replace("'", '"'))
            print("Extracted filepaths:", filepaths)
            return filepaths
        except (ValueError, IndexError, json.JSONDecodeError) as e:
            print(f"Error extracting file paths: {e}")
            print(f"Output data: {output_data}")
            return []

    def move_pngs_to_media(self, dxf_filepaths, user):
        moved_images = []
        png_folder = os.path.join(settings.BASE_DIR, 'dummy', 'png')  # Adjust this path as needed
        
        print(f"PNG folder: {png_folder}")
        print(f"Files in PNG folder: {os.listdir(png_folder)}")

        for dxf_filepath in dxf_filepaths:
            retry_count = 5
            delay = 2  # seconds

            # Convert DXF filename to PNG
            png_filename = os.path.splitext(os.path.basename(dxf_filepath))[0] + '.png'
            source_path = os.path.join(png_folder, png_filename)

            print(f"Looking for PNG file: {source_path}")

            for attempt in range(retry_count):
                if os.path.exists(source_path):
                    destination_path = os.path.join(settings.MEDIA_ROOT, 'pngs', png_filename)
                    os.makedirs(os.path.dirname(destination_path), exist_ok=True)

                    try:
                        with open(source_path, 'rb') as f:
                            django_file = File(f)
                            user_png = UserPNG(user=user)
                            user_png.image.save(png_filename, django_file, save=True)
                        
                        moved_images.append(png_filename)
                        print(f"Successfully moved: {png_filename}")
                        break
                    except Exception as e:
                        print(f"Error saving PNG {png_filename}: {str(e)}")
                else:
                    print(f"File not found: {source_path}. Retry {attempt + 1}/{retry_count}")
                    time.sleep(delay)
            else:
                raise FileNotFoundError(f"PNG not found after retries: {source_path}")
        
        return moved_images         








class PDFListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_pdfs = UserPNG.objects.all()
        serializer = PDFSerializer(user_pdfs, many=True)
        return Response(serializer.data)

class PDFServeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, filename):
        pdf_folder = os.path.join(settings.MEDIA_ROOT, 'pdfs')
        file_path = os.path.join(pdf_folder, filename)

        # Debug: Print the file path
        print(f"Looking for file at: {file_path}")

        if os.path.exists(file_path):
            print(f"File found: {file_path}")  # Debug: Confirm file exists
            with open(file_path, 'rb') as pdf_file:
                response = HttpResponse(pdf_file.read(), content_type='image/png')
                response['Content-Disposition'] = f'inline; filename="{filename}"'
                return response
        else:
            print(f"File not found: {file_path}")  # Debug: Log file not found
            return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)