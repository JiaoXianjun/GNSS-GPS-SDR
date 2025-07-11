import serial
import time
import curses
from collections import defaultdict

PORT = "/dev/ttyUSB0"
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
    txt_messages = []

    while True:
        try:
            line = ser.readline().decode('ascii', errors='ignore').strip()
            if not line.startswith('$'):
                continue

            parts = line.split(',')
            talker = parts[0][:6]

            # GSV Processing with grouping
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

            elif 'TXT' in talker or 'GPTXT' in talker:
                msg = line.split(',', 3)[-1]
                txt_messages.append(msg)
                if len(txt_messages) > 10:
                    txt_messages.pop(0)

            # Display
            stdscr.erase()
            safe_addstr(stdscr, 0, 0, f"GNSS Monitor on {PORT} @ {BAUDRATE} baud", max_x)
            safe_addstr(stdscr, 1, 0, "=" * (max_x - 1), max_x)

            row = 2
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

            # TXT message box
            row += 1
            safe_addstr(stdscr, row, 0, "Receiver Messages:", max_x)
            row += 1
            for txt in txt_messages[-3:]:
                safe_addstr(stdscr, row, 0, f"- {txt}", max_x)
                row += 1

            # Help text
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
                "GST: Position error estimates",
                "TXT: Receiver internal messages"
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
