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
if platform.system() == "Windows":
    import list_ports_windows_patched_from_pyserial_3_5
    serial.tools.list_ports = list_ports_windows_patched_from_pyserial_3_5  # Patch the serial.tools.list_ports module to enable identificatcon of serial ports on the FTDI serial hub


@dataclass
class VCUPort:
    """
    VCUPort class represents various ports in a VCU (Vehicle Control Unit) system. And the corresponding COM port addresses.

    Attributes:
        HPA (Optional[str])
        HIA (Optional[str])
        HIB (Optional[str])
        LPA (Optional[str])
        SGA (Optional[str])
    """
    HPA: Optional[str] = None
    HIA: Optional[str] = None
    HIB: Optional[str] = None
    LPA: Optional[str] = None
    SGA: Optional[str] = None


def map_vcu_ports(ports: serial.tools.list_ports_common.ListPortInfo) -> VCUPort:
    """
    Maps the VCU ports to their corresponding COM port addresses.

    Args:
        ports (serial.tools.list_ports_common.ListPortInfo): List of serial ports.

    Returns:
        VCUPort: An instance of VCUPort with mapped ports.
    """
    port_map = VCUPort()
    for port in ports:
        if port.location == 1 or re.match(r".*:1\.0", str(port.location)):
            port_map.HIA = port.device
        elif port.location == 2 or re.match(r".*:1\.1", str(port.location)):
            port_map.HIB = port.device
        elif port.location == 3 or re.match(r".*:1\.2", str(port.location)):
            port_map.HPA = port.device
        elif port.location == 4 or re.match(r".*:1\.3", str(port.location)):
            port_map.LPA = port.device
        elif port.location == 5 or re.match(r".*:1\.4", str(port.location)):  # Not valid/available on verC UART board's
            port_map.SGA = port.device
    return port_map


def main():
    """
    Main function to list all serial ports, filter valid ones for uart_control, and print the port map in JSON format.
    """
    argparser = argparse.ArgumentParser(description="List all serial ports and filter valid ones for uart_control. Select a port by serial number or COM port.")
    argparser.add_argument("--debug", "-d", action="store_true", help="Enable debug mode")
    args = argparser.parse_args()

    ports = serial.tools.list_ports.comports()
    valid_ports = []  # list of valid ports
    invalid_ports = []  # list of invalid ports

    for port in sorted(ports):
        if port.vid == 1027 and port.pid == 24593:
            valid_ports.append(port)
        else:
            invalid_ports.append(port)

    if args.debug:
        print("\n################# Invalid Ports:")
        for port in invalid_ports:
            print(f'Port.__dict__: {port.__dict__}\n')

        print("\n################# Valid Ports:")
        for port in valid_ports:
            print(f'Port.__dict__: {port.__dict__}\n')

        print("\n################# Port map:")

    json_output = json.dumps(asdict(map_vcu_ports(valid_ports)), indent=4)
    print(json_output)
    if not valid_ports:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
