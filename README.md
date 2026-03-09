## we have the similarities saved in the assets folder for bothe recommenders 
#### => similarity_bow.pkl
#### => similarity_emb.pkl

## locutc test 
locust -f tests/locustfile.py --host http://localhost:8000 --users 200 --spawn-rate 20 --run-time 5m --headless --csv results

