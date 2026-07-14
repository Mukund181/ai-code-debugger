import os
import urllib.request
import zipfile
import tempfile
import shutil
import sys

# Add root dir to path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.insert(0, root_dir)

from repo_analyzer.ast_parser import parse_any_file, ALL_SOURCE_EXTENSIONS, should_skip_dir
from repo_analyzer.graph_rag import CodeGraph

def run_diagnostics():
    log_path = os.path.join(current_dir, "diagnostic_log.txt")
    with open(log_path, "w", encoding="utf-8") as log:
        log.write("=== REPOSITORY ANALYSIS DIAGNOSTICS ===\n")
        
        # Analyze ERP-System
        url = "https://github.com/Mukund181/ERP-System/archive/refs/heads/main.zip"
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, "repo.zip")
        
        log.write(f"\nDownloading ERP-System from: {url}\n")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            log.write("Download success.\n")
        except Exception as e:
            log.write(f"Download failed on main: {e}. Trying master...\n")
            url = "https://github.com/Mukund181/ERP-System/archive/refs/heads/master.zip"
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)
                log.write("Download success on master.\n")
            except Exception as ex:
                log.write(f"Download failed on master: {ex}\n")
                return

        # Extract
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            log.write("Extraction success.\n")
        except Exception as e:
            log.write(f"Extraction failed: {e}\n")
            return
            
        # Get dirs
        dirs = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d)) and d != "__pycache__"]
        log.write(f"Extracted directories: {dirs}\n")
        if not dirs:
            log.write("No directory found inside zip!\n")
            return
            
        extracted_path = os.path.join(temp_dir, dirs[0])
        log.write(f"Scanning target path: {extracted_path}\n")
        
        # Traverse directory
        all_files = []
        for r, ds, fs in os.walk(extracted_path):
            ds[:] = [d for d in ds if not should_skip_dir(d)]
            for f in fs:
                abs_p = os.path.join(r, f)
                rel_p = os.path.relpath(abs_p, extracted_path)
                all_files.append((abs_p, rel_p))
                
        log.write(f"Total files found recursively: {len(all_files)}\n")
        for abs_p, rel_p in all_files:
            ext = os.path.splitext(rel_p)[1].lower()
            is_supported = ext in ALL_SOURCE_EXTENSIONS
            log.write(f" - {rel_p} (Ext: {ext}, Supported: {is_supported})\n")
            
            if is_supported:
                log.write(f"   Parsing {rel_p}...\n")
                try:
                    parsed = parse_any_file(abs_p)
                    log.write(f"   Parse result keys: {list(parsed.keys())}\n")
                    if "error" in parsed:
                        log.write(f"   Parse Error details: {parsed['error']}\n")
                except Exception as parse_err:
                    log.write(f"   Parser raised exception: {parse_err}\n")
                    
        shutil.rmtree(temp_dir, ignore_errors=True)
        log.write("\nDiagnostics completed.\n")

if __name__ == "__main__":
    run_diagnostics()
