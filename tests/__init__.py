import subprocess
import sys

subprocess.check_call(
    ["git", "config", "--global", "user.email", "you@example.com"]
)
subprocess.check_call(["git", "config", "--global", "user.name", "Your Name"])


sys.path.insert(0, "../")
