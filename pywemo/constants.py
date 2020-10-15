import os

MAX_RETRIES = int(os.environ.get('MAX_RETRIES', '1'))
DEVICE_ACTION_TIMEOUT = int(os.environ.get('DEVICE_REQUEST_TIMEOUT', '2'))
