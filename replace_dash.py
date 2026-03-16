import os
import glob

template_dir = r"c:\Users\Naveen\OneDrive\Documents\collegeportal_314 - Copy\templates"

def replace_chars():
    html_files = glob.glob(os.path.join(template_dir, "**", "*.html"), recursive=True)
    count = 0
    for file_path in html_files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        updated = False
        
        if "â€¢" in content:
            content = content.replace("â€¢", "&bull;")
            updated = True
        
        if "â”€" in content:
            content = content.replace("â”€", "-")
            updated = True
            
        if "â• " in content:
            content = content.replace("â• ", "=")
            updated = True

        if updated:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            count += 1
            print(f"Replaced in {file_path}")
            
    print(f"Total files updated: {count}")

if __name__ == "__main__":
    replace_chars()
