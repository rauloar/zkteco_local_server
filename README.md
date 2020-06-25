## Zkteco Local Puller

### About
This application works in only Local Area Network. 

It pulls attendance logs from device and push it to server.

### Configuration
You can change configurations by editing *config.json* file.
```json
{
  "PUSH_URL": "http://zkteco.test/push",
  "PUSH_KEY": "1ce649f57584f70d62387b65dba6601974a3f888",
  "PUSH_FREQUENCY": 1,
  "DEVICES": [
    {
      "ip": "192.168.0.2",
      "port": 4370,
      "timeout": 30,
      "clear_from_device_on_fetch": false
    }
  ]
}
```
PUSH_URL and PUSH_KEY is for pushing attendance to server. (Required)

PUSH_FREQUENCY is frequency of pulling attendance from device (in minute).(Required)

DEVICES is an array of local devices.
```json
{
    "ip": "192.168.0.2",
    "port": 4370,
    "timeout": 30,
    "clear_from_device_on_fetch": false
}
```
*ip* - is the IP Address of device. (Required)

*port* - is the TCP port number of device. (Optional, Default : 4370)

*timeout* - timeout in second (Optional, Default : 30)

*clear_from_device_on_fetch* - is a flag. If set *true* application will erase attendances from device after fetching.


### Build
To build this application. Install requirements and run ```python setup.py build```. Executeable file can be found at /output directory.


### Author
Md. Hazzaz Bin Faiz


### Owner
Smart Software Ltd.
