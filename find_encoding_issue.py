import os

def find_problematic_file():
    for root, _, files in os.walk("src/aixn"):
        for filename in files:
            filepath = os.path.join(root, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    f.read()
            except UnicodeDecodeError:
                print(f"Problematic file: {filepath}")
                return

if __name__ == "__main__":
    find_problematic_file()
