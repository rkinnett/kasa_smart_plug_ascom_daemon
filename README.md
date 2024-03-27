# kasa_smart_plug_ascom_daemon
*ASCOM-Remote server for Kasa smart switches.*

The created ASCOM-Remote server should be discoverable through ASCOM-remote driver selector.  The daemon produces verbose screen print outputs which can generally be ignored unless troubleshooting.

### Run the released executable (Windows only):
##### Download:
	https://github.com/rkinnett/kasa_smart_plug_ascom_daemon/releases/download/v0/start-server.exe

  Start the server by either double-clicking the .exe file or by invoking it by command line from inside Windows Command Prompt.  Then you should be able to connect astronomy software (e.g. NINA) to it via the standard ASCOM driver selector tool.  
  
### Or run from python (platform agnostic):
##### Requires:
	 pip install python-kasa  
  
##### Syntax:  
	python start_server.py  [server_address (optional]  [control port (optional)]  
		default server address is "localhost" (127.0.0.1)  
		default control port is 8000  
Use address 0.0.0.0 to make the server accessible from other computers on your local network.

#####  Examples:  
    python start_server.py  
    python start_server.py localhost  
    python start_server.py 0.0.0.0 8000  
