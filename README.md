# Kasa Smart Plut ASCOM-Remote Virtual Hub
*ASCOM-Remote vertual hub server for Kasa smart switches.*

This ASCOM-Remote server program automatically detects all available Kasa smart switching devices on a local network, then acts as a communication relay between the discovered switches and ASCOM-client astronomy software.
* All Kasa smart switch devices must be already connected to your local network via instructions provided by Kasa.  It's a good idea to name each switch according to what you plug into it, e.g. "telescope", "lamp", "warning light", "flat panel", etc.
* This Kasa ASCOM-Remote virtual hub program can run on the same computer as the ASCOM-client astronomy software, or on any other computer on the same local network, although firewall restrictions may complicate setup if running on separate machines.
* This Kasa ASCOM-Remote virtual hub program can run in Windows via the provided executable, or can run in Windows or on any platform with python3 installed through the provided python source files, but will require at least one non-core library (python-kasa) to be installed.
* After discovering Kasa switches on your network, this virtual hub program presents itself to a connected ASCOM-Remote client as a single switch "device" comprising of several individually-controllable power outlets.
* The *client* computer (running astronomy software) (not necessarily the same computer as is running this server program) must have both the [ASCOM platform](https://ascom-standards.org/Downloads/Index.htm) and [ASCOM-Remote](https://github.com/ASCOMInitiative/ASCOMRemote/releases) installed.
* Once the Kasa ASCOM-Remote virtual hub program has been started, it should be discoverable from any ASCOM-Remote client software via the standard "ASCOM Switch Chooser" utility via default Alpaca discovery port 


The created ASCOM-Remote server should be discoverable through the driver selector.  The daemon produces verbose screen print outputs which can generally be ignored unless troubleshooting.

## Run the released executable (Windows only):
##### Download:
<https://github.com/rkinnett/kasa_smart_plug_ascom_daemon/releases/download/v0/start-server.exe>

  Start the server by either double-clicking the .exe file or by invoking it by command line from inside Windows Command Prompt.  Then you should be able to connect astronomy software (e.g. NINA) to it via the standard ASCOM driver selector tool.  By default, the server can only be accessed from the same computer that's running it, and can be found on port 8000.  If the ASCOM driver selector does not automatically discover the server, then 
  
## Or run from python (platform agnostic):
##### Requires:
	 pip install python-kasa  
  
##### Syntax:  
	python start_server.py  [-a server_address (optional]  [-p port (optional)]  
		default server address is "localhost" (127.0.0.1)  
		default control port is 8000  
Use address 0.0.0.0 to make the server accessible from other computers on your local network.

#####  Examples:  
    python start_server.py  
    python start_server.py -a localhost  
    python start_server.py -a 0.0.0.0 -p 8000  

## Supported Hardware:
Any of the devices supported by the python-kasa library should work:  
<https://python-kasa.readthedocs.io/en/latest/SUPPORTED.html>  
  
Tested with HS103 single-outlet plugs and an HS300 smart power strip.  

Buy Kasa smart plugs on [amazon](https://www.amazon.com/s?k=kasa+smart+plug)
