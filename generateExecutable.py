"""
This module provides functionality to generate an executable from a Python script using PyInstaller.
It supports building the executable either locally or within a development container.
Functions:
- run_pyinstaller(script: str, workpath: str): Runs PyInstaller to create a one-file bundled executable.
- print_output(label: str, output: subprocess.CompletedProcess): Prints the attributes of a subprocess.CompletedProcess object.
- build_executable_in_devcontainer(): Builds a (Linux) executable in a development container.
Usage:
- Run the script without any flags to build both locally & in a development container.
- Run the script with the --container flag to build and run in a development container.
- Run the script with the --local flag to build and run locally.
- FileNotFoundError: If the 'devcontainer' command is not available in the PATH.
- ValueError: If the containerId cannot be retrieved from the devcontainer output.
- Exception: If the platform is unsupported.
"""
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys

import PyInstaller.__main__


def run_pyinstaller(script: str, workpath: str):
    """
    Run PyInstaller to create a one-file bundled executable.

    :param script: The script to be bundled into an executable.
    :param workpath: The directory to use for the build process.
    """
    PyInstaller.__main__.run([
        script,
        '--onefile',  # Create a one-file bundled executable
        '--workpath', workpath,  # The directory to use for the build process
        '--icon', 'team-evil.ico',
        '--clean'  # Clean the build directory before building, makes the build slower but more reliable
    ])


def print_output(label: str, output: subprocess.CompletedProcess):
    """
    Print the attributes of a subprocess.CompletedProcess object.

    :param label: A label to identify the output.
    :param output: The subprocess.CompletedProcess object to print.
    """
    print(f'{label}:')
    for attr in dir(output):
        if not callable(getattr(output, attr)) and not attr.startswith('_'):
            print(f'{attr}: {getattr(output, attr)}')
    print('#################################################################')


def build_executable_in_devcontainer():
    """
    Build a (linux) executable in a development container.
    """
    try:
        # Check if the devcontainer command is available
        devcontainer_path = shutil.which('devcontainer')
        if devcontainer_path is None:
            raise FileNotFoundError("The 'devcontainer' command is not available in your PATH.")

        # Build the development container
        # build_result = subprocess.run(['devcontainer', 'build', '--workspace-folder', '.'], shell=True, capture_output=True, text=True, check=True, encoding='utf-8')
        # print_output("Container build", build_result)

        # Run the development container
        up_result = subprocess.run(['devcontainer', 'up', '--workspace-folder', '.'], shell=True, capture_output=True, text=True, check=True, encoding='utf-8')
        print_output("Container up", up_result)

        # Parse the JSON output to get the containerId
        container_info = json.loads(up_result.stdout)
        container_id = container_info.get("containerId")
        # remote_workspace_folder = container_info.get("remoteWorkspaceFolder")
        if not container_id:
            raise ValueError("Failed to get containerId from the output")

        # Run the script to generate the executable
        exec_result = subprocess.run(['devcontainer', 'exec', '--container-id', container_id, '--workspace-folder', '.', 'python', f'{os.path.basename(__file__)}', '--local'], shell=True, capture_output=True, text=True, check=True, encoding='utf-8')
        print_output("Script execution", exec_result)

        # Stop and delete the container
        # down_result = subprocess.run(['devcontainer', 'down', '--container-id', containerId], shell=True, capture_output=True, text=True, check=True)  # Not working in cli yet
        # print("Container down: ", down_result)

        # Stop and remove the container using Docker commands
        stop_result = subprocess.run(['docker', 'stop', container_id], shell=True, capture_output=True, text=True, check=True, encoding='utf-8')
        print_output("Container stop", stop_result)

        remove_result = subprocess.run(['docker', 'rm', container_id], shell=True, capture_output=True, text=True, check=True)
        print_output("Container remove", remove_result)

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Make sure the 'devcontainer' command is available in your PATH.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    """
    Main function to parse arguments and trigger the build process.
    """
    argparser = argparse.ArgumentParser(description="Generate executable for UARTVCUPortMap")
    argBuildGroup = argparser.add_mutually_exclusive_group()
    argBuildGroup.add_argument("--container", help="Build and run in devcontainer", action="store_true")
    argBuildGroup.add_argument("--local", help="Build and run locally", action="store_true")
    args = argparser.parse_args()

    if not args.local:
        build_executable_in_devcontainer()

    if not args.container:
        if platform.system() == "Windows":
            WORKPATH = 'buildWindows'
        elif platform.system() == "Linux":
            WORKPATH = 'buildLinux'
        else:
            raise Exception('Unsupported platform')

        run_pyinstaller('UARTVCUPortMap.py', WORKPATH)


if __name__ == "__main__":
    main()
