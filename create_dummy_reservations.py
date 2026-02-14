from datetime import datetime, timedelta
from gpu_data import add_reservation, init_db
import random

init_db()

users = ["Alice", "Bob", "Charlie", "David"]
projects = ["LLM Training", "Computer Vision", "Simulation", "Testing"]

# Make reservations for today and tomorrow
today = datetime.now().date()
times = [
    (9, 12), (13, 15), (15, 18), (10, 14)
]

# 4090s
for i in range(1, 4): # 4090-01, 02, 03
    gpu_id = f"4090-0{i}"
    start_hour, end_hour = random.choice(times)
    start = datetime.combine(today, datetime.min.time()) + timedelta(hours=start_hour)
    end = datetime.combine(today, datetime.min.time()) + timedelta(hours=end_hour)
    
    user = random.choice(users)
    proj = random.choice(projects)
    
    add_reservation(user, gpu_id, start, end, proj)
    print(f"Added reservation: {user} on {gpu_id} ({start.time()} - {end.time()})")

# H100s
for i in range(1, 3):
    gpu_id = f"H100-0{i}"
    start_hour, end_hour = random.choice(times)
    start = datetime.combine(today + timedelta(days=1), datetime.min.time()) + timedelta(hours=start_hour)
    end = datetime.combine(today + timedelta(days=1), datetime.min.time()) + timedelta(hours=end_hour)
    
    user = random.choice(users)
    proj = random.choice(projects)
    
    add_reservation(user, gpu_id, start, end, proj)
    print(f"Added reservation: {user} on {gpu_id} ({start.time()} - {end.time()})")
