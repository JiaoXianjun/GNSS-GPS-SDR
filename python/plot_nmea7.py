import serial
import time
import curses
from collections import defaultdict

PORT = "/dev/ttyACM0"
BAUDRATE = 115200

# System and PRN mapping
SYSTEM_PREFIXES = {
    "$GPGSV": "GPS",
    "$GLGSV": "GLONASS",
    "$BDGSV": "BeiDou",
    "$GAGSV": "Galileo",
    "$QZGSV": "QZSS",
    "$GNGSV": "Mixed"
}

SYSTEM_BANDS = {
    "GPS": "L1/L2/L5",
    "BeiDou": "B1/B2",
    "Galileo": "E1/E5",
    "GLONASS": "L1/L2",
    "QZSS": "L1/L2",
    "SBAS": "L1",
    "Unknown": "N/A"
}

# Helper Functions

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

def system_to_band(system):
    return SYSTEM_BANDS.get(system, "N/A")

def safe_addstr(stdscr, row, col, text, width):
    if 0 <= row < curses.LINES:
        try:
            stdscr.addstr(row, col, text.ljust(width)[:width-1])
        except curses.error:
            pass

def parse_gsv_block(lines):
    sats = []
    for parts in lines:
        for i in range(4, len(parts) - 4, 4):
            try:
                prn = parts[i]
                elev = parts[i+1]
                azim = parts[i+2]
                snr = parts[i+3].split('*')[0]
                system = prn_to_system(prn)
                sats.append({
                    'prn': prn,
                    'elevation': elev,
                    'azimuth': azim,
                    'snr': snr,
                    'system': system,
                    'band': system_to_band(system)
                })
            except:
                continue
    return sats

def parse_gga(parts):
    if len(parts) < 15:
        return {}
    try:
        lat = float(parts[2])
        lat_dir = parts[3]
        lon = float(parts[4])
        lon_dir = parts[5]
        hdop = parts[8]
        fix_type = parts[6]
        alt = parts[9]
        lat_dec = (int(lat / 100) + (lat % 100) / 60) * (-1 if lat_dir == 'S' else 1)
        lon_dec = (int(lon / 100) + (lon % 100) / 60) * (-1 if lon_dir == 'W' else 1)
        return {
            'lat': f"{lat_dec:.6f}",
            'lon': f"{lon_dec:.6f}",
            'hdop': hdop,
            'fix_type': fix_type,
            'altitude': alt
        }
    except:
        return {}

def parse_gst(parts):
    if len(parts) < 9:
        return {}
    try:
        rms = parts[6]
        sigma_lat = parts[7]
        sigma_lon = parts[8].split('*')[0]
        return {
            'rms': rms,
            'sigma_lat': sigma_lat,
            'sigma_lon': sigma_lon
        }
    except:
        return {}

def parse_gsa(parts):
    if len(parts) < 18:
        return {}
    try:
        pdop = parts[15]
        hdop = parts[16]
        vdop = parts[17].split('*')[0]
        return {
            'pdop': pdop,
            'vdop': vdop,
            'hdop_gsa': hdop
        }
    except:
        return {}

def parse_vtg(parts):
    if len(parts) < 9:
        return {}
    try:
        speed_kmh = parts[7]
        return {
            'speed_kmh': speed_kmh
        }
    except:
        return {}

def parse_rmc(parts):
    if len(parts) < 10:
        return {}
    try:
        course = parts[8]
        return {
            'course': course
        }
    except:
        return {}

# Main Monitor Function

def monitor(stdscr):
    stdscr.nodelay(True)
    curses.curs_set(0)
    max_y, max_x = stdscr.getmaxyx()

    try:
        ser = serial.Serial(PORT, BAUDRATE, timeout=1)
    except Exception as e:
        stdscr.addstr(0, 0, f"Cannot open {PORT}: {e}")
        stdscr.refresh()
        time.sleep(3)
        return

    gsv_blocks = defaultdict(list)
    gsv_expected = {}
    satellites = {}
    last_update = time.time()
    gga_data = {}
    gst_data = {}
    gsa_data = {}
    vtg_data = {}
    rmc_data = {}

    while True:
        try:
            line = ser.readline().decode('ascii', errors='ignore').strip()
            if not line.startswith('$'):
                continue

            parts = line.split(',')
            talker = parts[0][:6]

            if 'GSV' in talker:
                try:
                    total_msgs = int(parts[1])
                    msg_num = int(parts[2])
                except:
                    continue
                gsv_blocks[talker].append(parts)
                gsv_expected[talker] = total_msgs
                if len(gsv_blocks[talker]) == total_msgs:
                    sats = parse_gsv_block(gsv_blocks[talker])
                    for sat in sats:
                        satellites[sat['prn']] = sat
                    gsv_blocks[talker].clear()
                    gsv_expected[talker] = 0
                    last_update = time.time()

            elif 'GGA' in talker:
                gga_data = parse_gga(parts)
            elif 'GST' in talker:
                gst_data = parse_gst(parts)
            elif 'GSA' in talker:
                gsa_data = parse_gsa(parts)
            elif 'VTG' in talker:
                vtg_data = parse_vtg(parts)
            elif 'RMC' in talker:
                rmc_data = parse_rmc(parts)

            # Display
            stdscr.erase()
            safe_addstr(stdscr, 0, 0, f"GNSS Monitor on {PORT} @ {BAUDRATE} baud", max_x)
            safe_addstr(stdscr, 1, 0, "=" * (max_x - 1), max_x)

            row = 2
            safe_addstr(
                stdscr,
                row,
                0,
                f"Fix Type: {gga_data.get('fix_type', 'N/A')}  HDOP: {gga_data.get('hdop', 'N/A')}  Lat: {gga_data.get('lat', 'N/A')}  Lon: {gga_data.get('lon', 'N/A')}  Alt: {gga_data.get('altitude', 'N/A')} m",
                max_x
            )
            row += 1
            safe_addstr(
                stdscr,
                row,
                0,
                f"Accuracy RMS: {gst_data.get('rms', 'N/A')}  Sigma Lat: {gst_data.get('sigma_lat', 'N/A')}  Sigma Lon: {gst_data.get('sigma_lon', 'N/A')}  PDOP: {gsa_data.get('pdop', 'N/A')}  VDOP: {gsa_data.get('vdop', 'N/A')}",
                max_x
            )
            row += 1
            safe_addstr(
                stdscr,
                row,
                0,
                f"Speed: {vtg_data.get('speed_kmh', 'N/A')} km/h  Course: {rmc_data.get('course', 'N/A')}°",
                max_x
            )
            row += 2

            safe_addstr(stdscr, row, 0, f"{'PRN':<5} {'SYS':<8} {'Band':<8} {'Elev':<6} {'Azim':<6} {'SNR':<6}", max_x)
            row += 1
            safe_addstr(stdscr, row, 0, "-" * (max_x - 1), max_x)
            row += 1

            for prn in sorted(satellites.keys()):
                sat = satellites[prn]
                line = f"{sat['prn']:<5} {sat['system']:<8} {sat['band']:<8} {sat['elevation']:<6} {sat['azimuth']:<6} {sat['snr']:<6}"
                safe_addstr(stdscr, row, 0, line, max_x)
                row += 1
                if row >= max_y - 10:
                    break

            info_lines = [
                "HDOP: Horizontal Dilution of Precision",
                "PDOP: Position Dilution of Precision (3D)",
                "VDOP: Vertical Dilution of Precision",
                "Fix Type: 1=No Fix, 2=2D, 3=3D",
                "GGA: Fix position, satellites, altitude",
                "GSA: Active satellites + DOP",
                "GSV: Satellites in view",
                "RMC: Position + Speed + Date/Time",
                "VTG: Track over ground",
                "GST: Position error estimates"
            ]
            for i, line in enumerate(info_lines):
                if max_y - len(info_lines) + i < max_y:
                    safe_addstr(stdscr, max_y - len(info_lines) + i, 0, line, max_x)

            stdscr.refresh()
            time.sleep(0.3)

        except KeyboardInterrupt:
            break
        except Exception:
            continue

if __name__ == '__main__':
    curses.wrapper(monitor)
