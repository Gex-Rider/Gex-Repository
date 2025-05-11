import subprocess

subprocess.run("git add .", shell=True)
subprocess.run('git commit -m "Auto update"', shell=True)
subprocess.run("git push origin main", shell=True)