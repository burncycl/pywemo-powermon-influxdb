#!/usr/bin/env python3

# 2018/06 BuRnCycL
# Python 3 # Dependency on pip3 install netdisco influxdb requests
# Be sure to name your Wemo Insight device something unqiue, so it can be discovered.

import requests, datetime, sys, urllib3
from xml.etree import ElementTree
from time import sleep
from netdisco.discovery import NetworkDiscovery
from influxdb import InfluxDBClient
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) # Supress insecure ssl warnings.


class uPnPDiscovery:
    def __init__(self, targetDeviceName=None):
        try:
            self.netdis = NetworkDiscovery()
            self.netdis.scan()
    
            # Declare variables, not war.
            self.targetDeviceName = targetDeviceName       
            self.targetDevice = {}
            
            print('Scanning Network for Belkin Wemo Insight Target Device Name: {}'.format(self.targetDeviceName))
            self.discover()
            self.netdis.stop()        
        
        except Exception as e:
            print('ERROR - {}'.format(e))
            sys.exit(1)

        
    def getTargetDevice(self):
        return(self.targetDevice)


    def discover(self):        
        try:
            for device in self.netdis.discover():
                #print(dev, netdis.get_info(dev)) # Debugging
                if device == "belkin_wemo": # Discover Belkin Wemo devices
                    for element in self.netdis.get_info(device):
                        if element['model_name'] == "Insight": # Check it's a Wemo Insight model.
                            if element['name'] == self.targetDeviceName: # Check it matches our target name.
                                # Update empty dictionary with our discovered device.
                                self.targetDevice['ip'] = element['host']
                                self.targetDevice['port'] = element['port']
                                print('Found Belkin Wemo Insight Device matching Target Name: {}, IP: {}, Port: {}'.format(element['name'], element['host'], element['port']))
                            else:
                                print('Found Belkin Wemo Insight Device Name: {}, but did not match Target Name: {}. Skipping.'.format(element['name'], self.targetDeviceName))                
                                pass
        
        except Exception as e:
            print('ERROR - {}'.format(e))
            sys.exit(1)


class wemoInsight:
    def __init__(self):
        # Declare variables, not war.
        targetDevice = uPnPDiscovery('Power').getTargetDevice() # Call the above uPnPDsicovery class to find Wemo Insight Devices.
        self.address = targetDevice['ip']
        self.port = targetDevice['port']
        
        try:
            self.client = InfluxDBClient(host='0.0.0.0', port=8086, username='influx', password='assword', ssl=True, verify_ssl=False, database='statsmon')
    
            # Function calls
            # Put these in here if you want to play with other Wemo Insight SOAP Actions, query the device parameters directly, or Insert into InfluxDB only once.
            #self.basicEvent(on=True)
            #self.basicEvent(off=True)
            #self.getParameters()
            #self.queryInsert()
            self.main() # Primary loop
        
        except Exception as e:
            print('ERROR - {}'.format(e))
            sys.exit(1)


    def dateTime(self):
        return(datetime.datetime.now()).isoformat()


    def basicEvent(self, on=False, off=False): # Put this in here if you want to play with other SOAP Actions.
        soapAction = '"urn:Belkin:service:basicevent:1#SetBinaryState"' # Turns wemo insight device on/off, aka "binary state".
        headers = {
            'Content-type': 'text/xml; charset="utf-8"',
            'SOAPACTION': soapAction,
        }

        # Turn wemo on/off
        if on == True:
            state = 1
        elif off == True:
            state = 0

        SOAPXML = '''<?xml version', '"1.0" encoding="utf-8"?>\n
        <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">\n
        <s:Body>\n
        <u:SetBinaryState xmlns:u="urn:Belkin:service:basicevent:1">\n
        <BinaryState>{}</BinaryState>\n
        </u:SetBinaryState>\n
        </s:Body>\n
        </s:Envelope>'''.format(str(state))

        response = requests.post('http://{}:{}/upnp/control/basicevent1'.format(self.address, self.port), headers=headers, data=SOAPXML)
        print(response.text) # Debugging


    def getParameters(self):
        soapAction = '"urn:Belkin:service:insight:1#GetInsightParams"'
        headers = {
            'Content-type': 'text/xml; charset="utf-8"',
            'SOAPACTION': soapAction,
        }

        SOAPXML = '''<?xml version="1.0" encoding="utf-8"?>\n
        <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">\n
        <s:Body>\n
        <u:GetInsightParams xmlns:u="urn:Belkin:service:insight:1">\n
        </u:GetInsightParams>\n
        </s:Body>\n
        </s:Envelope>'''

        response = requests.post('http://{}:{}/upnp/control/insight1'.format(self.address, self.port), headers=headers, data=SOAPXML)
        #print(response.text) # Debugging
        et = ElementTree.fromstring(response.text)
        params = et.find('.//InsightParams').text
        #print(params) # Debugging

        paramsArray = (params.split('|'))

        # All the output parameters
        #print('State: {}'.format(paramsArray[0]))
        #print('Last Change: {}'.format(paramsArray[1]))
        #print('On For: {}s'.format(paramsArray[2]))
        #print('On Today: {}s'.format(paramsArray[3]))
        #print('On Total: {}s'.format(paramsArray[4]))
        #print('Time Period: {}'.format(paramsArray[5]))
        #print('x: {}'.format(paramsArray[6]))
        print('Current Power: {}mW'.format(paramsArray[7]))
        #print('Today Power: {}mW'.format(paramsArray[8]))
        #print('Total Powera: {}mW'.format(paramsArray[9]))
        #print('Power Threshold: {}'.format(paramsArray[10]))
        
        return(paramsArray[7]) # We only care about Current Power.


    # Queries Wemo Insight device for miliwatts and inserts data into InfluxDB. Uses Python requests as opposed to Python InfluxDB client. Sometimes works better. Especially on localhost configurations.
    def influxdb_requests(self):  

        miliwatts = int(self.getParameters())
        url_string = 'http://localhost:8086/write?db=statsmon'
        data_string = 'miliwatts,device=wemo,location=work value={}'.format(miliwatts)

        r = requests.post(url_string, data=data_string)


    def influxdb(self): # Queries Wemo Insight device for miliwatts and inserts data into InfluxDB.

        miliwatts = int(self.getParameters())
        json_body = [
        {
        "measurement": "miliwatts",
        "tags": {
            "device": "wemo",
            "location": "home"
        },
        "time": self.dateTime(),
        "fields": {
            "value": miliwatts
            }
        }
        ]
        #print(json_body) # Debugging
        self.client.write_points(json_body)


    def main(self):
        while True:
            self.influxdb_requests()
            #self.influxdb()
            sleep(1)

wemoInsight()

