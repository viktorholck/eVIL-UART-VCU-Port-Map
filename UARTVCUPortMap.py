"""
This script VCU UART tagets to their corresponding COM port address.
Classes:
    VCUPort: A data class representing various ports in a VCU system and their corresponding COM port addresses.
Functions:
    map_vcu_ports(ports: serial.tools.list_ports_common.ListPortInfo) -> VCUPort:
    main():
"""
import argparse
import json
import platform
import re
import sys
from dataclasses import asdict, dataclass
from typing import Optional
import serial
import serial.tools.list_ports  # Needed to patch the serial.tools.list_ports module on Windows

# If running on Windows patch the serial.tools.list_ports to the list_ports_windows local copy
# To fix a known issue with the serial library on Windows not showing all information for FTDI devices
PLATFORM_WINDOWS: bool = False
if platform.system() == "Windows":
    PLATFORM_WINDOWS = True
    import list_ports_windows_patched_from_pyserial_3_5
    serial.tools.list_ports = list_ports_windows_patched_from_pyserial_3_5  # Patch the serial.tools.list_ports module to enable identificatcon of serial ports on the FTDI serial hub


@dataclass
class VCUPort:
    """
    A class representing a VCU (Vehicle Control Unit) port mapping for FTDI devices.
    Attributes:
        HPA (Optional[str]): High Priority A port.
        HIA (Optional[str]): High Isolation A port.
        HIB (Optional[str]): High Isolation B port.
        LPA (Optional[str]): Low Priority A port.
        SGA (Optional[str]): Signal Ground A port.
        JUMPERS (Optional[str]): Jumpers port.
    Methods:
        get_location_regex(list_of_FTDI_major_location_numbers: list) -> dict:
            Generates a dictionary of regex patterns for identifying port locations
            based on the provided list of FTDI major location numbers.
    """
    # list_of_FTDI_major_location_numbers: list  # List of FTDI major location numbers
    HPA: Optional[str] = None
    HIA: Optional[str] = None
    HIB: Optional[str] = None
    LPA: Optional[str] = None
    SGA: Optional[str] = None
    JUMPERS: Optional[str] = None

    def get_location_regex(self, list_of_FTDI_major_location_numbers: list) -> dict:
        self.FTDI1 = list_of_FTDI_major_location_numbers[0] if list_of_FTDI_major_location_numbers else None
        self.FTDI2 = list_of_FTDI_major_location_numbers[1] if len(list_of_FTDI_major_location_numbers) > 1 else None
        add_1_if_windows = 1 if PLATFORM_WINDOWS else 0

        # print(f"FTDI1: {self.FTDI1}, FTDI2: {self.FTDI2}")
        if self.FTDI2 is not None:  # if there are two FTDI devices (Sisyphos board)
            return {
                "HPA": rf".*{self.FTDI1}:1\.{0+add_1_if_windows}",
                "HIA": rf".*{self.FTDI1}:1\.{3+add_1_if_windows}",
                "HIB": rf".*{self.FTDI1}:1\.{2+add_1_if_windows}",
                "LPA": rf".*{self.FTDI1}:1\.{1+add_1_if_windows}",
                "SGA": rf".*{self.FTDI2}:1\.{0+add_1_if_windows}",
                "JUMPERS": rf".*{self.FTDI2}:1\.{1+add_1_if_windows}"
                }
        else:  # if there is only one FTDI device (verC board)
            return {
                "HPA": rf".*{self.FTDI1}:1\.{2+add_1_if_windows}",
                "HIA": rf".*{self.FTDI1}:1\.{0+add_1_if_windows}",
                "HIB": rf".*{self.FTDI1}:1\.{1+add_1_if_windows}",
                "LPA": rf".*{self.FTDI1}:1\.{3+add_1_if_windows}",
                "SGA": None,
                "JUMPERS": None
                }


def get_FTDI_devices_major_number(ports: list) -> list:
    """
    Extracts and returns a sorted list of unique major numbers from the location
    attributes of the given list of port objects.
    Each port object in the input list is expected to have a `location` attribute
    that contains a string in the format "major:minor". This function extracts the
    major number (the part before the colon) from each port's location and ensures
    that the returned list contains only unique major numbers, sorted in ascending order.
    Args:
        ports (list): A list of port objects, each with a `location` attribute.
    Returns:
        list: A sorted list of unique major numbers as strings.
    """
    major_numbers = set()

    for port in ports:
        if port.location:  # Ensure the location field is not None
            major_number = port.location.split(':')[0]  # Extract the major number (before the dot)
            major_numbers.add(major_number)

    # print(f"Unique major numbers: {sorted(major_numbers)}")
    # print(f"Number of unique major numbers: {len(major_numbers)}")
    return sorted(major_numbers)


def map_vcu_ports(ports: list) -> VCUPort:
    """
    Maps a list of ports to a VCUPort object based on their locations.
    This function identifies FTDI devices from the provided list of ports,
    generates regex patterns for matching port locations, and assigns the
    corresponding device names to the attributes of a VCUPort object.
    Args:
        ports (list): A list of port objects, where each port has attributes
                      such as `location` and `device`.
    Returns:
        VCUPort: An instance of the VCUPort class with its attributes populated
                 based on the matching port locations.
    Notes:
        - The `get_FTDI_devices_major_number` function is used to identify FTDI
          devices from the provided ports.
        - The `get_location_regex` method of the VCUPort class generates regex
          patterns for matching port locations.
        - Ports that do not match any regex pattern are skipped.
    """
    port_map = VCUPort()
    FTDI_devices = get_FTDI_devices_major_number(ports)

    regex = port_map.get_location_regex(FTDI_devices)
    # print(f'regex: {regex}')
    for port in ports:
        for attr in VCUPort.__annotations__.keys():
            if attr not in regex or regex[attr] is None:  # Skip attributes that do not have a corresponding regex pattern
                continue
            # print(f"Matching {attr} with regex: {regex[attr]} and port location: {port.location}")
            if re.match(regex[attr], str(port.location)):  # Match the port's location with the regex pattern
                setattr(port_map, attr, port.device)

    return port_map


def print_output(label: str, output: object):
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


def get_vcu_port_map(debug: bool = False, vid: int = 1027, pid: int = 24593) -> tuple[dict, bool]:
    """
    Scans all available serial ports, filters for valid UART control ports based on the specified VID and PID,
    and returns a port map in dictionary format along with a boolean indicating if any valid ports were found.
    Args:
        vid (int): The Vendor ID (VID) to filter the serial ports. Default is 1027.
        pid (int): The Product ID (PID) to filter the serial ports. Default is 24593.
    Returns:
            - A dictionary representing the port map.
    Debug Information:
        If `debug` is True, the function prints:
            - A list of invalid ports that do not match the specified VID and PID.
            - A list of valid ports that match the specified VID and PID.
            - The generated port map in dictionary format.
    """
    ports = serial.tools.list_ports.comports()
    valid_ports = []  # list of valid ports
    invalid_ports = []  # list of invalid ports

    for port in sorted(ports):
        if port.vid == vid and port.pid == pid:
            valid_ports.append(port)
        else:
            invalid_ports.append(port)

    if debug:
        print("\n################# Invalid Ports:")
        for port in invalid_ports:
            print_output(f'{port.device}', port)

        print("\n################# Valid Ports:")
        for port in valid_ports:
            print_output(f'{port.device}', port)

        print("\n################# Port map:")

    port_map = asdict(map_vcu_ports(valid_ports))
    return port_map, bool(valid_ports)


def main():
    """
    Main function to parse arguments and print the port map in JSON format.
    """
    argparser = argparse.ArgumentParser(description="List all serial ports and filter valid ones for uart_control. Select a port by serial number or COM port.")
    argparser.add_argument("--debug", "-d", action="store_true", help="Enable debug mode")
    args = argparser.parse_args()

    port_map, valid_ports = get_vcu_port_map(debug=args.debug)
    json_output = json.dumps(port_map, indent=4)
    print(json_output)

    if not valid_ports:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
