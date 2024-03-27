# kasa_smart_plug_ascom_daemon
ASCOM-Remote server for Kasa smart switches.

The created ASCOM-Remote server should be discoverable through ASCOM-remote driver selector.

The daemon produces verbose screen print outputs which can generally be ignored unless troubleshooting.

  
### Run from python:
  Requires python-kasa:  
    pip install python-kasa  
  
  Syntax:  
    python start_server.py  [server_address (optional]  [control port (optional)]
 
      default server address is "localhost" (127.0.0.1)
        you may wish to use address 0.0.0.0 if you want the server to be accessible from other computers.
      
      default control port is 8000

  Examples:
    python start_server.py
    python start_server.py localhost
    python start_server.py 0.0.0.0 8000