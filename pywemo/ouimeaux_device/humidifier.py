"""
Representation of a WeMo Humidifier device
"""

from .switch import Switch
from xml.etree import cElementTree as et
from pywemo.ouimeaux_device.api.xsd.device import quote_xml

import sys
if sys.version_info[0] < 3:
    class IntEnum(object):
        pass
else:
    from enum import IntEnum

# These enums were derived from the
# Humidifier.deviceevent.GetAttributeList()
# service call.
# Thus these names/values were not chosen randomly and the numbers have meaning.
class FanMode(IntEnum):
    Off = 0 # Fan and device turned off
    Minimum = 1
    Low = 2
    Medium = 3
    High = 4
    Maximum = 5

FAN_MODE_NAMES = {
    FanMode.Off: "Off",
    FanMode.Minimum: "Minimum",
    FanMode.Low: "Low",
    FanMode.Medium: "Medium",
    FanMode.High: "High",
    FanMode.Maximum: "Maximum",
}

DESIRED_HUMIDITY = IntEnum(
    value='desired_humidity',
    names=[
        ('45', 0),
        ('50', 1),
        ('55', 2),
        ('60', 3),
        ('100', 4), # "Always On" mode
    ]
)

DESIRED_HUMIDITY_NAMES = {
    DESIRED_HUMIDITY['45']: "45",
    DESIRED_HUMIDITY['50']: "50",
    DESIRED_HUMIDITY['55']: "55",
    DESIRED_HUMIDITY['60']: "60",
    DESIRED_HUMIDITY['100']: "100",
}

class WaterLevel(IntEnum):
    Empty = 0
    Low = 1
    Good = 2

WATER_LEVEL_NAMES = {
    WaterLevel.Empty: "Empty",
    WaterLevel.Low: "Low",
    WaterLevel.Good: "Good",
}

def attribute_xml_to_dict(xml_blob):
    """
    Returns attribute values as a dict of key value pairs.
    """

    xml_blob = "<attributes>" + xml_blob + "</attributes>"
    xml_blob = xml_blob.replace("&gt;", ">")
    xml_blob = xml_blob.replace("&lt;", "<")

    result = {}

    attributes = et.fromstring(xml_blob)

    result["water_level"] = int(2)

    for attribute in attributes:
        if attribute[0].text == "FanMode":
            try:
                result["fan_mode"] = int(attribute[1].text)
            except ValueError:
                pass
        elif attribute[0].text == "DesiredHumidity":
            try:
                result["desired_humidity"] = int(attribute[1].text)
            except ValueError:
                pass
        elif attribute[0].text == "CurrentHumidity":
            try:
                result["current_humidity"] = float(attribute[1].text)
            except ValueError:
                pass
        elif attribute[0].text == "NoWater" and attribute[1].text == "1":
            try:
                result["water_level"] = int(0)
            except ValueError:
                pass
        elif attribute[0].text == "WaterAdvise" and attribute[1].text == "1":
            try:
                result["water_level"] = int(1)
            except ValueError:
                pass
        elif attribute[0].text == "FilterLife":
            try:
                result["filter_life"] = float(round((float(attribute[1].text) \
                    / float(60480)) * float(100), 2))
            except ValueError:
                pass
        elif attribute[0].text == "ExpiredFilterTime":
            try:
                result["filter_expired"] = bool(int(attribute[1].text))
            except ValueError:
                pass
    return result


class Humidifier(Switch):
    """
    Representation of a WeMo Humidifier device
    """

    def __init__(self, *args, **kwargs):
        """
        Initialization method
        """

        Switch.__init__(self, *args, **kwargs)
        self._attributes = {}
        self.update_attributes()

    def __repr__(self):
        """
        Device's string representation (name)
        """

        return '<WeMo Humidifier "{name}">'.format(name=self.name)

    def update_attributes(self):
        """
        Request state from device
        """

        resp = self.deviceevent.GetAttributes().get('attributeList')
        self._attributes = attribute_xml_to_dict(resp)
        self._state = self.fan_mode

    def subscription_update(self, _type, _params):
        """
        Handle reports from device
        """

        if _type == "attributeList":
            self._attributes.update(attribute_xml_to_dict(_params))
            self._state = self.fan_mode

            return True

        return Switch.subscription_update(self, _type, _params)

    @property
    def fan_mode(self):
        """
        Returns the FanMode setting (as an int index of the IntEnum).
        """

        return self._attributes.get('fan_mode')

    @property
    def fan_mode_string(self):
        """
        Returns the FanMode setting as a string
		(Off, Low, Medium, High, Maximum).
        """

        return FAN_MODE_NAMES.get(self.fan_mode, "Unknown")

    @property
    def desired_humidity(self):
        """
        Returns the desired humidity setting (as an int index of the IntEnum).
        """

        return self._attributes.get('desired_humidity')

    @property
    def desired_humidity_percent(self):
        """
        Returns the desired humidity setting in percent (string).
        """

        return DESIRED_HUMIDITY_NAMES.get(self.desired_humidity, "Unknown")

    @property
    def current_humidity_percent(self):
        """
        Returns the current observed relative humidity in percent (float).
        """

        return self._attributes.get('current_humidity')

    @property
    def water_level(self):
        """
        Returns 0 if water level is Empty, 1 if Low, and 2 if Good.
        """

        return self._attributes.get('water_level')

    @property
    def water_level_string(self):
        """
        Returns Empty, Low, or Good depending on the water level.
        """

        return WATER_LEVEL_NAMES.get(self.water_level, "Unknown")

    @property
    def filter_life_percent(self):
        """
        Returns the percentage (float) of filter life remaining.
        """

        return self._attributes.get('filter_life')

    @property
    def filter_expired(self):
        """
        Returns 0 if filter is OK, and 1 if it needs to be changed.
        """

        return self._attributes.get('filter_expired')

    def get_state(self, force_update=False):
        """
        Returns 0 if off and 1 if on.
        """

        # The base implementation using GetBinaryState
        # doesn't work for Humidifier (always returns 0)
        # so use fan mode instead.
        if force_update or self._state is None:
            self.update_attributes()

        # Consider the Humidifier to be "on" if it's not off.
        return int(self._state != FanMode.Off)

    def set_state(self, state):
        """
        Set the fan mode of this device (as int index of the FanMode IntEnum).
        Provided for compatibility with the Switch base class.
        """

        self.set_fan_mode(state)

    def set_fan_mode(self, fan_mode):
        """
        Set the fan mode of this device (as int index of the FanMode IntEnum).
        Provided for compatibility with the Switch base class.
        """

        # Send the attribute list to the device
        self.deviceevent.SetAttributes(attributeList= \
            quote_xml("<attribute><name>FanMode</name><value>" + \
                str(int(fan_mode)) + "</value></attribute>"))

        # Refresh the device state
        self.get_state(True)

    def set_humidity(self, desired_humidity):
        """
        Set the desired humidity of this device (as int index of the IntEnum).
        """

        # Send the attribute list to the device
        self.deviceevent.SetAttributes(attributeList= \
            quote_xml("<attribute><name>DesiredHumidity</name><value>" + \
                str(int(desired_humidity)) + "</value></attribute>"))

        # Refresh the device state
        self.get_state(True)

    def set_fan_mode_and_humidity(self, fan_mode, desired_humidity):
        """
        Set the desired humidity and fan mode of this device
        (as int index of their respective IntEnums).
        """

        # Send the attribute list to the device
        self.deviceevent.SetAttributes(attributeList= \
            quote_xml("<attribute><name>FanMode</name><value>" + \
                str(int(fan_mode)) + "</value></attribute>" + \
                "<attribute><name>DesiredHumidity</name><value>" + \
                str(int(desired_humidity)) + "</value></attribute>"))

        # Refresh the device state
        self.get_state(True)