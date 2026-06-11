# Extensive Test Situation

This directory (`extensive_test`) contains a comprehensive dataset designed to test the Kambatztron scheduler under a realistic and highly constrained workload scenario.

## Scenario Description

The scenario spans **3 days** (from June 1st, 2026, 08:00 to June 4th, 2026, 08:00). 
It requires managing **30 cadets**, distributed across three teams (Alpha, Bravo, Charlie) and two platoons per team. 

### Job Types & Jobs

There are 5 types of jobs and 9 distinct jobs overall:
1. **Guarding**: 
   - *Gate Guard 1*, *Gate Guard 2*: Continuous 4-hour shifts, 24/7. Difficulties scale up dramatically at night (up to 10 for 00:00-04:00).
2. **Patrol**:
   - *Perimeter Patrol*: 4-hour shifts, night only (20:00 - 08:00).
3. **Standby**:
   - *Standby Team A*, *Standby Team B*: 12-hour shifts.
4. **HQ Duty**:
   - *HQ Duty*: Daytime only (08:00 - 20:00), 4-hour shifts.
5. **Kitchen**:
   - *Kitchen Morning* (06:00-09:00), *Kitchen Lunch* (11:00-14:00), *Kitchen Dinner* (17:00-20:00).

### Cadets & Constraints

The file `cadets.csv` contains 30 cadets with a mix of constraints:
- **Unavailable Hours**: Several cadets are unavailable for multi-hour blocks (some day, some night).
- **Forbidden Jobs**: Some cadets cannot do Kitchen Duty, others cannot do Patrol, or HQ Duty.
- **Job Constraints (`job_constraints.csv`)**: 
   - No job type can overlap with another.
   - Most job types cannot be consecutive.
   - Exceptions: Standby *can* be consecutive (a cadet can do two 12-hour standby shifts back to back). HQ can be consecutive with Kitchen duty.

## Usage

You can test this scenario by running the scheduling application from the project root:

```bash
cd /Users/gur/Desktop/kambatztron
python shift_scheduler.py \
  --cadets extensive_test/cadets.csv \
  --jobs extensive_test/jobs.json \
  --constraints extensive_test/job_constraints.csv \
  --output extensive_test/test_schedule_output.xlsx
```

## Challenge

This test is designed to verify:
1. **Constraint Satisfaction**: Ensures complex multi-day unavailability blocks and forbidden jobs are respected.
2. **Performance**: Evaluates the optimization algorithm's ability to handle ~100 distinct shift instances over 3 days across 30 candidates.
3. **Fairness**: Observes how well the workload tracker distributes heavily weighted night shifts vs. easy daytime shifts.
