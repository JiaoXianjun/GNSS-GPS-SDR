import serial
import time
import curses
from collections import defaultdict

PORT = "/dev/ttyUSB0"
BAUDRATE = 115200

def prn_to_system(prn):
    try:
        prn = int(prn)
        if 1 <= prn <= 32:
            return "GPS"
        elif 33 <= prn <= 64:
            return "SBAS"
        elif 65 <= prn <= 96:
            return "GLONASS"
        elif 120 <= prn <= 158:
            return "Galileo"
        elif 159 <= prn <= 163:
            return "QZSS"
        elif 201 <= prn <= 237:
            return "BeiDou"
        else:
            return "Unknown"
    except ValueError:
        return "Unknown"

def parse_gga(line):
    parts = line.split(',')
    if len(parts) < 15:
        return None

    def dms_to_decimal(dms, direction):
        if not dms or not direction:
            return None
        try:
            degrees = int(float(dms) / 100)
            minutes = float(dms) - degrees * 100
            decimal = degrees + minutes / 60
            if direction in ['S', 'W']:
                decimal = -decimal
            return decimal
        except:
            return None

    return {
        'time': parts[1],
        'lat': dms_to_decimal(parts[2], parts[3]),
        'lon': dms_to_decimal(parts[4], parts[5]),
        'fix_quality': parts[6],
        'num_satellites': parts[7],
        'hdop': parts[8],
        'altitude': parts[9]
    }

def parse_gsv(line):
    system_map = {
        "$GPGSV": "GPS",
        "$BDGSV": "BeiDou",
        "$GLGSV": "GLONASS",
        "$GAGSV": "Galileo",
        "$QZGSV": "QZSS",
        "$GNGSV": "Mixed"
    }

    system = None
    for prefix in system_map:
        if line.startswith(prefix):
            system = system_map[prefix]
            break

    parts = line.split(',')
    if len(parts) < 4 or not parts[3].isdigit():
        return []

    sats = []
    # Satellite data starts at index 4, each satellite uses 4 fields (PRN, elev, azim, SNR)
    for i in range(4, len(parts) - 4, 4):
        if i + 3 >= len(parts):
            break
        prn = parts[i]
        elevation = parts[i + 1]
        azimuth = parts[i + 2]
        snr = parts[i + 3].split('*')[0]  # Remove checksum

        if not prn:
            continue

        sat_system = prn_to_system(prn) if system == "Mixed" else system

        sats.append({
            'prn': prn,
            'elevation': elevation,
            'azimuth': azimuth,
            'snr': snr,
            'system': sat_system
        })

    return sats

def safe_addstr(stdscr, row, col, text, width):
    if row < 0 or row >= curses.LINES:
        return
    padded = text.ljust(width)[:width-1]  # truncate to avoid overflow
    try:
        stdscr.addstr(row, col, padded)
    except curses.error:
        pass  # Ignore errors if writing outside window

def monitor(stdscr):
    stdscr.nodelay(True)
    curses.curs_set(0)
    max_y, max_x = stdscr.getmaxyx()

    try:
        ser = serial.Serial(PORT, BAUDRATE, timeout=1)
    except serial.SerialException as e:
        stdscr.addstr(0, 0, f"Error opening serial port {PORT}: {e}")
        stdscr.refresh()
        stdscr.getkey()
        return

    gga_data = {}
    satellites = {}

    while True:
        try:
            max_y, max_x = stdscr.getmaxyx()  # Update size each loop for resizing
            line = ser.readline().decode('ascii', errors='ignore').strip()
            if not line.startswith('$'):
                continue

            # Parse GGA messages
            if 'GGA' in line:
                data = parse_gga(line)
                if data:
                    gga_data = data

            # Parse GSV messages
            elif 'GSV' in line:
                sats = parse_gsv(line)
                for sat in sats:
                    satellites[sat['prn']] = sat

            stdscr.erase()

            # Header
            safe_addstr(stdscr, 0, 0, f"Real-Time GNSS Monitor ({PORT} @ {BAUDRATE} baud)", max_x)
            safe_addstr(stdscr, 1, 0, "-" * (max_x - 1), max_x)

            # Position info
            safe_addstr(stdscr, 2, 0, f"Fix Time:      {gga_data.get('time', 'N/A')}", max_x)
            safe_addstr(stdscr, 3, 0, f"Latitude:      {gga_data.get('lat', 'N/A')}", max_x)
            safe_addstr(stdscr, 4, 0, f"Longitude:     {gga_data.get('lon', 'N/A')}", max_x)
            safe_addstr(stdscr, 5, 0, f"Altitude:      {gga_data.get('altitude', 'N/A')} m", max_x)
            safe_addstr(stdscr, 6, 0, f"Satellites in Fix: {gga_data.get('num_satellites', 'N/A')}", max_x)
            safe_addstr(stdscr, 7, 0, f"HDOP:          {gga_data.get('hdop', 'N/A')}", max_x)

            # Satellite info table header
            safe_addstr(stdscr, 9, 0, f"{'PRN':<5} {'System':<8} {'Elev(deg)':<10} {'Azim(deg)':<10} {'SNR(dBHz)':<10}", max_x)
            safe_addstr(stdscr, 10, 0, "-" * (max_x - 1), max_x)

            # Display satellites, limiting to terminal height
            row = 11
            for prn, sat in sorted(satellites.items()):
                if row >= max_y - 1:
                    break
                line = f"{prn:<5} {sat['system']:<8} {sat['elevation']:<10} {sat['azimuth']:<10} {sat['snr']:<10}"
                safe_addstr(stdscr, row, 0, line, max_x)
                row += 1

            stdscr.refresh()
            time.sleep(0.5)

        except KeyboardInterrupt:
            break
        except Exception:
            # Catch all unexpected exceptions and continue (could log if needed)
            pass

    ser.close()

if __name__ == '__main__':
    curses.wrapper(monitor)
