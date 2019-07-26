# Dan McGinn, Tufts CEEO
# Run with python3

from http.server import BaseHTTPRequestHandler, HTTPServer # package for Webserver
from urllib.parse import unquote # package for decoding UTF-8
import getpass, sys, socket, os, webbrowser
from time import sleep
# Packages for Root Drive Commands
import gatt
import threading
import time,termios,tty,sys
import datetime

connected = False
pageContent = open('RootWebserver.html').read()%(str(False),'0','')+open('styleSheet.html').read()
rate = 0 # Set rate
sensorData = ''

def setPageContent():
    global pageContent, rate, sensorData
    pageContent = open('RootWebserver.html').read()%(str(connected),str(rate),sensorData)+open('styleSheet.html').read()
    return pageContent, rate, sensorData

def changeTurnRate(NewTurnRate):
   global rate
   rate = NewTurnRate
   return rate

def connectRoot():
    global manager, connected, thread
    manager = BluetoothDeviceManager(adapter_name = 'hci0')
    manager.start_discovery(service_uuids=[root_identifier_uuid])
    thread = threading.Thread(target = manager.run)
    thread.start()
    while manager.robot is None:
        pass
    connected = True
    return  manager, connected, thread

def disconnectRoot():
    global manager, connected, thread
    manager.stop()
    manager.robot.disconnect()
    print("Disconnected")
    connected = False
    thread.join()
    return  manager, connected, thread

# Get IP Address
ip_address = '';
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8",80))
ip_address = s.getsockname()[0]
s.close()

# Set host port
host_port = 8000

# BLE UUID's
root_identifier_uuid = '48c5d828-ac2a-442d-97a3-0c9822b04979'
uart_service_uuid = '6e400001-b5a3-f393-e0a9-e50e24dcca9e'
tx_characteristic_uuid = '6e400002-b5a3-f393-e0a9-e50e24dcca9e' # Write
rx_characteristic_uuid = '6e400003-b5a3-f393-e0a9-e50e24dcca9e' # Notify

class BluetoothDeviceManager(gatt.DeviceManager):
    robot = None # root robot device

    def device_discovered(self, device):
        print("[%s] Discovered: %s" % (device.mac_address, device.alias()))
        self.stop_discovery() # Stop searching
        self.robot = RootDevice(mac_address=device.mac_address, manager=self)
        self.robot.connect()

class RootDevice(gatt.Device):
    def connect_succeeded(self):
        super().connect_succeeded()
        print("[%s] Connected" % (self.mac_address))

    def connect_failed(self, error):
        super().connect_failed(error)
        print("[%s] Connection failed: %s" % (self.mac_address, str(error)))

    def disconnect_succeeded(self):
        super().disconnect_succeeded()
        print("[%s] Disconnected" % (self.mac_address))

    def services_resolved(self):
        super().services_resolved()
        print("[%s] Resolved services" % (self.mac_address))

        self.uart_service = next(
            s for s in self.services
            if s.uuid == uart_service_uuid)

        self.tx_characteristic = next(
            c for c in self.uart_service.characteristics
            if c.uuid == tx_characteristic_uuid)

        self.rx_characteristic = next(
            c for c in self.uart_service.characteristics
            if c.uuid == rx_characteristic_uuid)

        self.rx_characteristic.enable_notifications() # listen to RX messages

    def characteristic_value_updated(self, characteristic, value):
        global sensorData
        message = []
        type = ""
        for byte in value:
            message.append(byte)
#        print ("Messages from Root:")
        if message[0] == 4: 
            type = "Color Sensor"; 
            sensorData = sensorData + str(datetime.datetime.now().time()) + ': Color Sensor Triggered<br>'
        if message[0] == 12: 
            type = "Bumper"; 
            sensorData = sensorData + str(datetime.datetime.now().time()) + ': Bumper Triggered<br>'
        if message[0] == 13: 
            type = "Light Sensor"; 
            sensorData = sensorData + str(datetime.datetime.now().time()) + ': Light Sensor Triggered<br>'
        if message[0] == 17: 
            type = "Touch Sensor"; 
            sensorData = sensorData + str(datetime.datetime.now().time()) + ': Touch Sensor Triggered<br>'
        if message[0] == 20: 
            type = "Cliff Sensor"; 
            sensorData = sensorData + str(datetime.datetime.now().time()) + ': Cliff Sensor Triggered<br>'

        print(type, message)
        # MyServer().do_POST() # Find a way to call MyServer.do_POST to post everytime a sensor is triggered
        return sensorData

    def drive_forward(self):
        self.tx_characteristic.write_value([0x01, 0x04, 0x00, 0x00, 0x00, 0x00, 0x64, 0x00, 0x00, 0x00, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xD1])

    def drive_left(self):
        self.tx_characteristic.write_value([0x01, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x8A])

    def drive_right(self):
        self.tx_characteristic.write_value([0x01, 0x04, 0x00, 0x00, 0x00, 0x00, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x25])

    def stop(self):
        self.tx_characteristic.write_value([0x01, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x7E])

    def drive_backwards(self):
        self.tx_characteristic.write_value([0x01, 0x04, 0x00, 0xFF, 0xFF, 0xFF, 0x9C, 0xFF, 0xFF, 0xFF, 0x9C, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x71])

    def pen_up(self):
        self.tx_characteristic.write_value([0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    def pen_down(self):
        self.tx_characteristic.write_value([0x02, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    def turn_rate(self, rate):
        left = 0
        right = 0
        if rate >= 0:
            left = rate
        if rate < 0:
            right = -1*rate
        leftbytes = left.to_bytes(4,byteorder='big',signed=True)  # need to convert to byte string
        rightbytes = right.to_bytes(4,byteorder='big',signed=True)
        # note that we're not dynamically calculating the CRC at the end, so just leaving it 0 (unchecked)
        self.tx_characteristic.write_value([0x01, 0x04, 0x00, leftbytes[0], leftbytes[1], leftbytes[2], leftbytes[3], rightbytes[0], rightbytes[1], rightbytes[2], rightbytes[3], 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0])

    def steer(self, left, right):
        leftbytes = left.to_bytes(4,byteorder='big',signed=True)  # need to convert to byte string
        rightbytes = right.to_bytes(4,byteorder='big',signed=True)
        # note that we're not dynamically calculating the CRC at the end, so just leaving it 0 (unchecked)
        self.tx_characteristic.write_value([0x01, 0x04, 0x00, leftbytes[0], leftbytes[1], leftbytes[2], leftbytes[3], rightbytes[0], rightbytes[1], rightbytes[2], rightbytes[3], 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0])

# Webserver
class MyServer(BaseHTTPRequestHandler):

    def do_HEAD(self,pageContent):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def _redirect(self, path):
        self.send_response(303)
        self.send_header('Content-type', 'text/html')
        self.send_header('Location', path)
        self.end_headers()

    def do_GET(self):
        global pageContent
        setPageContent()
        self.do_HEAD(pageContent)
        self.wfile.write(pageContent.encode("utf-8"))

    def do_POST(self):
        global pageContent, manager, connected, thread, rate, sensorData
        angle = 0
        content_length = int(self.headers['Content-Length'])  # Get the size of data
        post_data = self.rfile.read(content_length).decode('utf-8')  # Get the data
        print(post_data)
        if 'Connect' in post_data:
            connectRoot()
        if 'Fwd' in post_data:
            if connected is True:
                print ("Drive forward")
                manager.robot.drive_forward()
                rate = 0
        if 'Left' in post_data:
            if connected is True:
                print ("Drive left")
                manager.robot.drive_left()
                rate = 0
        if 'Right' in post_data:
            if connected is True:
                print ("Drive right")
                manager.robot.drive_right()
                rate = 0
        if 'Bkwd' in post_data:
            if connected is True:
                print ("Drive backwards")
                manager.robot.drive_backwards()
                rate = 0
        if 'Stop' in post_data:
            if connected is True:
                print ("Stop")
                manager.robot.stop()
                rate = 0
        if 'Rate' in post_data:
            if connected is True:
                rate = int(post_data.split("=")[1])
                changeTurnRate(rate)
                print ("Turning ", rate)
                manager.robot.turn_rate(rate)
        if 'PenUp' in post_data:
            if connected is True:
                print ("PenUp")
                manager.robot.pen_up()
        if 'PenDown' in post_data:
            if connected is True:
                print ("PenDown")
                manager.robot.pen_down()
        if 'Disconnect' in post_data:
            if connected is True:
                disconnectRoot()
        setPageContent()
        self._redirect('/')  # Redirect back to the root url
        return pageContent, manager, connected, thread, rate, sensorData

# Create Webserver
if __name__ == '__main__':
    http_server = HTTPServer((ip_address, host_port), MyServer)
    print("Server Starts - %s:%s" % (ip_address, host_port))
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        disconnectRoot()
        http_server.server_close()
        print("\n-------------------EXIT-------------------")
