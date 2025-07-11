import serial
import time
import os
import re

# ANSI escape codes for terminal manipulation
# \033[2J clears the entire screen
# \033[H moves the cursor to the home position (top-left)
CLEAR_SCREEN = "\033[2J"
MOVE_CURSOR_HOME = "\033[H"

def clear_and_reset_cursor():
    """Clears the terminal screen and moves the cursor to the top-left."""
    # Using os.system('clear') for initial clear and when outputting to a new terminal
    # For continuous updates within the same terminal session, printing ANSI codes is faster
    os.system('cls' if os.name == 'nt' else 'clear') # Initial clear for cross-platform compatibility
    print(MOVE_CURSOR_HOME, end="") # Move cursor to home after clearing

def parse_nmea_checksum(line):
    """
    Parses an NMEA sentence and validates its checksum.
    Returns the data part of the sentence (excluding '$' and '*checksum')
    if the checksum is valid, otherwise returns None.
    """
    # NMEA sentences are structured as: $COMMAND,data1,data2,...*checksum
    if '*' not in line:
        return None # No checksum found in the line

    parts = line.strip().split('*')
    data_part = parts[0] # Everything from '$' up to '*'
    checksum_str = parts[1] # The checksum value as a hex string

    try:
        # Calculate XOR checksum for all characters between '$' and '*'
        calculated_checksum = 0
        for char in data_part[1:]: # Start from the character after '$'
            calculated_checksum ^= ord(char)
        
        # Compare calculated checksum with the one from the NMEA sentence
        if int(checksum_str, 16) == calculated_checksum:
            return data_part # Checksum matches, return the data part
        else:
            # Checksum mismatch, often due to corrupted data
            # print(f"DEBUG: Checksum mismatch for: {line.strip()} (Calculated: {calculated_checksum:02X}, Expected: {checksum_str})")
            return None
    except ValueError:
        # Handle cases where the checksum string is not valid hexadecimal
        # print(f"DEBUG: Invalid checksum format: {line.strip()}")
        return None
    except IndexError:
        # Handle cases where the line might be malformed after splitting by '*'
        # print(f"DEBUG: Malformed line after checksum split: {line.strip()}")
        return None

def main():
    # Serial port configuration
    port = '/dev/ttyUSB0'
    baudrate = 115200
    timeout = 1 # Read timeout in seconds

    # Data structures to store parsed satellite information
    # beidou_sats: Dictionary to store individual satellite data, keyed by PRN
    beidou_sats = {}
    # total_beidou_sats_in_view: Stores the total count of satellites reported in the GSV message
    total_beidou_sats_in_view = 0
    # total_gsv_msgs: Total number of $BDGSV messages expected for a complete update cycle
    total_gsv_msgs = 0
    # current_gsv_msg_num: Current message number in the sequence
    current_gsv_msg_num = 0

    try:
        # Open the serial port
        ser = serial.Serial(port, baudrate, timeout=timeout)
        print(f"Connected to {port} at {baudrate} baud. Press Ctrl+C to exit.")
        
        clear_and_reset_cursor() # Perform an initial clear and reset

        while True:
            # Read a line from the serial port
            # decode('ascii', errors='ignore') handles potential non-ASCII characters
            line = ser.readline().decode('ascii', errors='ignore').strip()
            
            if not line:
                continue # Skip empty lines

            # Validate checksum and get the data part of the NMEA sentence
            data_part = parse_nmea_checksum(line)
            if data_part is None:
                continue # Skip lines with invalid checksums or malformed structure

            # Process only messages that start with '$BD'
            if data_part.startswith('$BD'):
                parts = data_part.split(',')
                msg_type = parts[0] # e.g., '$BDGSV', '$BDGSA'

                if msg_type == '$BDGSV':
                    # Example $BDGSV sentence structure:
                    # $BDGSV,total_msgs,msg_num,num_sats_in_view,sat_id_1,elevation_1,azimuth_1,SNR_1,...*checksum
                    try:
                        # Extract the total number of messages in this GSV sequence
                        total_gsv_msgs = int(parts[1])
                        # Extract the current message number in this GSV sequence
                        current_gsv_msg_num = int(parts[2])
                        # Extract the total number of satellites in view for the entire constellation
                        total_beidou_sats_in_view = int(parts[3])

                        # If this is the first message of a new GSV sequence (msg_num is 1),
                        # clear any previously collected satellite data to start fresh.
                        if current_gsv_msg_num == 1:
                            beidou_sats = {}

                        # Parse satellite data from the current $BDGSV sentence.
                        # Each sentence can contain data for up to 4 satellites.
                        # The fields repeat: sat_id, elevation, azimuth, SNR.
                        # We start parsing from index 4 (after num_sats_in_view)
                        # and increment by 4 for each satellite.
                        for i in range(4, len(parts) - 1, 4):
                            # Ensure there are enough fields for a complete satellite entry (sat_id, elev, azim, SNR)
                            if len(parts) > i + 3:
                                sat_id = parts[i]
                                elevation = parts[i+1]
                                azimuth = parts[i+2]
                                snr = parts[i+3]
                                
                                # Store satellite data. Use 'N/A' if a field is empty.
                                if sat_id: # Only add if satellite ID is present
                                    beidou_sats[sat_id] = {
                                        'elevation': elevation if elevation else 'N/A',
                                        'azimuth': azimuth if azimuth else 'N/A',
                                        'SNR': snr if snr else 'N/A'
                                    }
                            else:
                                # Break the loop if there aren't enough remaining fields
                                # for another full satellite entry.
                                break

                        # If this is the last message in the current $BDGSV sequence,
                        # it means we have collected all available satellite data.
                        # Now, update the terminal display.
                        if current_gsv_msg_num == total_gsv_msgs:
                            # Move cursor to home and clear the screen for a fresh update
                            print(MOVE_CURSOR_HOME + CLEAR_SCREEN, end="")
                            
                            print(f"--- Beidou GNSS Satellite Information ---")
                            print(f"Total Beidou Satellites in View: {total_beidou_sats_in_view}")
                            print("-" * 55) # Separator for readability
                            print(f"{'PRN':<5} {'SNR (dB)':<10} {'Elevation (deg)':<15} {'Azimuth (deg)':<15}")
                            print("-" * 55)

                            if beidou_sats:
                                # Sort satellites by PRN for a consistent and readable display
                                # Convert PRN to int for sorting, handle non-digit PRNs gracefully
                                sorted_sats = sorted(beidou_sats.items(), 
                                                     key=lambda item: int(item[0]) if item[0].isdigit() else float('inf'))
                                for sat_id, data in sorted_sats:
                                    print(f"{sat_id:<5} {data['SNR']:<10} {data['elevation']:<15} {data['azimuth']:<15}")
                            else:
                                print("No Beidou satellite data received yet or no satellites in view.")
                            
                            print("-" * 55) # Another separator
                            print(f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                            
                            # Flush stdout to ensure the output is immediately displayed in the terminal
                            os.sys.stdout.flush() 

                    except ValueError as e:
                        # Catch errors during integer conversion (e.g., if a field is not a number)
                        # print(f"DEBUG: Error parsing $BDGSV message data: {line.strip()} - {e}")
                        continue
                    except IndexError as e:
                        # Catch errors if the message is incomplete or malformed (e.g., missing fields)
                        # print(f"DEBUG: Incomplete $BDGSV message: {line.strip()} - {e}")
                        continue
                # Messages like $GPTXT are implicitly ignored because we only process '$BD' messages.
                # Other '$BD' messages (e.g., $BDGSA) are also ignored as per requirements.
            # else:
                # This block can be uncommented for debugging to see what non-$BD messages are being skipped
                # print(f"DEBUG: Ignoring non-$BD message: {line.strip()}")

    except serial.SerialException as e:
        print(f"\nError opening serial port {port}: {e}")
        print("Please ensure:")
        print("1. The GNSS module is connected to /dev/ttyUSB0.")
        print("2. You have read/write permissions for /dev/ttyUSB0.")
        print("   (You might need to add your user to the 'dialout' group: sudo usermod -a -G dialout $USER && newgrp dialout)")
    except KeyboardInterrupt:
        print("\nExiting script due to user interruption (Ctrl+C).")
    finally:
        # Ensure the serial port is closed when the script exits
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial port closed.")

if __name__ == "__main__":
    main()
