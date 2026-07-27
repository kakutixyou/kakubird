# set.py
import os

def init_structure():
    base_path = os.getcwd()
    print(f"📁 Initializing empty boxes under: {base_path}")
    
    structure = {'keywords': ['deployment_keywords.json', 'language_keywords.json', 'framework_keywords.json', 'build_keywords.json'], 'themes': ['deployment_themes.json', 'architecture_themes.json', 'project_themes.json', 'ui_themes.json'], 'templates': ['framework_templates.json', 'folder_templates.json', 'file_templates.json', 'github_templates.json', 'docker_templates.json'], 'rules': ['dependency_rules.json', 'framework_rules.json', 'naming_rules.json', 'project_rules.json'], 'examples': ['flask_project.json', 'react_project.json', 'fastapi_project.json', 'electron_project.json', 'vscode_extension.json'], 'metadata': ['version.json', 'schema.json', 'source.json']}
    
    for folder, files in structure.items():
        if folder == "root":
            target_dir = base_path
        else:
            target_dir = os.path.join(base_path, folder.replace("/", os.sep))
            
        os.makedirs(target_dir, exist_ok=True)
        
        for f in files:
            file_path = os.path.join(target_dir, f)
            if not os.path.exists(file_path):
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write("")
                print(f"  📄 Created Empty: {os.path.relpath(file_path, base_path)}")

    print("✅ Setup Completed successfully!")

if __name__ == "__main__":
    init_structure()

