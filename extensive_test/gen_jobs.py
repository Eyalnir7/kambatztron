import json
from datetime import datetime, timedelta

def format_ts(dt1, dt2):
    return f"{dt1.strftime('%Y-%m-%d %H:%M')}-{dt2.strftime('%Y-%m-%d %H:%M')}"

start_date = datetime(2026, 6, 1, 8, 0)
days = 3

jobs = {}

def add_job(name, job_type, shifts, diff_func):
    if name not in jobs:
        jobs[name] = {"job_type": job_type, "difficulty_by_time_slot": {}}
    for dt1, dt2 in shifts:
        jobs[name]["difficulty_by_time_slot"][format_ts(dt1, dt2)] = diff_func(dt1)

# Generate shifts
guard_shifts = []
for i in range(days * 6):
    dt1 = start_date + timedelta(hours=i * 4)
    dt2 = dt1 + timedelta(hours=4)
    guard_shifts.append((dt1, dt2))

patrol_shifts = []
for d in range(days):
    base = start_date + timedelta(days=d)
    patrol_shifts.append((base + timedelta(hours=12), base + timedelta(hours=16))) # 20:00-00:00
    patrol_shifts.append((base + timedelta(hours=16), base + timedelta(hours=20))) # 00:00-04:00
    patrol_shifts.append((base + timedelta(hours=20), base + timedelta(hours=24))) # 04:00-08:00

standby_shifts = []
for d in range(days):
    base = start_date + timedelta(days=d)
    standby_shifts.append((base, base + timedelta(hours=12)))
    standby_shifts.append((base + timedelta(hours=12), base + timedelta(hours=24)))

hq_shifts = []
for d in range(days):
    base = start_date + timedelta(days=d)
    hq_shifts.append((base, base + timedelta(hours=4))) # 08-12
    hq_shifts.append((base + timedelta(hours=4), base + timedelta(hours=8))) # 12-16
    hq_shifts.append((base + timedelta(hours=8), base + timedelta(hours=12))) # 16-20

kitchen_morning = []
kitchen_lunch = []
kitchen_dinner = []
for d in range(days):
    base = start_date + timedelta(days=d)
    kitchen_morning.append((base - timedelta(hours=2), base + timedelta(hours=1))) # 06:00-09:00
    kitchen_lunch.append((base + timedelta(hours=3), base + timedelta(hours=6))) # 11:00-14:00
    kitchen_dinner.append((base + timedelta(hours=9), base + timedelta(hours=12))) # 17:00-20:00

def guard_diff(dt):
    h = dt.hour
    if h == 8 or h == 16: return 4
    if h == 12: return 5
    if h == 20: return 8
    if h == 0: return 10
    if h == 4: return 9
    return 5

def patrol_diff(dt):
    h = dt.hour
    if h == 20: return 7
    if h == 0: return 9
    if h == 4: return 8
    return 6

def standby_diff(dt):
    h = dt.hour
    if h == 8: return 6
    if h == 20: return 8
    return 6

def hq_diff(dt):
    return 3

def kitchen_diff(dt):
    return 4

add_job("Gate Guard 1", "guarding", guard_shifts, guard_diff)
add_job("Gate Guard 2", "guarding", guard_shifts, guard_diff)
add_job("Perimeter Patrol", "patrol", patrol_shifts, patrol_diff)
add_job("Standby Team A", "standby", standby_shifts, standby_diff)
add_job("Standby Team B", "standby", standby_shifts, standby_diff)
add_job("HQ Duty", "hq", hq_shifts, hq_diff)
add_job("Kitchen Morning", "kitchen", kitchen_morning, kitchen_diff)
add_job("Kitchen Lunch", "kitchen", kitchen_lunch, kitchen_diff)
add_job("Kitchen Dinner", "kitchen", kitchen_dinner, kitchen_diff)

with open("/Users/gur/Desktop/kambatztron/extensive_test/jobs.json", "w") as f:
    json.dump(jobs, f, indent=2)

print("jobs.json generated.")
