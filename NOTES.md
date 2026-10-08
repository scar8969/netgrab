== curl ==
# POST /api/tasks  {"urls":["https://…"],"parallel":4}
# GET  /api/tasks
# POST /api/tasks/1/pause | /resume
# CLI: ctfile-dl dl links.txt --out ./downloads --parallel 4

== session plan ==
# Session 1: extract + worker (single download vs local ranged server) → tests
# Session 2: resume + parallel + speed limit → tests
# Session 3: web progress + cli → screenshots → README → CI/Docker/Pages → tag
