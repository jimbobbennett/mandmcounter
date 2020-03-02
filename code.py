import board
import busio
import digitalio
import time
import json
from connection import Connection
from secrets import secrets

import adafruit_vc0706
import requests as requests

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)

connection = Connection()
wifi_manager = connection.connect(spi, True)

# Create a serial connection for the VC0706 connection, speed is auto-detected.
uart = busio.UART(board.TX, board.RX, baudrate=115200, timeout=0.25)

print("uart created")

# Setup VC0706 camera
vc0706 = adafruit_vc0706.VC0706(uart)

# Print the version string from the camera.
print('VC0706 version:')
print(vc0706.version)

# Set the baud rate to 115200 for fastest transfer (its the max speed)
vc0706.baudrate = 115200

# Set the image size.
vc0706.image_size = adafruit_vc0706.IMAGE_SIZE_320x240 # Or set IMAGE_SIZE_320x240 or
                                                       # IMAGE_SIZE_160x120
# Note you can also read the property and compare against those values to
# see the current size:
size = vc0706.image_size
if size == adafruit_vc0706.IMAGE_SIZE_640x480:
    print('Using 640x480 size image.')
elif size == adafruit_vc0706.IMAGE_SIZE_320x240:
    print('Using 320x240 size image.')
elif size == adafruit_vc0706.IMAGE_SIZE_160x120:
    print('Using 160x120 size image.')

# Take a picture.
print('Taking a picture in 3 seconds...')
time.sleep(3)
print('SNAP!')
if not vc0706.take_picture():
    raise RuntimeError('Failed to take picture!')

# Print size of picture in bytes.
frame_length = vc0706.frame_length
print('Picture size (bytes): {}'.format(frame_length))

buffer = bytearray(0)

wcount = 0
while frame_length > 0:
    # Compute how much data is left to read as the lesser of remaining bytes
    # or the copy buffer size (32 bytes at a time).  Buffer size MUST be
    # a multiple of 4 and under 100.  Stick with 32!
    to_read = min(frame_length, 32)
    copy_buffer = bytearray(to_read)
    # Read picture data into the copy buffer.
    if vc0706.read_picture_into(copy_buffer) == 0:
        raise RuntimeError('Failed to read picture frame data!')

    buffer = buffer + copy_buffer

    frame_length -= 32
    # Print a dot every 2k bytes to show progress.
    wcount += 1
    if wcount >= 64:
        print('.', end='')
        wcount = 0

headers={
            'Content-Type': 'application/octet-stream',
            'Prediction-Key': secrets['prediction_key']
        }

retry = 0
r = None

while retry < 10:
    try:
        print("Trying to send...")
        r = requests.post(secrets['prediction_endpoint'], data=buffer, headers=headers)
        break
    except RuntimeError as e:
        print("Could not send data, retrying after 5 seconds: ",e)
        retry = retry + 1
        time.sleep(5)
        continue

result_text = r.text

print(result_text)
results = json.loads(result_text)
predictions = results['predictions']
count = sum(map(lambda x : x['probability'] > 0.7, predictions))
print("Counted", count, "M&Ms")
