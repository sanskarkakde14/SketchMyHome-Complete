from locust import HttpUser, task, between, TaskSet
import random
import string

class UserBehavior(TaskSet):
    def on_start(self):
        self.register()
        self.login()

    def random_string(self, length=10):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    @task
    def register(self):
        self.username = self.random_string()
        self.password = self.random_string()
        response = self.client.post("/api/account/register/", json={
            "email": f"{self.username}@example.com",
            "name": self.random_string(),
            "tc": True,
            "phone": "1234567890",
            "location": "Sample Location",
            "password": self.password,
            "password2": self.password
        })
        print(f"register status code: {response.status_code}")
        print(f"register response: {response.json()}")
    @task
    def login(self):
        response = self.client.post("/api/account/login/", json={
            "email": f"pramod@mailinator.com",
            "password": "Sanskar123"
        })
        self.token = response.json()["token"]["access"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        print(f"login status code: {response.status_code}")
        print(f"login response: {response.json()}")

    @task
    def profile(self):
        response = self.client.get("/api/account/profile/", headers=self.headers)
        print(f"profile status code: {response.status_code}")

    @task
    def change_password(self):
        new_password = self.random_string()
        response = self.client.post("/api/account/changepassword/", json={
            "old_password": self.password,
            "new_password": new_password,
            "new_password2": new_password
        }, headers=self.headers)
        print(f"change_password status code: {response.status_code}")

    @task
    def create_project(self):
        response = self.client.post("/api/dummy/create-project/", json={
            "project_name": self.random_string(),
            "width": 100,
            "length": 200,
            "bedroom": 3,
            "bathroom": 2,
            "car": 1,
            "temple": 1,
            "garden": 1,
            "living_room": 1,
            "store_room": 1
        }, headers=self.headers)
        print(f"create_project status code: {response.status_code}")

    @task
    def pdf_list(self):
        response = self.client.get("/api/dummy/pdf-list/", headers=self.headers)
        print(f"pdf_list status code: {response.status_code}")

    @task
    def generate_map_soil_data(self):
        response = self.client.post("/api/dummy/generate-map-soil-data/", json={
            "latitude": 40.7128,
            "longitude": -74.0060
        }, headers=self.headers)
        print(f"generate_map_soil_data status code: {response.status_code}")

    @task
    def map_files_list(self):
        response = self.client.get("/api/dummy/map-files-list/", headers=self.headers)
        print(f"map_files_list status code: {response.status_code}")

class DjangoUser(HttpUser):
    tasks = [UserBehavior]
    wait_time = between(1, 2)  # Time in seconds between tasks
    host = "http://127.0.0.1:8000"  # Set your base host URL here

# To run the test, save this as locustfile.py and run:
# locust -f locustfile.py --host=http://localhost:8000
