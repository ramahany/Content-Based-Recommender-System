from locust import HttpUser, task, between

class FastAPIUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def endpoint1(self):
        self.client.get("/api/v1/listmovies")

    @task
    def endpoint2(self):
        self.client.post(
            "/api/v1/recommend/Tangled",
        )