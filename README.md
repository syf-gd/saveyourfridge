#SaveYourFridge

SaveYourFridge 2018

## Installation



##Sensor data transmission

###Python code
this_sensor_battery=get_sensors_py_battery()
this_sensor_temp=get_sensors_mp_temp()
raw = bytearray(struct.pack("f", this_sensor_battery)+struct.pack("f", this_sensor_temp))

###Sifgox backend
Device type->PYCOM_Devkit_1->Edit->Custom configuration

battery::float:32:little-endian temp::float:32:little-endian

###Output in Sigfox backend
Device->Device id->Messages->Message with "battery" and "temp" printed

Hint: Battery as default data should be put in front of all other data. With the battery voltage we can control an escalation process to warn the user from backend side at a later point of time.
