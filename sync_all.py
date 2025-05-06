# create a file called sync_all.py
import os
import subprocess

# Range of tournament IDs to sync
start_id = 252
end_id = 300  # Adjust as needed

for tournament_id in range(start_id, end_id + 1):
    print(f"Syncing tournament {tournament_id}...")
    subprocess.run(["python", "manage.py", "sync_ksi_data", f"--tournament={tournament_id}"])
    print(f"Completed tournament {tournament_id}")