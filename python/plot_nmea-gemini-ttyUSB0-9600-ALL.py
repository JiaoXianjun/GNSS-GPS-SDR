import serial
import time
import os
import sys
import re

# --- Configuration ---
SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 9600
TIMEOUT = 1 # seconds for serial read timeout

# --- Data Storage ---
# Dictionary to hold parsed satellite data
# Structure:
# {
#   'GP': {'total_sats_in_view': 0, 'satellites': {PRN: {'elev': X, 'azimuth': Y, 'snr': Z}}},
#   'GB': {'total_sats_in_view': 0, 'satellites': {PRN: {'elev': X, 'azimuth': Y, 'snr': Z}}},
#   'GA': {'total_sats_in_view': 0, 'satellites': {PRN: {'elev': X, 'azimuth': Y, 'snr': Z}}},
#   'GN': {'total_sats_in_view': 0, 'satellites': {PRN: {'elev': X, 'azimuth': Y, 'snr': Z}}},
#   # Add other constellations if needed, e.g., 'GL' for GLONASS, 'GQ' for QZSS
# }
satellite_data = {
    'GP': {'total_sats_in_view': 0, 'satellites': {}},
    'GB': {'total_sats_in_view': 0, 'satellites': {}},
    'GA': {'total_sats_in_view': 0, 'satellites': {}},
    'GN': {'total_sats_in_view': 0, 'satellites': {}},
    'GL': {'total_sats_in_view': 0, 'satellites': {}}, # GLONASS
    'GQ': {'total_sats_in_view': 0, 'satellites': {}}  # QZSS
}

# --- NMEA Parsing Helper ---
def parse_gsv_sentence(line):
    """
    Parses a single NMEA GSV sentence.
    Returns a tuple: (talker_id, total_msgs, msg_num, total_sats_in_view, satellite_list)
    satellite_list is a list of tuples: (prn, elevation, azimuth, snr)
    Returns None if parsing fails or checksum is invalid.
    """
    try:
        # Check for valid NMEA sentence start and checksum
        if not line.startswith('$') or '*' not in line:
            return None

        parts = line.strip().split('*')
        if len(parts) != 2:
            return None # Malformed sentence

        sentence_data = parts[0]
        checksum_str = parts[1].strip()

        # Calculate checksum
        calc_checksum = 0
        for char in sentence_data[1:]: # Exclude '$'
            calc_checksum ^= ord(char)

        if checksum_str.upper() != f"{calc_checksum:02X}":
            # print(f"Checksum mismatch: Expected {checksum_str.upper()}, Got {calc_checksum:02X} for {line.strip()}")
            return None # Checksum mismatch

        fields = sentence_data.split(',')
        if len(fields) < 4:
            return None # Not enough fields for a basic GSV message

        talker_id = fields[0][1:3] # e.g., 'GP', 'GN', 'GB', 'GA'
        message_type = fields[0][3:] # e.g., 'GSV'

        if message_type != 'GSV':
            return None # Not a GSV message

        total_msgs = int(fields[1])
        msg_num = int(fields[2])
        total_sats_in_view = int(fields[3])

        satellites = []
        # Each satellite takes 4 fields: PRN, Elevation, Azimuth, SNR
        for i in range(4, len(fields), 4):
            if len(fields) >= i + 4: # Ensure all 4 fields for a satellite are present
                prn = int(fields[i]) if fields[i] else None
                elevation = int(fields[i+1]) if fields[i+1] else None
                azimuth = int(fields[i+2]) if fields[i+2] else None
                snr = int(fields[i+3]) if fields[i+3] else None
                if prn is not None: # Only add if PRN is valid
                    satellites.append({'prn': prn, 'elev': elevation, 'azimuth': azimuth, 'snr': snr})
            else:
                # Handle cases where the last satellite might have incomplete data
                break

        return (talker_id, total_msgs, msg_num, total_sats_in_view, satellites)

    except (ValueError, IndexError) as e:
        # print(f"Error parsing GSV line '{line.strip()}': {e}")
        return None

# --- Terminal Display ---
def clear_terminal_region(num_lines):
    """Clears a specified number of lines from the current cursor position upwards."""
    # Move cursor up by num_lines, clear from cursor to end of screen
    sys.stdout.write(f"\033[{num_lines}A") # Move cursor up
    sys.stdout.write("\033[J") # Clear from cursor to end of screen
    sys.stdout.flush()

def display_satellite_data():
    """
    Prints the current satellite data to the terminal, clearing the previous output.
    """
    # Calculate the number of lines needed for the display
    # Header lines + (constellation lines + satellite lines) for each constellation
    num_display_lines = 2 # For "GNSS Satellite Data" and empty line

    for constellation, data in satellite_data.items():
        if data['total_sats_in_view'] > 0:
            num_display_lines += 2 # For "--- Constellation (X sats) ---" and header row
            num_display_lines += len(data['satellites']) # For each satellite line
        else:
            num_display_lines += 1 # For "--- Constellation (0 sats) ---"

    # Clear the previous display region
    # This assumes the script is the only thing writing to the terminal
    # and we want to clear the entire area it uses.
    # For a more robust solution in a busy terminal, one might save/restore cursor.
    sys.stdout.write("\033[H") # Move cursor to home position (top-left)
    sys.stdout.write("\033[J") # Clear from cursor to end of screen
    sys.stdout.flush()

    print("\033[1mGNSS Satellite Data\033[0m\n") # Bold title

    for constellation, data in satellite_data.items():
        total_sats = data['total_sats_in_view']
        sats = data['satellites']

        print(f"\033[1m--- {constellation} ({total_sats} sats) ---\033[0m") # Bold constellation header

        if total_sats > 0:
            print(f"{'PRN':<5} {'Elev':<5} {'Azim':<5} {'SNR':<5}")
            print("-" * 23)
            sorted_sats = sorted(sats.values(), key=lambda x: x['prn'])
            for sat in sorted_sats:
                prn = sat.get('prn', 'N/A')
                elev = sat.get('elev', 'N/A')
                azim = sat.get('azimuth', 'N/A')
                snr = sat.get('snr', 'N/A')
                print(f"{str(prn):<5} {str(elev):<5} {str(azim):<5} {str(snr):<5}")
        else:
            print("No satellites in view.")
        print("") # Empty line for spacing

    sys.stdout.flush()

# --- Main Script Logic ---
def main():
    ser = None
    try:
        # Open the serial port
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT)
        print(f"Successfully opened serial port {SERIAL_PORT} at {BAUD_RATE} bps.")
        print("Press Ctrl+C to exit.")
        time.sleep(1) # Give a moment for the message to be seen

        # Clear initial screen
        os.system('cls' if os.name == 'nt' else 'clear')

        # Buffer for multi-sentence GSV messages
        gsv_buffer = {} # {talker_id: {msg_num: parsed_data_for_this_msg}}
        last_update_time = time.time()
        update_interval = 0.5 # seconds between terminal updates

        while True:
            line = ser.readline().decode('ascii', errors='ignore').strip()
            if line:
                parsed_data = parse_gsv_sentence(line)

                if parsed_data:
                    talker_id, total_msgs, msg_num, total_sats_in_view, satellites = parsed_data

                    if talker_id in satellite_data:
                        # Store the current message's satellite data in the buffer
                        if talker_id not in gsv_buffer:
                            gsv_buffer[talker_id] = {}
                        gsv_buffer[talker_id][msg_num] = {'total_sats_in_view': total_sats_in_view, 'satellites': satellites}

                        # Check if all messages for this talker_id have been received
                        if len(gsv_buffer[talker_id]) == total_msgs:
                            # Consolidate data from all messages for this constellation
                            current_constellation_sats = {}
                            for msg_part in gsv_buffer[talker_id].values():
                                for sat_info in msg_part['satellites']:
                                    current_constellation_sats[sat_info['prn']] = sat_info

                            # Update the main satellite_data dictionary
                            satellite_data[talker_id]['total_sats_in_view'] = total_sats_in_view
                            satellite_data[talker_id]['satellites'] = current_constellation_sats
                            gsv_buffer[talker_id] = {} # Clear buffer for next set

            # Update display periodically
            if time.time() - last_update_time > update_interval:
                display_satellite_data()
                last_update_time = time.time()

    except serial.SerialException as e:
        print(f"Error opening or communicating with serial port: {e}")
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        if ser and ser.is_open:
            ser.close()
            print("Serial port closed.")

if __name__ == '__main__':
    main()
