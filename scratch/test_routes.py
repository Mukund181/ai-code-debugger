import os
import sys
from fastapi.testclient import TestClient

# Ensure workspace is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.insert(0, root_dir)

from main import app

client = TestClient(app)

def test_flow():
    # 1. Analyze repo
    print("Testing /api/analyze-repo...")
    repo_url = "https://github.com/Mukund181/Image-to-Image-using-CGAN"
    response = client.post("/api/analyze-repo", json={"repo_url": repo_url})
    print("Status:", response.status_code)
    print("Response:", response.json())
    
    if response.status_code != 200:
        print("Analysis failed!")
        return
        
    files_list = response.json().get("files_list", [])
    if not files_list:
        print("No files found!")
        return
        
    target_file = files_list[0]
    print(f"\nTesting /api/check-impact for file: {target_file} with empty code_change...")
    
    # 2. Check impact with empty code_change
    response = client.post("/api/check-impact", json={
        "file_path": target_file,
        "code_change": ""
    })
    print("Status:", response.status_code)
    try:
        res_json = response.json()
        print("Response keys:", list(res_json.keys()))
        if "report" in res_json:
            print("\nReport excerpt:")
            print(res_json["report"][:400] + "...")
        else:
            print("Error detail:", res_json.get("detail"))
    except Exception as e:
        print("Failed to parse json response:", str(e))
        print("Raw text:", response.text)

if __name__ == "__main__":
    test_flow()
