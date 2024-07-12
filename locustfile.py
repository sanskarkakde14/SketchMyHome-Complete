from locust import HttpUser, task

class SMH(HttpUser):
    @task
    def smh_initial(self):
        self.client.post("/api/account/login", json={"username":"pramod@mailinator.com", "password":"Sanskar123"})
        self.client.get("/world")