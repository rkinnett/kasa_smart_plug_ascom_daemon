"""""""""""""""""""""""""""""""""""""""""""""""""""""""""
Kasa Switch ASCOM-Remote Server
R. Kinnett, 2024
https://github.com/rkinnett/kasa_smart_plug_ascom_daemon
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""
import argparse
import asyncio
from alpaca import Alpaca
import threading
import time


from kasa import SmartPlug as KasaSmartPlug, Discover as KasaDiscover, SmartDeviceException as KasaSmartDeviceException

import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

supported_switch_types = ("kasa", )

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

class KasaSwitch():
    device = None
    state = None
    state_str = None
    
    def __init__(self, switch_address=None, switch_type=None, switch_name=None, kasa_device=None ):
        self.address = switch_address
        self.name = switch_name
        self.type = switch_type
        self.device = kasa_device
        
        if kasa_device is not None:
            self.address = kasa_device.host
            self.name    = kasa_device.alias
            self.type    = kasa_device.model
        
        if switch_address is not None:
            self.device = KasaSmartPlug(switch_address)
            
    async def check(self):
        assert self.device is not None, 'device not defined'
        await self.device.update()
        self.state = self.device.is_on
        self.state_str = "on" if self.device.is_on else "off"
        return self.state
    
    async def on(self):
        assert self.device is not None, 'device not defined'
        print('turning switch on')
        await self.device.turn_on()
            
    async def off(self):
        assert self.device is not None, 'device not defined'
        print('turning switch off')
        await self.device.turn_off()

    async def setState(self, state):
        assert self.device is not None, 'device not defined'
        print('setting switch state %s' % str(state))
        if state:
            await self.on()
        else:
            await self.off()
            
    

class SwitchManager():
    version = 1
    switches = []
    num_switches = 0
    
    discovery_loop_period = 30
    discovery_loop_busy = False
    discovery_loop_started = False
    
    state_check_loop_period = 2
    state_check_loop_busy = False
    state_check_loop_started = False
        
    def __init__(self, alpaca):
        self.alpaca = alpaca

        self.alpaca_methods = [
            ["GET", "connected",            self.getConnected],
            ["GET", "description",          self.getDescription],
            ["GET", "driverinfo",           self.getDriverInfo],
            ["GET", "driverversion",        self.getDriverVersion],
            ["GET", "interfaceversion",     self.getInterfaceVersion],
            ["GET", "name",                 self.getName],
            ["GET", "supportedactions",     self.getSupportedActions],
            ["GET", "maxswitch",            self.getMaxSwitch],
            ["GET", "canwrite",             self.getCanWrite],
            ["GET", "getswitch",            self.getSwitch],
            ["GET", "getswitchdescription", self.getSwitchDescription],
            ["GET", "getswitchname",        self.getSwitchName],
            ["GET", "getswitchvalue",       self.getSwitchValue],
            ["GET", "minswitchvalue",       self.getMinSwitchValue],
            ["GET", "maxswitchvalue",       self.getMaxSwitchValue],
            ["GET", "switchstep",           self.getSwitchStep],
            ["PUT", "action",               self.doAction],
            ["PUT", "commandblind",         self.doCommandBlind],
            ["PUT", "commandbool",          self.doCommandBool],
            ["PUT", "commandstring",        self.doCommandString],
            ["PUT", "connected",            self.setConnected],
            ["PUT", "setswitch",            self.setSwitch],
            ["PUT", "setswitchname",        self.setSwitchName],
            ["PUT", "setswitchvalue",       self.setSwitchValue],
        ]

    
    async def discover(self):
        # Discover Kasa Switches:
        self.discovery_loop_busy = True
        print('Discovering kasa smart plugs...')
        discovered_switches = await KasaDiscover.discover()
        discovered_switch_addrs = discovered_switches.keys()
        discovered_switch_names = [device.alias for addr, device in discovered_switches.items()]
        new_switch_list = []
        for switch_idx, switch_name in enumerate(sorted(discovered_switch_names)):
            for addr, device in discovered_switches.items():
                if device.alias == switch_name:
                    print('  Device at address %s:  {name: "%s", type: %s}' % (addr, device.alias, device.model))
                    print('  adding switch addr %s, device ' % addr, device)
                    new_switch_list.append(KasaSwitch(kasa_device = device))            
        self.switches = new_switch_list
        self.num_switches = len(self.switches)
        print('  found %i kasa switches' % self.num_switches)
        self.discovery_loop_busy = False
        
        
    async def check_switches(self):
        self.state_check_loop_busy = True
        for switch_idx, switch in enumerate(self.switches):
            try:
                await switch.check()
                print('  switch %i state: %s' % (switch_idx, switch.state_str))
            except Exception as error:
                print("An exception occurred:", error) # An exception occurred: division by zero
                print('error checking status of switch %i' % switch_idx)
        self.state_check_loop_busy = False
    
    
    async def state_check_loop(self):
        while True:
            if not self.discovery_loop_busy:
                if not self.state_check_loop_busy:
                    print('State check loop updating switch states')
                    self.state_check_loop_busy = True
                    await self.check_switches()
                    self.state_check_loop_busy = False
                else:
                    print('!!!!!! state check busy, skipping')
            time.sleep(self.state_check_loop_period)
    
    
    async def start_state_check_loop(self):
        self.state_check_loop_thread = threading.Thread(target=asyncio.run, args=(self.state_check_loop(),))    
        self.state_check_loop_thread.start()
        self.state_check_loop_started = True
    
    
    async def discovery_loop(self):
        while True:
            if not self.discovery_loop_busy:
                #print('####### discovery loop discovering #######')
                await self.discover()
            else:
                print('!!!!!! discovery busy, skipping')
            time.sleep(self.discovery_loop_period)
            
        
    async def start_discovery_loop(self):
        self.discovery_loop_thread = threading.Thread(target=asyncio.run, args=(self.discovery_loop(),))    
        self.discovery_loop_thread.start()
        self.discovery_loop_started = True


    def getConnected(self, transaction):
        return self.alpaca.nominal_response(transaction, value=self.alpaca.connected)

    def getDescription(self, transaction):
        return self.alpaca.nominal_response(transaction, value="Kasa smart plug daemon")
        
    def getDriverInfo(self, transaction):
        return self.alpaca.nominal_response(transaction, value="Kasa smart plug daemon")
        
    def getDriverVersion(self, transaction):
        return self.alpaca.nominal_response(transaction, value=self.version)
        
    def getInterfaceVersion(self, transaction):
        return self.alpaca.nominal_response(transaction, value=self.alpaca.api.version)

    def getName(self, transaction):
        return self.alpaca.nominal_response(transaction, value="Kasa smart plug daemon")
        
    def getSupportedActions(self, transaction):
        return self.alpaca.nominal_response(transaction, value=[])

    def getMaxSwitch(self, transaction):
        return self.alpaca.nominal_response(transaction, value=self.num_switches)
    
    def getCanWrite(self, transaction):
        return self.alpaca.nominal_response(transaction, value=True)

    def getSwitch(self, transaction):
        try:
            switch_num = int(transaction.params["id"])
        except:
            return self.alpaca.error_response(transaction,
                self.alpaca.api.error_codes['INVALID_VALUE'], 
                'invalid switch id: %i' % switch_num
            )
        try: 
            switch = self.switches[switch_num]
        except IndexError:
            return self.alpaca.error_response(transaction,
                self.alpaca.api.error_codes['INVALID_VALUE'], 
                'invalid switch id: %i' % switch_num
            )
        switch.check()
        return self.alpaca.nominal_response(transaction, value=switch.state)
            
    def getSwitchDescription(self, transaction):
        # Get switch number from params, then get the specified switch
        try:
            switch_num = int(transaction.params["id"])
        except:
            return self.alpaca.error_response(transaction,
                self.alpaca.api.error_codes['INVALID_VALUE'], 
                'invalid switch id: %i' % switch_num
            )
        #print('switch num %i' % switch_num)
        try: 
            switch = self.switches[switch_num]
            #print(switch)
        except IndexError:
            return self.alpaca.error_response(transaction,
                self.alpaca.api.error_codes['INVALID_VALUE'], 
                'invalid switch id: %i' % switch_num
            )
        description = 'Kasa switch type ' + switch.type
        return self.alpaca.nominal_response(transaction, value=description)        

    def getSwitchName(self, transaction):
        #print('getSwitchName')
        #print(transaction.params)
        try:
            switch_num = int(transaction.params["id"])
        except:
            return self.alpaca.error_response(transaction,
                self.alpaca.api.error_codes['INVALID_VALUE'], 
                'invalid switch id: %i' % switch_num
            )
        #print('switch num %i' % switch_num)
        try: 
            switch = self.switches[switch_num]
            #print(switch)
        except IndexError:
            return self.alpaca.error_response(transaction,
                self.alpaca.api.error_codes['INVALID_VALUE'], 
                'invalid switch id: %i' % switch_num
            )
        return self.alpaca.nominal_response(transaction, value=switch.name)

    def getSwitchValue(self, transaction):
        try:
            switch_num = int(transaction.params["id"])
        except:
            return self.alpaca.error_response(transaction,
                self.alpaca.api.error_codes['INVALID_VALUE'], 
                'invalid switch id: %i' % switch_num
            )
        try: 
            switch = self.switches[switch_num]
        except IndexError:
            return self.alpaca.error_response(transaction,
                self.alpaca.api.error_codes['INVALID_VALUE'], 
                'invalid switch id: %i' % switch_num
            )
        time.sleep(0.25)
        switch.check()
        print('Switch state: %s' % str(switch.state))
        value = 1 if switch.state else 0
        return self.alpaca.nominal_response(transaction, value=value)
            
    def getMinSwitchValue(self, transaction):
        return self.alpaca.nominal_response(transaction, value=0)

    def getMaxSwitchValue(self, transaction):
        return self.alpaca.nominal_response(transaction, value=1)

    def getSwitchStep(self, transaction):
        return self.alpaca.nominal_response(transaction, value=1)
        
    def doAction(self, transaction):
        return self.alpaca.not_supported_response(transaction)
        
    def doCommandBlind(self, transaction):
        return self.alpaca.not_supported_response(transaction)
        
    def doCommandBool(self, transaction):
        return self.alpaca.not_supported_response(transaction)
        
    def doCommandString(self, transaction):
        return self.alpaca.not_supported_response(transaction)

    def setConnected(self, transaction):
        self.alpaca.connected = transaction.params["connected"] in ("true", "True")
        # don't send a response if client is disconnecting
        if self.alpaca.connected:        
            print('\n\n>>>>>>>>>>>>>>> CLIENT CONNECTED >>>>>>>>>>>>>>\n\n')
        else:
            print('\n\nXXXXXXXXXXXXXXX CLIENT DISCONNECTED XXXXXXXXXXXXXXXX\n\n')        
        return self.alpaca.nominal_response(transaction)

    def setSwitch(self, transaction):
        try:
            switch_num = int(transaction.params["id"])
        except:
            return self.alpaca.error_response(transaction,
                self.alpaca.api.error_codes['INVALID_VALUE'], 
                'invalid switch id: %i' % switch_num
            )
        try: 
            switch = self.switches[switch_num]
        except IndexError:
            return self.alpaca.error_response(transaction,
                self.alpaca.api.error_codes['INVALID_VALUE'], 
                'invalid switch id: %i' % switch_num
            )
        try:
            state = transaction.params["state"] in ("true", "True")
        except:
            return self.alpaca.error_response(transaction,
                self.alpaca.api.error_codes['INVALID_VALUE'], 
                'unable to parse commanded state'
            )
        try:
            asyncio.run(switch.setState(state))
        except:
            return self.alpaca.error_response(transaction,
                self.alpaca.api.error_codes['VALUE_NOT_SET'], 
                'unable to set switch state'
            )
        return self.alpaca.nominal_response(transaction)

            
    def setSwitchName(self, transaction):
        return self.alpaca.not_supported_response(transaction)

    def setSwitchValue(self, transaction):
        try:
            switch_num = int(transaction.params["id"])
        except:
            return self.alpaca.error_response(transaction,
                self.alpaca.api.error_codes['INVALID_VALUE'], 
                'invalid switch id: %i' % switch_num
            )
        try: 
            switch = self.switches[switch_num]
        except IndexError:
            return self.alpaca.error_response(transaction,
                self.alpaca.api.error_codes['INVALID_VALUE'], 
                'invalid switch id: %i' % switch_num
            )
        try:
            state = transaction.params["value"] == '1'
        except:
            return self.alpaca.error_response(transaction,
                self.alpaca.api.error_codes['INVALID_VALUE'], 
                'unable to parse commanded value'
            )
        try:
            print('setting state: %s' % str(state))
            asyncio.run(switch.setState(state))
        except:
            return self.alpaca.error_response(transaction,
                self.alpaca.api.error_codes['VALUE_NOT_SET'], 
                'unable to set switch state'
            )
        try:
            print('checking switch state')
            asyncio.run(switch.check())
        except:
            return self.alpaca.error_response(transaction,
                self.alpaca.api.error_codes['VALUE_NOT_SET'], 
                'unable to get switch state'
            )
        return self.alpaca.nominal_response(transaction)    


def delay_print(outstr, delay=0.01):
  for char in outstr:
    print(char, end='', flush=True)
    time.sleep(delay)


async def main():

    print("""



    +-------------------------------------------------------------------------+
    |                  Kasa Smart Plug ASCOM-Remote Daemon                    |  
    |                           R. Kinnett, 2024                              | 
    |        https://github.com/rkinnett/kasa_smart_plug_ascom_daemon         |
    +-------------------------------------------------------------------------+
        
    """)
    
    print('\n')
    delay_print('>>>>>>>>>>>>>>>   INITIALIZING...  >>>>>>>>>>>>>>\n')
    time.sleep(0.5)
    delay_print('         This will take a few seconds...',0.05)
    print('\n\n')
    time.sleep(1)

    # Parse command line arguments:
    parser = argparse.ArgumentParser(description="Run a simple HTTP server")
    parser.add_argument(
        "-a",
        "--address",
        type=str,
        default="localhost",
        help="Specify the IP address on which the server listens",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8000,
        help="Specify the port on which the server listens",
    )
    args = parser.parse_args()
    #print('Specified arguments:',args)
    #print('Kasa ASCOM-Remote server address: %s, port: %i' % (args.address, args.port))
    alpaca_device_control_port = args.port
    
    alpaca = Alpaca(
        device_type = "Switch", 
        server_address = args.address, 
        control_port = args.port
    )
    
    switch_manager = SwitchManager(alpaca)
    await switch_manager.discover()
    
    alpaca.bindMethods(switch_manager.alpaca_methods)
    alpaca.start()
    delay_print("\n\n\n >>>>>>>>>>>>  Kasa Alpaca server started  <<<<<<<<<<<<< \n")
    time.sleep(1)
    delay_print(      "         Clients may now discover and connect...         \n",0.02)
    print('\n\n')
    time.sleep(1)
    delay_print('!!!  To stop the Kasa ASCOM-remote server, press ctrl-c or close this window.\n',0.02)
    time.sleep(1)
    delay_print('Status information that follows may be ignored unless troubleshooting.\n',0.02)
    print('\n\n')
    time.sleep(2)

    print('Starting switch state auto-rediscover and state check loops...')
    await switch_manager.start_discovery_loop()
    await switch_manager.start_state_check_loop()


asyncio.run(main())

