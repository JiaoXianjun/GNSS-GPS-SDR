import serial
import time
import curses
from datetime import datetime

# NMEA system prefix to GNSS label
SYSTEM_LABELS = {
    '$GP': 'GPS',
    '$GA': 'Galileo',
    '$GL': 'GLONASS',
    '$GB': 'Beidou',
    '$BD': 'Beidou'  # Some modules use $BD instead of $GB for Beidou
}

# Satellite data: system -> {PRN: SNR}
satellite_data = {
    'GPS': {},
    'Galileo': {},
    'GLONASS': {},
    'Beidou': {}
}

# Fix info and time data
fix_info = {
    'utc_time': '',
    'local_time': '',
    'hdop': '',
    'vdop': '',
    'pdop': ''
}

def parse_gsv(fields, system):
    """Parse GSV message and return list of (PRN, SNR) tuples."""
    sats = []
    try:
        for i in range(4, len(fields) - 4, 4):
            prn = fields[i]
            snr = fields[i+3] if fields[i+3] != '' else '0'
            sats.append((prn, snr))
    except (IndexError, ValueError):
        pass
    return sats

def parse_gga(fields):
    """Parse GGA message for UTC time."""
    try:
        utc_raw = fields[1]
        if utc_raw and len(utc_raw) >= 6:
            hour = int(utc_raw[0:2])
            minute = int(utc_raw[2:4])
            second = int(utc_raw[4:6])
            utc_time = datetime.utcnow().replace(hour=hour, minute=minute, second=second)
            fix_info['utc_time'] = utc_time.strftime('%H:%M:%S')
            fix_info['local_time'] = datetime.now().strftime('%H:%M:%S')
    except Exception:
        pass

def parse_gsa(fields):
    """Parse GSA message for DOP info."""
    try:
        fix_info['pdop'] = fields[15]
        fix_info['hdop'] = fields[16]
        fix_info['vdop'] = fields[17].split('*')[0]
    except IndexError:
        pass

def display(stdscr, ser):
    curses.curs_set(0)
    stdscr.nodelay(True)

    while True:
        try:
            line = ser.readline().decode('ascii', errors='ignore').strip()
            if not line.startswith('$'):
                continue

            fields = line.split(',')
            prefix = line[0:3]
            system = SYSTEM_LABELS.get(prefix, None)

            if 'GSV' in line:
                sats = parse_gsv(fields, system)
                if system and sats:
                    for prn, snr in sats:
                        satellite_data[system][prn] = snr

            elif 'GGA' in line:
                parse_gga(fields)

            elif 'GSA' in line:
                parse_gsa(fields)

            # Clear and update screen
            stdscr.erase()
            stdscr.addstr(0, 2, "GNSS Monitor", curses.A_BOLD | curses.A_UNDERLINE)

            row = 2
            for sys_name in satellite_data:
                stdscr.addstr(row, 2, f"{sys_name} Satellites:", curses.A_BOLD)
                row += 1

                valid_prns = []
                for prn in satellite_data[sys_name]:
                    try:
                        valid_prns.append((int(prn), prn))
                    except ValueError:
                        continue  # Skip non-numeric PRNs

                for _, prn in sorted(valid_prns):
                    snr = satellite_data[sys_name][prn]
                    stdscr.addstr(row, 4, f"PRN: {prn: <4}  SNR: {snr: >3} dBHz")
                    row += 1

                row += 1

            # Time Info
            stdscr.addstr(row, 2, "Time Info:", curses.A_BOLD)
            row += 1
            stdscr.addstr(row, 4, f"UTC Time:   {fix_info.get('utc_time', '')}")
            row += 1
            stdscr.addstr(row, 4, f"Local Time: {fix_info.get('local_time', '')}")
            row += 2

            # Accuracy Info
            stdscr.addstr(row, 2, "Fix Accuracy:", curses.A_BOLD)
            row += 1
            stdscr.addstr(
                row,
                4,
                f"PDOP: {fix_info.get('pdop', '')}  HDOP: {fix_info.get('hdop', '')}  VDOP: {fix_info.get('vdop', '')}"
            )

            stdscr.refresh()
            time.sleep(0.1)

        except KeyboardInterrupt:
            break
        except Exception as e:
            stdscr.addstr(0, 2, f"Error: {e}")
            stdscr.refresh()
            time.sleep(1)

def main():
    port = '/dev/ttyACM1'  # Update this to match your GNSS module's device path
    baudrate = 115200
    try:
        with serial.Serial(port, baudrate, timeout=1) as ser:
            curses.wrapper(display, ser)
    except serial.SerialException as e:
        print(f"Serial error: {e}")

if __name__ == "__main__":
    main()
