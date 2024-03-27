# kasa_smart_plug_ascom_daemon
ASCOM-Remote hub for Kasa smart switches
  
### Get the released Windows executable here:    
   https://github.com/rkinnett/kasa_smart_plug_ascom_daemon/releases
  
  Syntax:  
    start_server
  
  Compiled with pyinstaller:  
	  py -3 -m PyInstaller --noconfirm --onefile --console --name "start_server" --icon "power_button.ico" "start_server.py" --clean
  
  
### Or run from python:  
  Requires python-kasa:  
    pip install python-kasa  
  
  Syntax:  
    python start_server.py