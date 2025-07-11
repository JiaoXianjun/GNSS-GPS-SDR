import serial
import time
import random
import curses

PORT = "/dev/ttyUSB0"
# PORT = "/dev/ttyACM0"
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

def system_to_band(system):
    bands = {
        "GPS": "L1/L2/L5",
        "BeiDou": "B1/B2",
        "Galileo": "E1/E5",
        "GLONASS": "L1/L2",
        "QZSS": "L1/L2",
        "SBAS": "L1",
        "Unknown": "N/A"
    }
    return bands.get(system, "N/A")

def parse_gga(parts):
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

def parse_rmc(parts):
    if len(parts) < 12:
        return None
    return {
        'time': parts[1],
        'status': parts[2],  # A=valid, V=invalid
        'lat': parts[3],
        'lat_dir': parts[4],
        'lon': parts[5],
        'lon_dir': parts[6],
        'speed_knots': parts[7],
        'course_deg': parts[8],
        'date': parts[9],
        'mag_var': parts[10] if len(parts) > 10 else None,
        'mag_var_dir': parts[11] if len(parts) > 11 else None,
    }

def parse_vtg(parts):
    if len(parts) < 9:
        return None
    return {
        'course_true': parts[1],
        'course_magnetic': parts[3],
        'speed_knots': parts[5],
        'speed_kmh': parts[7]
    }

def parse_gsa(parts):
    if len(parts) < 18:
        return None
    satellites_used = [p for p in parts[3:15] if p != '']
    return {
        'mode': parts[1],         # M=manual, A=automatic
        'fix_type': parts[2],     # 1=No fix, 2=2D, 3=3D
        'satellites_used': satellites_used,
        'pdop': parts[15],
        'hdop': parts[16],
        'vdop': parts[17].split('*')[0] if '*' in parts[17] else parts[17]
    }

def parse_gsv(parts):
    system_map = {
        "$GPGSV": "GPS",
        "$BDGSV": "BeiDou",
        "$GLGSV": "GLONASS",
        "$GAGSV": "Galileo",
        "$QZGSV": "QZSS",
        "$GNGSV": "Mixed"
    }

    line = parts[0]
    system = None
    for prefix in system_map:
        if line.startswith(prefix):
            system = system_map[prefix]
            break

    if len(parts) < 4 or not parts[3].isdigit():
        return []

    sats = []
    for i in range(4, len(parts) - 4, 4):
        if i + 3 >= len(parts):
            break
        prn = parts[i]
        elevation = parts[i + 1]
        azimuth = parts[i + 2]
        snr = parts[i + 3].split('*')[0]

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

def parse_gst(parts):
    if len(parts) < 9:
        return None
    return {
        'rms_deviation': parts[1],
        'std_dev_major': parts[2],
        'std_dev_minor': parts[3],
        'orientation': parts[4],
        'std_dev_lat': parts[5],
        'std_dev_lon': parts[6],
        'std_dev_alt': parts[7].split('*')[0] if '*' in parts[7] else parts[7]
    }

def parse_zda(parts):
    if len(parts) < 7:
        return None
    return {
        'time': parts[1],
        'day': parts[2],
        'month': parts[3],
        'year': parts[4],
        'local_zone_hours': parts[5],
        'local_zone_minutes': parts[6].split('*')[0] if '*' in parts[6] else parts[6]
    }

def safe_addstr(stdscr, row, col, text, width):
    if row < 0 or row >= curses.LINES:
        return
    padded = text.ljust(width)[:width-1]
    try:
        stdscr.addstr(row, col, padded)
    except curses.error:
        pass

def monitor(stdscr):
    stdscr.nodelay(True)
    curses.curs_set(0)

    try:
        ser = serial.Serial(PORT, BAUDRATE, timeout=1)
    except serial.SerialException as e:
        stdscr.addstr(0, 0, f"Error opening serial port {PORT}: {e}")
        stdscr.refresh()
        stdscr.getkey()
        return

    gga_data = {}
    gsa_data = {}
    rmc_data = {}
    vtg_data = {}
    gst_data = {}
    zda_data = {}
    txt_messages = []
    satellites = {}

    explanation = [
        "=== NMEA & GNSS Info ===",
        "HDOP: Horizontal Dilution of Precision (accuracy of horizontal pos.)",
        "PDOP: Position Dilution of Precision (3D accuracy)",
        "VDOP: Vertical Dilution of Precision (vertical accuracy)",
        "Fix Mode (GSA): M=Manual, A=Automatic",
        "Fix Type (GSA): 1=No Fix, 2=2D Fix, 3=3D Fix",
        "GGA: Fix data including position, satellites, altitude",
        "GSA: DOP and active satellites info",
        "GSV: Satellites in view with signal info",
        "RMC: Recommended Minimum data (time, date, position, speed)",
        "VTG: Track and Ground speed",
        "GST: Estimate of Position Error",
        "ZDA: Date and Time",
        "TXT: Receiver messages"
    ]

    while True:
        try:
            max_y, max_x = stdscr.getmaxyx()
            line = ser.readline().decode('ascii', errors='ignore').strip()
            if not line.startswith('$'):
                continue

            parts = line.split(',')

            if 'GGA' in line:
                data = parse_gga(parts)
                if data:
                    gga_data = data

            elif 'GSA' in line:
                data = parse_gsa(parts)
                if data:
                    gsa_data = data

            elif 'GSV' in line:
                sats = parse_gsv(parts)
                for sat in sats:
                    satellites[sat['prn']] = sat

            elif 'RMC' in line:
                data = parse_rmc(parts)
                if data:
                    rmc_data = data

            elif 'VTG' in line:
                data = parse_vtg(parts)
                if data:
                    vtg_data = data

            elif 'GST' in line:
                data = parse_gst(parts)
                if data:
                    gst_data = data

            elif 'ZDA' in line:
                data = parse_zda(parts)
                if data:
                    zda_data = data

            elif 'TXT' in line:
                msg = line.split(',', 2)[-1]
                txt_messages.append(msg)
                if len(txt_messages) > 20:
                    txt_messages.pop(0)

            stdscr.erase()

            safe_addstr(stdscr, 0, 0, f"Real-Time GNSS Monitor ({PORT} @ {BAUDRATE} baud)", max_x)
            safe_addstr(stdscr, 1, 0, "-" * (max_x - 1), max_x)

            safe_addstr(stdscr, 2, 0, f"Fix Time (GGA):      {gga_data.get('time', 'N/A')}", max_x)
            safe_addstr(stdscr, 3, 0, f"Latitude (GGA):      {gga_data.get('lat', 'N/A')+random.uniform(-73.5, 15.1)}", max_x)
            safe_addstr(stdscr, 4, 0, f"Longitude (GGA):     {gga_data.get('lon', 'N/A')+random.uniform(-13.5, 105.1)}", max_x)
            safe_addstr(stdscr, 5, 0, f"Altitude (GGA):      {gga_data.get('altitude', 'N/A')} m", max_x)
            safe_addstr(stdscr, 6, 0, f"Satellites in Fix:   {gga_data.get('num_satellites', 'N/A')}", max_x)
            safe_addstr(stdscr, 7, 0, f"HDOP (GGA):          {gga_data.get('hdop', 'N/A')}", max_x)

            safe_addstr(stdscr, 8, 0, f"Fix Mode (GSA):      {gsa_data.get('mode', 'N/A')}", max_x)
            safe_addstr(stdscr, 9, 0, f"Fix Type (GSA):      {gsa_data.get('fix_type', 'N/A')}", max_x)
            safe_addstr(stdscr, 10, 0, f"PDOP (GSA):          {gsa_data.get('pdop', 'N/A')}", max_x)
            safe_addstr(stdscr, 11, 0, f"HDOP (GSA):          {gsa_data.get('hdop', 'N/A')}", max_x)
            safe_addstr(stdscr, 12, 0, f"VDOP (GSA):          {gsa_data.get('vdop', 'N/A')}", max_x)

            safe_addstr(stdscr, 13, 0, f"Speed (knots) (VTG): {vtg_data.get('speed_knots', 'N/A')}", max_x)
            safe_addstr(stdscr, 14, 0, f"Speed (km/h) (VTG):  {vtg_data.get('speed_kmh', 'N/A')}", max_x)
            safe_addstr(stdscr, 15, 0, f"Course (deg) (VTG):  {vtg_data.get('course_true', 'N/A')}", max_x)
            safe_addstr(stdscr, 16, 0, f"Date (RMC):          {rmc_data.get('date', 'N/A')}", max_x)

            safe_addstr(stdscr, 17, 0, f"RMS Deviation (GST): {gst_data.get('rms_deviation', 'N/A')}", max_x)
            safe_addstr(stdscr, 18, 0, f"Std Dev Lat (GST):   {gst_data.get('std_dev_lat', 'N/A')}", max_x)
            safe_addstr(stdscr, 19, 0, f"Std Dev Lon (GST):   {gst_data.get('std_dev_lon', 'N/A')}", max_x)
            safe_addstr(stdscr, 20, 0, f"Std Dev Alt (GST):   {gst_data.get('std_dev_alt', 'N/A')}", max_x)

            safe_addstr(stdscr, 21, 0, f"ZDA UTC Time:        {zda_data.get('time', 'N/A')}", max_x)
            safe_addstr(stdscr, 22, 0, f"ZDA Date (DD-MM-YYYY): {zda_data.get('day', 'N/A')}-{zda_data.get('month', 'N/A')}-{zda_data.get('year', 'N/A')}", max_x)

            MAX_TXT_LINES = 3
            txt_display = txt_messages[-MAX_TXT_LINES:]
            safe_addstr(stdscr, 23, 0, f"Receiver Messages (last {MAX_TXT_LINES}):", max_x)
            for i, msg in enumerate(txt_display):
                if 24 + i >= max_y - len(explanation) - 1:
                    break
                safe_addstr(stdscr, 24 + i, 0, f"- {msg}", max_x)

            sat_start_row = 24 + len(txt_display) + 1
            sat_rows_available = max_y - sat_start_row - len(explanation) - 1

            if sat_rows_available > 2:
                safe_addstr(stdscr, sat_start_row, 0, f"{'PRN':<5} {'System':<8} {'Band':<8} {'Elev(deg)':<10} {'Azim(deg)':<10} {'SNR(dBHz)':<10}", max_x)
                safe_addstr(stdscr, sat_start_row + 1, 0, "-" * (max_x - 1), max_x)

                row = sat_start_row + 2
                sats_to_show = list(sorted(satellites.items()))[:sat_rows_available - 2]
                for prn, sat in sats_to_show:
                    band = system_to_band(sat['system'])
                    line = f"{prn:<5} {sat['system']:<8} {band:<8} {sat['elevation']:<10} {sat['azimuth']:<10} {sat['snr']:<10}"
                    safe_addstr(stdscr, row, 0, line, max_x)
                    row += 1

            # Show explanations at bottom
            expl_start = max_y - len(explanation)
            for i, line in enumerate(explanation):
                if expl_start + i < max_y:
                    safe_addstr(stdscr, expl_start + i, 0, line, max_x)

            stdscr.refresh()
            time.sleep(0.5)

        except KeyboardInterrupt:
            break
        except Exception:
            pass

    ser.close()

if __name__ == '__main__':
    curses.wrapper(monitor)
