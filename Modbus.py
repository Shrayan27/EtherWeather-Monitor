import socket
import time
import csv
import struct
import sys
from datetime import datetime

def calculate_crc(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return [crc & 0xFF, (crc >> 8) & 0xFF]

class RawWeatherStation:

    def __init__(self, host="192.168.1.200", port=4196, address=1):
        self.address = address
        self.host = host
        self.port = port
        self.sock = None
        
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(3)
            self.sock.connect((self.host, self.port))
            print(f"Connected to {self.host}:{self.port}")
        except Exception as e:
            print(f"\n[!] ERROR: Could not connect to {self.host}:{self.port}")
            print(f"    Reason: {e}")
            print("    Check:")
            print("    1. RS485-to-ETH device is powered and Ethernet cable is plugged in")
            print("    2. IP address and port are correct in VirCom")
            print("    3. Transfer Protocol in VirCom is set to None (Transparent)")
            print("    4. Your PC is in the same network segment as the device")
            raise e

    def close(self):
        if self.sock:
            try:    
                self.sock.close()
                print(f"Connection to {self.host}:{self.port} closed.")
            except Exception as e:
                pass

    def send_command(self, command):
        crc = calculate_crc(command)
        full_cmd = command + crc
        print("TX:", ' '.join(f"{b:02X}" for b in full_cmd))

        try:
            self.sock.sendall(bytearray(full_cmd))
            time.sleep(0.1)
 
            response = b""
            self.sock.settimeout(2)
            while True:
                try:
                    chunk = self.sock.recv(300)
                    if not chunk:
                        break
                    response += chunk
                    if len(response) >= 200:
                        break
                except socket.timeout:
                    break
 
            print("Length:", len(response))
            rx_hex = ' '.join(f"{b:02X}" for b in response)
            print("RX:", rx_hex)
            return response
 
        except Exception as e:
            print(f"[TCP] Send/Receive error: {e}")
            # Try to reconnect once
            try:
                print("[TCP] Attempting reconnect...")
                self.sock.close()
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(3)
                self.sock.connect((self.host, self.port))
                print("[TCP] Reconnected successfully.")
            except Exception as re:
                print(f"[TCP] Reconnect failed: {re}")
            return b""

    def change_address_full_sequence(self, new_address):
        try:
            print("\n--- ADDRESS CHANGE START ---")
            # STEP 1
            enter_cmd = b'>*\r\n'
            self.sock.sendall(enter_cmd)
            time.sleep(0.5)
            resp = self.sock.recv(100)
            print("Config Mode Response:", resp)
            if b"CONFIGURE MODE" not in resp:
                print("Failed entering config mode")
                return False

            # STEP 2
            id_cmd = f'>ID {new_address}\r\n'.encode()
            self.sock.sendall(id_cmd)
            time.sleep(0.5)
            resp = self.sock.recv(100)
            print("Set Address Response:", resp)
            if b"CMD IS SET" not in resp:
                print("Address not accepted")
                return False

            # STEP 3
            exit_cmd = b'>!\r\n'
            self.sock.sendall(exit_cmd)
            time.sleep(1)
            print(f"Address changed to {new_address}")
            self.address = new_address
            return True
        except Exception as e:
            print("Address Change Error:", e)
            return False

    def parse_data(self, response):
        def align_frame(resp):
            for i in range(len(resp) - 1):
                if resp[i] == self.address and resp[i+1] == 0x03:
                    return resp[i:]
            return None

        response = align_frame(response)
        if not response:
            print("Frame not aligned (Sync lost)")
            return None

        byte_count = response[2]
        print("Byte count:", byte_count)
        
        data_bytes = response[3:3+byte_count]

        def get_u16(i):
            return data_bytes[i*2] << 8 | data_bytes[i*2+1]

        def get_float(i):
            if (i+1)*2 + 1 >= len(data_bytes):
                return 0.0
            b = bytes([
                data_bytes[i*2 + 2],
                data_bytes[i*2 + 3],
                data_bytes[i*2],
                data_bytes[i*2 + 1]
            ])
            return struct.unpack('>f', b)[0]

        wind_direction = get_u16(1)
        wind_speed = get_float(2)
        temperature = get_float(4)
        humidity = get_float(6)
        pressure = get_float(8)

        print("\n[FINAL CORRECT DATA]")
        print(f"Wind Direction : {wind_direction} deg")
        print(f"Wind Speed     : {wind_speed:.2f} m/s")
        print(f"Temperature    : {temperature:.2f} °C")
        print(f"Humidity       : {humidity:.2f} %")
        print(f"Barometric Pressure       : {pressure:.2f} hPa")

        return {
            "temperature": temperature,
            "humidity": humidity,
            "pressure": pressure,
            "wind_speed": wind_speed,
            "wind_direction": wind_direction
        }
        
    def _signed(self, val):
        if val > 32767:
            return val - 65536
        return val

class CSVLogger:
    def __init__(self, filename="weather.csv"):
        self.filename = filename
        self.init_file()
    
    def init_file(self):
        try:
            with open(self.filename, "x", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Timestamp",
                    "Temperature (C)",
                    "Humidity (%)",
                    "BarometricPressure (hPa)",
                    "Wind Speed (m/s)",
                    "Wind Direction (deg)"
                ])
        except FileExistsError:
            pass
    
    def log(self, data):
        try:
            with open(self.filename, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    f"{data['temperature']:.2f}",
                    f"{data['humidity']:.2f}",
                    f"{data['pressure']:.2f}",
                    f"{data['wind_speed']:.2f}",
                    data["wind_direction"]
                ])
        except PermissionError:
            print("[CSVLogger] File is open in another program — row skipped.")
        except Exception as e:
            print(f"[CSVLogger] Write error: {e}")

def main():
    station = None
    try:
        # Initialize station
        station = RawWeatherStation(host="192.168.1.200", port=4196, address=1)
        logger = CSVLogger()
        command = [0x01, 0x03, 0x00, 0x00, 0x00, 0x60]

        print("Starting data retrieval loop. Press Ctrl+C to exit.")
        while True:
            try:
                response = station.send_command(command)

                if response:
                    data = station.parse_data(response)
                    if data:
                        logger.log(data)
                        print(f"Logged Data: {data}")
                time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping script...")
                break
            except Exception as e:
                print(f"Communication Error: {e}")
                break
                
    except Exception as e:
        print(f"Unexpected Error: {e}")
        sys.exit(1)
    finally:
        if station:
            station.close()

if __name__ == "__main__":
    main()