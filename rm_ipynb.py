import os
import shutil

delete_dirs = ['.ipynb_checkpoints', '__pycache__']

def delete_checkpoints(directory):
    for root, dirs, files in os.walk(directory, topdown=False):
        for name in files:
            if name in delete_dirs:
                file_path = os.path.join(root, name)
                try:
                    os.remove(file_path)
                    print(f"Deleted file: {file_path}")
                except OSError as e:
                    print(f"Error deleting file: {e.strerror} - {file_path}")
        for name in dirs:
            dir_path = os.path.join(root, name)
            if name in delete_dirs:
                try:
                    shutil.rmtree(dir_path)
                    print(f"Deleted directory: {dir_path}")
                except OSError as e:
                    print(f"Error deleting directory: {e.strerror} - {dir_path}")

# 替换为你的起始目录
start_directory = './'
delete_checkpoints(start_directory)