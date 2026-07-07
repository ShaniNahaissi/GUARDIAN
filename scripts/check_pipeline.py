import urllib.request
import json

url = 'https://api.github.com/repos/ShaniNahaissi/GUARDIAN/actions/runs?branch=improve-model-people-recognition'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode())
        runs = data.get('workflow_runs', [])
        if not runs:
            print('No active workflow runs found on GitHub.')
        else:
            print(f"Total runs found: {len(runs)}\n")
            for run in runs[:5]:
                print(f"Run Name: {run.get('name')}")
                print(f"Run ID: {run.get('id')}")
                print(f"Status: {run.get('status')}")
                print(f"Conclusion: {run.get('conclusion')}")
                print(f"Trigger Commit: {run.get('head_commit', {}).get('message')}")
                print(f"Created At: {run.get('created_at')}")
                print(f"URL: {run.get('html_url')}")
                print("-" * 50)
except Exception as e:
    print(f"Error fetching runs: {e}")
