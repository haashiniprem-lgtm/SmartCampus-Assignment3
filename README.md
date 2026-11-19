# Smart Campus Facility and Maintenance Platform

Flask + PostgreSQL prototype for CSA10 Assignment 3.

## Run
`docker compose up -d --build`

Open:
- http://localhost:5051
- http://localhost:5052

Check: `docker compose ps`
Stop: `docker compose down`

Both backend instances share PostgreSQL and its persistent named volume.

## Demo checks
1. Create a booking. Submit the same facility/time overlap again: expected HTTP 409.
2. Create a ticket using event ID SENSOR-100, then submit SENSOR-100 again: duplicate is ignored.
3. Book as Student; approval must be denied unless role is Department Approver or Administrator.
4. Restart one backend: `docker compose restart web1`. Check the booking/ticket remains.
5. Open /health on ports 5051 and 5052 to see the responding instance.

Triage uses deterministic keyword rules, not a trained AI model. Use synthetic data only. No measured 300-user capacity is claimed.
