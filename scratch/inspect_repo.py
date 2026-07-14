import urllib.request
import zipfile
import tempfile
import shutil
import os

def inspect():
    url = "https://github.com/Mukund181/ERP-System/archive/refs/heads/main.zip"
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "repo.zip")
    
    print("Downloading ERP-System...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
    except Exception as e:
        # Fallback to master
        print("Main branch failed, trying master...")
        url = "https://github.com/Mukund181/ERP-System/archive/refs/heads/master.zip"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)

    print("Extracting...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
        
    print("\nRecursively listing extracted files:")
    for root, dirs, files in os.walk(temp_dir):
        # Print subdirs and files relative to temp_dir
        rel_root = os.path.relpath(root, temp_dir)
        print(f"Directory: {rel_root}")
        for f in files:
            print(f"  - {f}")
            
    shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    inspect()
