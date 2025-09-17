
import argparse
import logging
import os
import subprocess
import sys
import shutil
from time import sleep

import modbus_tk
import modbus_tk.defines as cst
import modbus_tk.modbus_rtu as modbus_rtu
import serial
import pymdfu

def parse_arguments():
    parser = argparse.ArgumentParser(description="NTN-MODBUS-MASTER-MCU-FW-UPDATE")
    parser.add_argument("--image", type=str, help="firmware image file path", default='')
    parser.add_argument("--port", type=str, help="device port, default is /dev/ttyUSB0", default='/dev/ttyUSB0')
    parser.add_argument("--dev_id", type=int, help="device Modbus ID, default is 1", default=1)
    parser.add_argument("--retry", action='store_true', help="Use for MCU already in bootloader Mode", default=False)
    return parser.parse_args()

def get_logger():
    return modbus_tk.utils.create_logger('console')

def find_pymdfu_executable():
    """Find the pymdfu executable, handling Windows path issues."""
    # First try to find pymdfu in PATH
    pymdfu_path = shutil.which('pymdfu')
    if pymdfu_path:
        return pymdfu_path

    # On Windows, try with .exe extension
    if sys.platform == 'win32':
        pymdfu_path = shutil.which('pymdfu.exe')
        if pymdfu_path:
            return pymdfu_path

    # Try to find it in Python Scripts directory
    if sys.platform == 'win32':
        python_scripts = os.path.join(os.path.dirname(sys.executable), 'Scripts')
        pymdfu_exe = os.path.join(python_scripts, 'pymdfu.exe')
        if os.path.exists(pymdfu_exe):
            return pymdfu_exe

        pymdfu_script = os.path.join(python_scripts, 'pymdfu')
        if os.path.exists(pymdfu_script):
            return pymdfu_script

    # Try using python -m pymdfu as fallback
    try:
        # Test if pymdfu module can be imported and run
        result = subprocess.run([sys.executable, '-m', 'pymdfu', '--help'],
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return [sys.executable, '-m', 'pymdfu']
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        pass

    # If all else fails, return 'pymdfu' and let subprocess handle the error
    return 'pymdfu'

def log_args(args, logger):
    logger.info(f'Image Path: {args.image}')
    logger.info(f'Port: {args.port}')
    logger.info(f'Device Modbus ID: {args.dev_id}')
    logger.info(f'Retry: {args.retry}')

class NTNModbusMaster:
    def __init__(self, slave_address, port, baudrate=115200, bytesize=8, parity='N', stopbits=1, xonxoff=0, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        try:
            self.master = modbus_rtu.RtuMaster(
                serial.Serial(
                    port=port,
                    baudrate=baudrate,
                    bytesize=bytesize,
                    parity=parity,
                    stopbits=stopbits,
                    xonxoff=xonxoff
                )
            )
            self.master.set_timeout(1)
            self.master.set_verbose(False)
            self.slave_addr = slave_address
            self.logger.info('NTN dongle init!')
        except modbus_tk.modbus.ModbusError as e:
            self.logger.error(f'{e} - Code={e.get_exception_code()}')
            raise

    def read_register(self, reg, functioncode=cst.READ_INPUT_REGISTERS):
        try:
            value = self.master.execute(self.slave_addr, functioncode, reg, 1)
            return value[0] if value[0] != 0 else None
        except Exception as e:
            self.logger.info(e)
            return None

    def read_registers(self, reg, num, functioncode=cst.READ_INPUT_REGISTERS):
        try:
            values = self.master.execute(self.slave_addr, functioncode, reg, num)
            return values if not all(x == 0 for x in values) else None
        except Exception as e:
            self.logger.info(e)
            return None

    def set_registers(self, reg, val):
        try:
            if val is not None:
                self.master.execute(self.slave_addr, cst.WRITE_MULTIPLE_REGISTERS, reg, output_value=val)
                return True
            return False
        except Exception as e:
            self.logger.info(e)
            return False

    def set_register(self, reg, val):
        try:
            if val is not None:
                self.master.execute(self.slave_addr, cst.WRITE_SINGLE_REGISTER, reg, output_value=val)
                return True
            return False
        except Exception as e:
            self.logger.info(e)
            return False

    def close(self):
        """Close the Modbus connection and release the serial port."""
        try:
            if hasattr(self, 'master') and self.master:
                self.master.close()
                self.logger.info('NTN dongle connection closed!')
        except Exception as e:
            self.logger.error(f'Error closing connection: {e}')

def run_firmware_update(args, logger):
    if not args.image:
        raise ValueError('Missing firmware image file path')

    # Only establish Modbus connection if not in retry mode
    if not args.retry:
        ntn_dongle = NTNModbusMaster(
            slave_address=args.dev_id,
            port=args.port,
            baudrate=115200,
            logger=logger
        )

        valid_passwd = ntn_dongle.set_registers(0x0000, (0, 0, 0, 0))
        logger.info(f'Password valid: {valid_passwd}')

        if not valid_passwd:
            raise RuntimeError('Failed to set password or password invalid.')

        # Enable Engineering mode
        ntn_dongle.set_register(0xFFD0, 0xAA55)
        # Enable Bootloader Mode
        ntn_dongle.set_register(0xD000, 0xAA55)
        # Reset MCU
        ntn_dongle.set_register(0xFD00, 0xAA55)
        sleep(1)

        # Close the Modbus connection to release the serial port
        ntn_dongle.close()
        sleep(0.5)  # Give some time for the port to be released
    else:
        logger.info('Retry mode: Skipping Modbus configuration, device should already be in bootloader mode')
        # In retry mode, just wait a bit to ensure any previous connections are closed
        sleep(0.5)
    
    # Find the correct pymdfu executable
    pymdfu_cmd = find_pymdfu_executable()
    logger.info(f'Using pymdfu command: {pymdfu_cmd}')

    # Build command list - handle both string and list cases
    if isinstance(pymdfu_cmd, list):
        command = pymdfu_cmd + [
            "update",
            "--tool", "serial",
            "--port", args.port,
            "--baudrate", '115200',
            "--image", args.image,
            "-v", "debug"
        ]
    else:
        command = [
            pymdfu_cmd, "update",
            "--tool", "serial",
            "--port", args.port,
            "--baudrate", '115200',
            "--image", args.image,
            "-v", "debug"
        ]

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        universal_newlines=True
    )

    for line in process.stdout:
        logger.info(line.rstrip())

    return_code = process.wait()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, command)

def main():
    args = parse_arguments()
    logger = get_logger()
    log_args(args, logger)
    try:
        run_firmware_update(args, logger)
    except Exception as e:
        logger.error(f'Firmware update failed: {e}')
        raise

if __name__ == '__main__':
    main()
