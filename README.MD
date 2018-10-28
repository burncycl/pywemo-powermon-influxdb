## 2018/09 BuRnCycL

This simple script uses Netdisco to discover uPnP devices on a network for a given the device name 'Power', which you 
specify when setting up your WeMo Insight device on your phone. It will then query the device at a one second 
interval and insert miliwatts data into InfluxDB.

This is a proof-of-concept, and so I have not modularized nor removed hard-coded parameters.

Additional functionality available, like binary switching on and off of the device, left commented out.
