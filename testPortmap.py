import json
import os
import re
import subprocess
import platform

import serial


def execute_and_get_json_output(executable_path):
    """
    Executes a given executable file and parses its output as JSON.

    Args:
        executable_path (str): The file path to the executable to be run.

    Returns:
        dict: The parsed JSON output from the executable.

    Raises:
        subprocess.CalledProcessError: If the executable returns a non-zero exit code.
        json.JSONDecodeError: If the output from the executable is not valid JSON.

    Notes:
        - The function captures both stdout and stderr of the executable.
        - If an error occurs during execution or JSON parsing, an error message is printed.
    """
    try:
        # Execute the command and capture the output
        result = subprocess.run([executable_path], capture_output=True, text=True, check=True)
        # Parse the output as JSON
        output_json = json.loads(result.stdout)
        return output_json
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}, {e.stdout}, {e.stderr}. Is a supported UART board connected?")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON output: {e}")


def send_command_to_serial_device(uart_target: str, uart_target_port: str, baudrate: int = 115200, command: str = ""):
    """
    Sends a command to a serial device and retrieves the response.

    Args:
        uart_target (str): A label or identifier for the UART target device.
        uart_target_port (str): The serial port to which the UART target device is connected (e.g., "COM3" or "/dev/ttyUSB0").
        baudrate (int, optional): The communication speed for the serial connection. Defaults to 115200.
        command (str, optional): The command string to send to the serial device. Defaults to an empty string.

    Returns:
        str: The response received from the serial device, or None if an error occurs.

    Raises:
        serial.SerialException: If there is an issue with the serial communication.

    Notes:
        - The command string is automatically appended with a carriage return ("\r") before being sent.
        - The function reads up to 1024 bytes from the serial device as a response.
        - The response is decoded from bytes to a string before being returned.
    """
    try:
        with serial.Serial(uart_target_port, baudrate, timeout=1) as ser:
            ser.write((command + "\r").encode())
            response = ser.read(1024).decode()
            print(f"{uart_target}-> {uart_target_port}: {response}")
            return response
    except serial.SerialException as e:
        print(f"Error communicating with serial device: {e}")
        return None


def verify_uart_connection(uart_target, uart_target_port):
    """
    Verifies the UART connection to a specified target by sending a command
    and checking the response for expected output.
    Args:
        uart_target (str): The target UART device identifier. Supported values are:
            - "HPA"
            - "HIA"
            - "LPA"
            - "SGA"
            - "HIB"
        uart_target_port (str): The port associated with the UART target.
    Returns:
        bool: True if the connection is verified based on the expected response
        for the given target, False otherwise.
    Notes:
        - The function uses `send_command_to_serial_device` to send a command
          to the specified UART target and port.
        - The expected response varies depending on the `uart_target` value.
        - If the `uart_target` is not recognized, the function returns False.
    """
    match uart_target:
        case "HPA":
            output = send_command_to_serial_device(uart_target, uart_target_port, command='uname -a')
            return output and ('QNX hpa' in output)
        case "HIA":
            output = send_command_to_serial_device(uart_target, uart_target_port, command='')
            return output and ('GoForHIA>' in output)
        case "LPA":
            output = send_command_to_serial_device(uart_target, uart_target_port, command='')
            return output and ('Atmel LP->' in output)
        case "SGA":
            output = send_command_to_serial_device(uart_target, uart_target_port, command='')
            return output and (re.search(r'DoIP-.* login:', output) is not None)
        case "HIB":
            output = send_command_to_serial_device(uart_target, uart_target_port, command='')
            return output and ('GoForHIB>' in output)
        case "JUMPERS":
            print("JUMPERS: Check not implemented")
            return False
        case _:
            return False

    return False


def main():
    """
    Main function to execute the UART VCU Port Map executable, process its output,
    and send a command to a serial device.
    """

    if platform.system() == "Windows":
        executable_path_primary = "./UARTVCUPortMap.exe"
        executable_path_secondary = "./dist/UARTVCUPortMap.exe"
    elif platform.system() == "Linux":
        executable_path_primary = "./UARTVCUPortMap"
        executable_path_secondary = "./dist/UARTVCUPortMap"
    else:
        raise Exception('Unsupported platform')

    executable_path = executable_path_primary if os.path.isfile(executable_path_primary) else executable_path_secondary
    if not os.path.isfile(executable_path):
        print(f"Error: Executable not found at either {executable_path_primary} or {executable_path_secondary}")
        return

    output = execute_and_get_json_output(executable_path)
    if output:
        for key, value in output.items():
            if value is None:
                print(f"{key} - Status: Not mapped\n")
                continue
            status = verify_uart_connection(key, value)
            print(f"{key} ({value}) - Status: {'OK' if status else 'ERROR'}\n")


if __name__ == "__main__":
    main()
