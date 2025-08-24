import json
import os
import re
import subprocess
import platform
import argparse

import serial


def execute_and_get_json_output(target_path, use_script=False):
    """
    Executes a given executable file or Python script and parses its output as JSON.

    Args:
        target_path (str): The file path to the executable or script to be run.
        use_script (bool): If True, run as Python script; if False, run as executable.

    Returns:
        dict: The parsed JSON output from the target.

    Raises:
        subprocess.CalledProcessError: If the target returns a non-zero exit code.
        json.JSONDecodeError: If the output from the target is not valid JSON.

    Notes:
        - The function captures both stdout and stderr of the target.
        - If an error occurs during execution or JSON parsing, an error message is printed.
    """
    try:
        if use_script:
            # Execute the Python script and capture the output
            result = subprocess.run(["python", target_path], capture_output=True, text=True, check=True)
        else:
            # Execute the executable and capture the output
            result = subprocess.run([target_path], capture_output=True, text=True, check=True)
        # Parse the output as JSON
        output_json = json.loads(result.stdout)
        return output_json
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}, {e.stdout}, {e.stderr}. Is a supported UART board connected?")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON output: {e}")


def send_command_to_serial_device(uart_target: str, uart_target_port: str, baudrate: int = 115200, command: str = "", verbose: bool = True):
    """
    Sends a command to a serial device and retrieves the response.

    Args:
        uart_target (str): A label or identifier for the UART target device.
        uart_target_port (str): The serial port to which the UART target device is connected (e.g., "COM3" or "/dev/ttyUSB0").
        baudrate (int, optional): The communication speed for the serial connection. Defaults to 115200.
        command (str, optional): The command string to send to the serial device. Defaults to an empty string.
        verbose (bool, optional): Whether to print the communication details. Defaults to True.

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
            if verbose:
                # Clean up the response for display
                clean_response = response.strip().replace('\n', ' ').replace('\r', '')
                if len(clean_response) > 60:
                    clean_response = clean_response[:57] + "..."
                
                # Show command and response separately for clarity
                if command:
                    print(f"  └─ Command: {command}")
                    print(f"  └─ Response: {clean_response}")
                else:
                    print("  └─ Command: (empty)")
                    print(f"  └─ Response: {clean_response}")
            return response
    except serial.SerialException as e:
        print(f"  └─ Error communicating with {uart_target} ({uart_target_port}): {e}")
        return None


def verify_uart_connection(uart_target, uart_target_port, verbose=False):
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
        verbose (bool): Whether to show detailed communication logs.
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
            output = send_command_to_serial_device(uart_target, uart_target_port, command='uname -a', verbose=verbose)
            return output and ('QNX hpa' in output)
        case "HIA":
            output = send_command_to_serial_device(uart_target, uart_target_port, command='', verbose=verbose)
            return output and ('GoForHIA>' in output)
        case "LPA":
            output = send_command_to_serial_device(uart_target, uart_target_port, command='', verbose=verbose)
            return output and ('Atmel LP->' in output)
        case "SGA":
            output = send_command_to_serial_device(uart_target, uart_target_port, command='', verbose=verbose)
            return output and (re.search(r'DoIP-.* login:', output) is not None)
        case "HIB":
            output = send_command_to_serial_device(uart_target, uart_target_port, command='', verbose=verbose)
            return output and ('GoForHIB>' in output)
        case "JUMPERS":
            if verbose:
                print("  └─ JUMPERS : Check not implemented")
            return "NOT_IMPLEMENTED"
        case _:
            return False

    return False


def main():
    """
    Main function to execute the UART VCU Port Map executable or Python script, process its output,
    and send a command to a serial device.
    """
    parser = argparse.ArgumentParser(description='Test UART VCU Port Mapping')
    parser.add_argument('--use-script', action='store_true',
                        help='Use uart_controller.py script instead of built executable')
    args = parser.parse_args()

    if args.use_script:
        # Use the Python script directly
        target_path = "UARTVCUPortMap.py"
        if not os.path.isfile(target_path):
            print(f"Error: Python script not found at {target_path}")
            return
        use_script = True
    else:
        # Use the built executable (original behavior)
        if platform.system() == "Windows":
            executable_path_primary = "./UARTVCUPortMap.exe"
            executable_path_secondary = "./dist/UARTVCUPortMap.exe"
        elif platform.system() == "Linux":
            executable_path_primary = "./UARTVCUPortMap"
            executable_path_secondary = "./dist/UARTVCUPortMap"
        else:
            raise RuntimeError('Unsupported platform')

        target_path = executable_path_primary if os.path.isfile(executable_path_primary) else executable_path_secondary
        if not os.path.isfile(target_path):
            print(f"Error: Executable not found at either {executable_path_primary} or {executable_path_secondary}")
            return
        use_script = False

    print("=" * 60)
    print("UART VCU Port Mapping Test")
    print("=" * 60)
    if args.use_script:
        print("Using Python script: uart_controller.py")
    else:
        print(f"Using executable: {target_path}")
    print("-" * 60)

    output = execute_and_get_json_output(target_path, use_script)
    if output:
        # Fields that shouldn't be tested as serial ports
        non_testable_fields = {'MASTER', 'board_type', 'current_mode', 'previous_mode', 'error', 'UNIDENTIFIED'}
        
        # Show board info
        board_type = output.get('board_type', 'Unknown')
        current_mode = output.get('current_mode', 'Unknown')
        master_port = output.get('MASTER', 'Unknown')
        print(f"Board Type: {board_type}")
        print(f"Current Mode: {current_mode}")
        print(f"Master Port: {master_port}")
        print("-" * 60)
        
        # Test each port
        test_results = []
        for key, value in output.items():
            if key in non_testable_fields:
                continue
                
            if value is None:
                result = "NOT MAPPED"
                test_results.append((key, "N/A", result))
                print(f"🔸 {key:<4}: {result}")
                continue
                
            # Test the connection for actual hardware ports only
            print(f"🔧 Testing {key} ({value})...")
            
            status = verify_uart_connection(key, value, verbose=True)
            if status == "NOT_IMPLEMENTED":
                result = "⚠️  NOT IMPLEMENTED"
            elif status:
                result = "✅ PASS"
            else:
                result = "❌ FAIL"
            test_results.append((key, value, result))
            
            # Always show normal format with verbose output
            print(f"🔸 {key:<4}: {result}")
        
        # Summary
        print("-" * 60)
        passed = sum(1 for _, _, result in test_results if "PASS" in result)
        not_implemented = sum(1 for _, _, result in test_results if "NOT IMPLEMENTED" in result)
        total_testable = sum(1 for _, port, _ in test_results if port != "N/A")
        actual_testable = total_testable - not_implemented
        print(f"Test Summary: {passed}/{actual_testable} ports passed")
        if not_implemented > 0:
            print(f"Warning: {not_implemented} port(s) have no test implementation")
        if passed == actual_testable and actual_testable > 0:
            print("🎉 All implemented tests passed!")
        elif passed > 0:
            print("⚠️  Some tests failed")
        else:
            print("💥 All tests failed")


if __name__ == "__main__":
    main()
