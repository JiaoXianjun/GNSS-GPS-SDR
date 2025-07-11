import serial
import re
import time
import curses
from collections import defaultdict

PORT = "/dev/ttyUSB0"
BAUDRATE = 115200

def parse_gga(line):
    # Example: $GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47
    parts = line.split(',')
    if len(parts) < 15:
        return None

    def dms_to_decimal(dms, direction):
        if not dms or not direction:
            return None
        degrees = int(float(dms) / 100)
        minutes = float(dms) - degrees * 100
        decimal = degrees + minutes / 60
        if direction in ['S', 'W']:
            decimal = -decimal
        return decimal

    return {
        'time': parts[1],
        'lat': dms_to_decimal(parts[2], parts[3]),
        'lon': dms_to_decimal(parts[4], parts[5]),
        'fix_quality': parts[6],
        'num_satellites': parts[7],
        'hdop': parts[8],
        'altitude': parts[9]
    }

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

def parse_gsv(line):
    system_map = {
        "$GPGSV": "GPS",
        "$BDGSV": "BeiDou",
        "$GLGSV": "GLONASS",
        "$GAGSV": "Galileo",
        "$QZGSV": "QZSS",
        "$GNGSV": "Mixed"  # Will identify per PRN
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
    for i in range(4, len(parts) - 4, 4):
        if i + 3 >= len(parts):
            break
        prn = parts[i]
        elevation = parts[i + 1]
        azimuth = parts[i + 2]
        snr = parts[i + 3].split('*')[0]  # Remove checksum

        if not prn:
            continue

        # Determine system per satellite if GNGSV
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
    padded = text.ljust(width)[:width - 1]  # truncate to avoid overflow
    stdscr.addstr(row, col, padded)

def monitor(stdscr):
    stdscr.nodelay(True)
    curses.curs_set(0)

    max_y, max_x = stdscr.getmaxyx()  # ✅ This defines max_y and max_x

    ser = serial.Serial(PORT, BAUDRATE, timeout=1)
    gga_data = {}
    satellites = defaultdict(dict)

    while True:
        try:
            line = ser.readline().decode('ascii', errors='ignore').strip()
            if not line.startswith('$'):
                continue

            if 'GGA' in line:
                data = parse_gga(line)
                if data:
                    gga_data = data

            elif 'GSV' in line:
                sats = parse_gsv(line)
                for sat in sats:
                    satellites[sat['prn']] = sat

            stdscr.clear()
            stdscr.addstr(0, 0, f"Real-Time GNSS Monitor (/dev/ttyUSB0 @ {BAUDRATE} baud)")
            stdscr.addstr(1, 0, "-"*80)

            # Positioning Info
            stdscr.addstr(2, 0, "Fix Time:      " + gga_data.get('time', 'N/A'))
            stdscr.addstr(3, 0, "Latitude:      " + str(gga_data.get('lat', 'N/A')))
            stdscr.addstr(4, 0, "Longitude:     " + str(gga_data.get('lon', 'N/A')))
            stdscr.addstr(5, 0, "Altitude:      " + str(gga_data.get('altitude', 'N/A')) + " m")
            stdscr.addstr(6, 0, "Satellites:    " + str(gga_data.get('num_satellites', 'N/A')))
            stdscr.addstr(7, 0, "HDOP:          " + str(gga_data.get('hdop', 'N/A')))

            # Satellite Info Table
            stdscr.addstr(9, 0, f"{'PRN':<5} {'System':<8} {'Elev(deg)':<10} {'Azim(deg)':<10} {'SNR(dBHz)':<10}")
            stdscr.addstr(10, 0, "-" * 60)
            row = 11
            for prn, sat in sorted(satellites.items()):
                if row >= max_y - 1:
                    break  # Prevent drawing outside screen
                line = f"{prn:<5} {sat['system']:<8} {sat['elevation']:<10} {sat['azimuth']:<10} {sat['snr']:<10}"
                safe_addstr(stdscr, row, 0, line, width=max_x - 1)
                row += 1



            stdscr.refresh()
            time.sleep(0.5)

        except KeyboardInterrupt:
            break

    ser.close()

if __name__ == '__main__':
    curses.wrapper(monitor)
