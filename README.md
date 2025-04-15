# NTN Dongle MCU Firmware Update

This Python script facilitates firmware updates for NTN DOngle MCU devices using the `pymdfu` library over a serial connection.

## Features
- Updates firmware on NTN Dongle MCU devices.
- Supports Modbus RTU communication over serial ports.
- Configurable via command-line arguments for image path, port, device ID, and retry mode.
- Logs detailed process information for debugging.
- Handles password validation and bootloader mode activation.

## Prerequisites
- Python 3.6+
- Required Python packages:
  - `pymdfu`
  - `modbus_tk`
  - `pyserial`
- A compatible NTN Modbus Master MCU device connected via a serial port (e.g., `/dev/ttyUSB0`).
- Firmware image file for the update.

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/CREATIVE5-io/Hestia-FW-Update-Python.git
   cd Hestia-FW-Update-Python
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
Run the script with appropriate command-line arguments:

```bash
python ntn_dongle_fw_update.py --image <path_to_firmware_image> --port <serial_port> --dev_id <device_id> [--retry]
```

### Arguments
- `--image`: Path to the firmware image file (required).
- `--port`: Serial port of the device (default: /dev/ttyUSB0).
- `--dev_id`: Modbus device ID (default: 1).
- `--retry`: Use if the MCU is already in bootloader mode (optional).

### Example
```bash
python ntn_dongle_fw_update.py --image firmware.bin --port /dev/ttyUSB0 --dev_id 1
```

## Script Overview
The script:
1. Parses command-line arguments.
2. Initializes a Modbus RTU master connection.
3. Validates the password (if not in retry mode).
4. Activates engineering and bootloader modes (if not in retry mode).
5. Resets the MCU (if not in retry mode).
6. Executes the `pymdfu update` command to perform the firmware update.
7. Logs all steps and outputs from the update process.

## Logging
- Logs are output to the console with levels `INFO`, `ERROR`, etc.
- Real-time output from the `pymdfu` update process is captured and logged.

## Troubleshooting
- Ensure the serial port is correct and accessible.
- Verify the firmware image file exists and is valid.
- Check that the device ID matches the target MCU.
- Use `--retry` if the device is already in bootloader mode.
- Install missing dependencies if errors occur.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for suggestions or bug reports.
