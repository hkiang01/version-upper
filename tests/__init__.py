import subprocess
import sys

subprocess.check_call(["git", "config", "user.email", "you@example.com"])
subprocess.check_call(["git", "config", "user.name", "Your Name"])


sys.path.insert(0, "../")
