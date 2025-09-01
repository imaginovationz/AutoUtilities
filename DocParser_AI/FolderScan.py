'''
Created on Aug 29, 2025

@author: ernig
'''
import os
import tkinter as tk
from tkinter import filedialog

def scan_folder_tree(main_folder):
    """
    Scans through the main_folder and returns a nested dictionary representing
    the folder and file tree structure.
    """
    def build_tree(path):
        tree = {'name': os.path.basename(path), 'type': 'folder', 'children': []}
        try:
            with os.scandir(path) as it:
                for entry in it:
                    if entry.is_dir():
                        tree['children'].append(build_tree(entry.path))
                    else:
                        tree['children'].append({'name': entry.name, 'type': 'file'})
        except PermissionError:
            # Skip folders/files that cannot be accessed
            pass
        return tree

    return build_tree(main_folder)

def select_folder():
    root = tk.Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory(title="Select Main Folder to Scan")
    root.destroy()
    return folder_selected

def print_tree(tree, indent=""):
    print(f"{indent}{tree['name']}/" if tree['type'] == 'folder' else f"{indent}{tree['name']}")
    if tree['type'] == 'folder':
        for child in tree['children']:
            print_tree(child, indent + "    ")

if __name__ == "__main__":
    main_folder = select_folder()
    if not main_folder or not os.path.isdir(main_folder):
        print("Invalid folder path or selection cancelled.")
    else:
        tree = scan_folder_tree(main_folder)
        print_tree(tree)