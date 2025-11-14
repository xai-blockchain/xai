import os
import subprocess

def find_problematic_file():
    core_dir = "src/aixn/core"
    for filename in os.listdir(core_dir):
        filepath = os.path.join(core_dir, filename)
        if os.path.isfile(filepath):
            print(f"Scanning {filepath}...")
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "semgrep",
                    "--config",
                    "auto",
                    filepath,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode != 0:
                print(f"Error scanning {filepath}:")
                print(result.stdout)
                print(result.stderr)
                # You can choose to stop here or continue
                # return

if __name__ == "__main__":
    find_problematic_file()
