# Kasa Smart Plug ASCOM-Remote Virtual Hub
*Virtual hub and ASCOM-Remote (Alpaca) server for Kasa smart switches.*

This ASCOM-Remote server program automatically detects all available Kasa smart switching devices on a local network, then acts as a communication relay between the discovered switches and ASCOM-client astronomy software.
* All Kasa smart switch devices must be already connected to your local network via instructions provided by Kasa.  It's a good idea to name each switch according to what you plug into it, e.g. "telescope", "lamp", "warning light", "flat panel", etc.
* This Kasa ASCOM-Remote server program can run on the same computer as ASCOM-Remote client software or on a different computer on the same local network.
* The *client* computer (running astronomy software) must have both the [ASCOM platform](https://ascom-standards.org/Downloads/Index.htm) and [ASCOM-Remote](https://github.com/ASCOMInitiative/ASCOMRemote/releases) installed.
* Once the Kasa ASCOM-Remote server program has been started, it should be discoverable from any ASCOM-Remote client software via the standard "ASCOM Switch Chooser" utility via default Alpaca discovery port.


## Run the released executable (Windows only):
##### Download:
<https://github.com/rkinnett/kasa_smart_plug_ascom_daemon/releases/download/v0/kasa_ascom_server.exe>
* Start the server by either double-clicking the .exe file or by invoking it by command line from inside Windows Command Prompt.
* Syntax as below.

##### Examples:  
	kasa_ascom_server.exe  
	kasa_ascom_server.exe -a localhost -p 11111
  
## Or run from python3 (platform agnostic):
##### Requires:
	pip install python-kasa
  
##### Download project code:
	git clone https://github.com/rkinnett/kasa_smart_plug_ascom_daemon.git 
  
##### Syntax:  
	python3 start_server.py  [-a server_address (optional]  [-p port (optional)]  
		default server address is 0.0.0.0  (accessibe through host computer local IP address) 
		default control port is 8000  
  
##### Examples:  
	python3 start_server.py  
	python3 start_server.py -a localhost  
	python3 start_server.py -a 127.0.0.1 -p 8000  

## Supported Hardware:
Any of the devices supported by the python-kasa library should work:  
<https://python-kasa.readthedocs.io/en/latest/SUPPORTED.html>  
* Tested with HS103 single-outlet plugs and an HS300 smart power strip.  
* Buy Kasa smart plugs on [amazon](https://www.amazon.com/s?k=kasa+smart+plug)
