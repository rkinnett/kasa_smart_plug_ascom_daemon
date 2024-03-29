"""""""""""""""""""""""""""""""""""""""""""""""""""""""""
Kasa Switch ASCOM-Remote Server
R. Kinnett, 2024
https://github.com/rkinnett/kasa_smart_plug_ascom_daemon
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""
alpaca.py

Devines Alpaca class:
  
    Initialize like:
        alpaca = Alpaca(device_type = "Switch", server_address = address, control_port = port)
    
    Start:
        alpaca.bindMethods(device_manager.alpaca_methods)
        alpaca.start()

    Functions:
        alpaca.bindMethod(self, method_type, method_name, action)
        alpaca.bindMethods(self, methods_list)
        
        alpaca.nominal_response(self, transaction, value=None)
        alpaca.error_response(self, transaction, error_number, error_message)
        alpaca.device_error_response(self, transaction, error_message)
        alpaca.invalid_request_response(self, transaction, error_message)
        alpaca.not_supported_response(self, transaction)
        alpaca.management_response(self, transaction, value)
        

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""


from http.server import HTTPServer, BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import asyncio
import threading
from threading import Thread
import time
import sys
import re
from urllib.parse import parse_qs, urlparse
# for multicast discovery:
from socket import AF_INET6, AF_INET
import socket
import struct
import os



class AlpacaAPI():
    # https://ascom-standards.org/api/

    def __init__(self):
        self.supported_device_types = list(self.methods.keys())
        self.supported_device_types.remove("Common")

    version = 1

    methods = {
        'Common': {
            'PUT': {
                "action":           {"device_type":"str", "device_number":"int", "action":"str", "parameters":"str"},
                "commandblind":     {"device_type":"str", "device_number":"int", "command":"str", "raw":"str"},
                "commandbool":      {"device_type":"str", "device_number":"int", "command":"str", "raw":"str"},
                "commandstring":    {"device_type":"str", "device_number":"int", "command":"str", "raw":"str"},
                "connected":        {"device_type":"str", "device_number":"int", "connected":"bool"},
            },
            'GET': {
                "connected":        {"device_type":"str", "device_number":"int"},
                "description":      {"device_type":"str", "device_number":"int"},
                "driverinfo":       {"device_type":"str", "device_number":"int"},
                "driverversion":    {"device_type":"str", "device_number":"int"},
                "interfaceversion": {"device_type":"str", "device_number":"int"},
                "name":             {"device_type":"str", "device_number":"int"},
                "supportedactions": {"device_type":"str", "device_number":"int"},
            }    
        },
        'Switch': {
            'PUT': {
                "setswitch":            {"device_number":"int", "id":"int", "state":"bool"},    # Sets a switch controller device to the specified state, true or false
                "setswitchname":        {"device_number":"int", "id":"int", "name":"str"},      # Sets a switch device name to the specified value
                "setswitchvalue":       {"device_number":"int", "id":"int", "value":"float"},   # Sets a switch device value to the specified value
            },
            'GET': {
                "maxswitch":            {"device_number":"int"},              # The number of switch devices managed by this driver
                "canwrite":             {"device_number":"int", "id":"int"},  # Indicates whether the specified switch device can be written to
                "getswitch":            {"device_number":"int", "id":"int"},  # Return the state of switch device id as a boolean
                "getswitchdescription": {"device_number":"int", "id":"int"},  # Gets the description of the specified switch device
                "getswitchname":        {"device_number":"int", "id":"int"},  # Gets the name of the specified switch device
                "getswitchvalue":       {"device_number":"int", "id":"int"},  # Gets the value of the specified switch device as a double
                "minswitchvalue":       {"device_number":"int", "id":"int"},  # Gets the minimum value of the specified switch device as a double
                "maxswitchvalue":       {"device_number":"int", "id":"int"},  # Gets the maximum value of the specified switch device as a double
                "switchstep":           {"device_number":"int", "id":"int"},  # Returns the step size that this device supports (the difference between successive values of the device).
            }
        }
    }
    
    error_codes = {
        "SUCCESSFUL_TRANSACTION":               0x0,
        "PROPERTY_OR_METHOD_NOT_IMPLEMENTED":   0x400,
        "INVALID_VALUE":                        0x401,
        "VALUE_NOT_SET":                        0x402,
        "NOT_CONNECTED":                        0x407,
        "INVALID_WHILE_PARKED":                 0x408,
        "INVALID_WHILE_SLAVED":                 0x409,
        "INVALID_OPERATION":                    0x40B,
        "ACTION_NOT_IMPLEMENTED":               0x40C,
    }




class Alpaca():
    api = AlpacaAPI()
    connected = False
    cliend_id = None
    server_transaction_id = 0
    server_transaction_count = 0
    methods = {"GET":{}, "PUT":{}}
        
    def __init__(self, device_type, server_address='127.0.0.1', control_port=8000, discovery_port=32227):
        assert device_type in self.api.supported_device_types, 'device type "%s" not supported' % device_type
        self.server_address = server_address
        self.control_port = control_port
        self.device_type = device_type
        self.discovery_port = discovery_port
        self.server = self.AlpacaHttpServer(self, server_address, control_port)

        # re-catalog API-listed methods, pulling in Common and device type-specific methods
        for api_method_group in ("Common", self.device_type):
            for method_type in ("GET", "PUT"):
                for method_name in list(self.api.methods[api_method_group][method_type].keys()):
                    self.methods[method_type][method_name] = {
                        "action":None, 
                        "required_params":self.api.methods[api_method_group][method_type][method_name]
                    }

    def start(self):
        # Warn if any api methods have not been bound
        for method_type in ("GET", "PUT"):
            for method_name in list(self.methods[method_type].keys()):
                if self.methods[method_type][method_name]["action"] is None:
                    print('Warning: Alpaca API %s method "%s" not bound' % (method_type, method_name))
        print('Starting Alpaca device server')
        self.server.start()
        
        print('Initializing Alpaca discovery responder')
        self.discovery_responder = self.DiscoveryResponder(self.server_address, self.discovery_port, self.control_port)

        
        
    def bindMethod(self, method_type, method_name, action):
        assert method_type in ("GET", "PUT"), 'Alpaca bind method failed, expected "GET" or "PUT" type, got "%s"' % method_type
        assert method_name in self.methods[method_type], 'Alpaca bind method failed, unrecognized %s method "%s"' % (method_type, method_name)
        assert hasattr(action, '__call__'), "Alpaca bind method failed, expected function handle"
        self.methods[method_type][method_name]["action"] = action
        #print(self.methods[method_type][method_name])
        
    def bindMethods(self, methods_list):
        assert type(methods_list) is list, "Bind method expected list type"
        assert len(methods_list)>=1 and len(methods_list[0])==3, "Bind method expected Nx3 list"
        for idx, method in enumerate(methods_list):
            assert len(method)==3, 'Bind method expected Nx3 list'
            assert type(method[0]) is str and method[0] in ("GET", "PUT"), 'Bind method expected "GET" or "PUT"'
            assert type(method[1]) is str, "Expected method name as string"
            assert hasattr(method[2], '__call__'), "Expected function handle"
            self.bindMethod(method[0], method[1], method[2])

    class Transaction:
        def __init__(self, client_transaction_id, server_transaction_id, client_id, request_type, request_path, method, params):
            self.client_transaction_id = client_transaction_id
            self.server_transaction_id = server_transaction_id
            self.client_id = client_id
            self.request_type = request_type
            self.request_path = request_path
            self.method = method
            self.params = params


    def ProcessRequest(self, request_type, request_path, request_body):
        self.server_transaction_count += 1
        server_transaction_id = self.server_transaction_count-1
        
        #print('Request body: %s' % str(request_body))
    
        # parse url-encoded params:
        (api, method, params) = self.__parse_request_path(request_path)
        #print('params:',params)

        # parse body-encoded params:
        if request_body is not None:
            for name, val in parse_qs(request_body).items():
                #val = val if len(val)>1 else val
                val = val[0] if isinstance(val, list) else val
                params[name.lower()] = val

        client_id = params['clientid'] if 'clientid' in params else 0
        client_transaction_id = int(params['clienttransactionid']) if 'clienttransactionid' in params else 0

        transaction = self.Transaction(
            client_transaction_id = client_transaction_id,
            server_transaction_id = server_transaction_id,
            client_id = client_id,
            request_type = request_type,
            request_path = request_path,
            method = method,
            params = params
        )

        #print('Request details: %s' % str((api, method, params)))
        #print("%s request from client ID %s, client transaction %i
        
        if api=="management":
            if method == "apiversions":
                return self.management_response(transaction, [self.api.version])
            elif method == "description":
                return self.management_response(transaction, {
                    "ServerName": "Kasa Switch Hub",
                    "Manufacturer": "rkinnett",
                    "ManufacturerVersion": "1",
                    "Location": "here"
                })
                
            elif method == "configureddevices":
                return self.management_response(transaction, [
                    {
                        "DeviceName": "Kasa Switch Hub",
                        "DeviceType": "Switch",
                        "DeviceNumber": 0,
                        "UniqueID": "1234"
                    },
                ])
            else:
                return self.invalid_request_response(transaction, 'Unrecognized %s method "%s"' % (request_type, method))

        
        elif api=="device_control":        
            device_type = params["device_type"]
            device_number = params["device_number"]
            print("%s request from client ID %s, client transaction %i: \n   device type %s, device number %s, method %s, params %s" \
                % (request_type, client_id, client_transaction_id,  device_type, device_number, method, str(params)))
                    
            # Require either GET or PUT method:
            if request_type not in ("GET", "PUT"):
                return self.invalid_request_response(transaction, 'Expected GET or PUT type HTTP request, got "%s"' % request_type)

            # Require valid device type, number, and method:
            if device_type is None or device_number is None or method is None:
                return self.invalid_request_response(transaction, 'Unsupported path "%s" (expected /api/v1/switch/0/[method]' % request_path)
            
            # Require valid (and registered) method:
            if method is None:
                return self.invalid_request_response(transaction, 'Invalid method "%s"' % method)
            
            if method not in self.methods[request_type]:        
                return self.invalid_request_response(transaction, 'Unrecognized %s method "%s"' % (request_type, method))

            if self.methods[request_type][method]["action"] is None:
                return self.invalid_request_response(transaction, 'Unrecognized %s method "%s"' % (request_type, method))

            # Require required parameters:
            required_params = self.methods[request_type][method]["required_params"]
            #print('required_params: %s' % str(required_params))
            #print('params: %s' % str(params))
            missing_params = []
            for required_param in required_params:
                #print('required param "%s" in params? %s' % (required_param, required_param in params))
                if required_param not in params:
                    missing_params.append(required_param)
            if len(missing_params)>0:
                print('Missing params: %s' % str(missing_params))
                http_return_code = self.server.http_return_codes["INVALID_REQUEST"]
                error_message = 'Error, missing parameter(s): %s' % str(missing_params)
                return (http_return_code, error_message)

            #print("%s request client_id: %s, client transaction ID: %s" % (request_type, client_id, client_transaction_id) )

            return self.methods[request_type][method]["action"](transaction)
        
            
    def noop(self, params):
        print("Alpaca No op, params: %s" % str(params))
        
    
    def nominal_response(self, transaction, value=None):
        response = {
            "ClientTransactionID": transaction.client_transaction_id,
            "ServerTransactionID": transaction.server_transaction_id,
            "ErrorNumber": 0,
            "ErrorMessage": "",
        }
        if value is not None:
            response.update({"Value":value})
        print('response: ',response)
        return (self.server.http_return_codes['VALID_REQUEST'], response)
        
    def error_response(self, transaction, error_number, error_message):
        response = {
            "ClientTransactionID": transaction.client_transaction_id,
            "ServerTransactionID": transaction.server_transaction_id,
            "ErrorNumber": error_number,
            "ErrorMessage": error_message,
        }
        return (self.server.http_return_codes['VALID_REQUEST'], response)

    def device_error_response(self, transaction, error_message):
        return (self.server.http_return_codes['DEVICE_ERROR'], error_message)

    def invalid_request_response(self, transaction, error_message):
        return (self.server.http_return_codes['INVALID_REQUEST'], error_message)

    def not_supported_response(self, transaction):
        return self.error_response(transaction, self.api.error_codes['ACTION_NOT_IMPLEMENTED'], 'method not implemented')
    
    def management_response(self, transaction, value):
        response = {
            "Value" : value,
            "ClientTransactionID": transaction.client_transaction_id,
            "ServerTransactionID": transaction.server_transaction_id,
        }
        return (self.server.http_return_codes['VALID_REQUEST'], response)
    
    def __parse_request_path(self, request_path):
        (api, method, params) = (None, None, {})
        #print("Request path: %s" % request_path)
        path_fields        = request_path.split('/')
        #print('Path fields: %s' % str(path_fields))
        if path_fields[1]=="api" and len(path_fields)==6:
            api = "device_control"
            params["device_type"] = path_fields[3]
            params["device_number"] = path_fields[4]
            method = path_fields[5].split('?')[0]
            #print('path fields 5: %s' % path_fields[5])
            #print('? in path fields 5? %s' % str("?" in path_fields[5]))
            if "?" in path_fields[5]:
                #print("parse_qs:",  parse_qs(path_fields[5].split('?')[1]))
                for name, val in parse_qs(path_fields[5].split('?')[1]).items():
                    val = val[0] if isinstance(val, list) else val
                    params[name.lower()] = val
                #params = dict((name.lower(), val) for name, val in parse_qs(path_fields[5].split('?')[1]).items())
        elif path_fields[1]=="management":
            api = "management"
            method = path_fields[-1]
        else:
            print('Error:  unrecognized request path: %s' % request_path)
        #print( ("api:",api),("method:",method), ("params:",params))
        return (api, method, params)




    class AlpacaHttpServer():
        http_return_codes = {
            "VALID_REQUEST":   200,
            "INVALID_REQUEST": 400,
            "DEVICE_ERROR":    500
        }    
    
        def __init__(self, parent, server_address, device_control_port):
            self.parent = parent
            self.server_address = server_address
            self.device_control_port = device_control_port
            self.server = ThreadingHTTPServer((server_address, device_control_port), self.MakeHandler(self.parent))
            self.thread = threading.Thread(target=self.start_serve_forever)
            
        def start(self):
            print(f"Starting Alpaca server on {self.server_address}:{self.device_control_port}")
            self.thread.start()
            print(f'HTTP server listening on port {self.device_control_port}')
            
        def start_serve_forever(self):
            try:
                self.server.serve_forever()
            except Exception as ex:
                print("exception", ex)                        
            except (ConnectionResetError, ConnectionAbortedError):
                print('Connection closed by remote client')
        
            
        def MakeHandler(self, alpaca):
            class HttpHandler(BaseHTTPRequestHandler):
                protocol_version = 'HTTP/1.1'
                
                def do_GET(self):
                    try:
                        self._handle_request("GET")
                    except Exception as ex:
                        print(ex)

                def do_PUT(self):
                    self._handle_request("PUT")
                    
                def _handle_request(self, http_request_type):
                    try:
                        request_body = self._read_request_body()
                    except Exception as ex:
                        print('error parsing request body')
                        print('Request body: "%s"' % request_body)
                        print(ex)
                        return
                    try:
                        (http_return_code, response_content) = alpaca.ProcessRequest(http_request_type, self.path, request_body)
                    except (ConnectionResetError, ConnectionAbortedError):
                        print('Connection closed by remote client')
                        return
                    except TypeError as er:
                        print(er)
                        print('No response to send; skipping.')
                        return
                    try:
                        self._respond(http_return_code, response_content)
                    except (ConnectionResetError, ConnectionAbortedError):
                        print('Connection closed by remote client')
                    except TypeError:
                        print('TypeError; ProcessRequest result: %s' % str((http_return_code, response_content)))
                        
                def _process_request_headers(self):
                    try:
                        print('\r\n=========== new request received ===========')
                        #print('Headers:')
                        #print(self.headers)
                        #print('CONTENT-LENGTH: %s' % str(self.headers.get('content-length')))
                        #print('TRANSFER-ENCODING: %s' % str(self.headers.get('Transfer-Encoding')))
                        #print('CONTENT-TYPE: %s' % str(self.headers.get('content-type')))
                        content_type = self.headers.get('content-type')
                        content_length = self.headers.get('content-length')
                        content_encoding = self.headers.get('transfer-encoding')
                        content_length = int(content_length) if content_length else None
                        return (content_type, content_length, content_encoding)
                    except (ConnectionResetError, ConnectionAbortedError):
                        print("Connection reset!")
                    except Exception as ex:
                        print('error:')
                        print(ex)
                        return                        
                    
                def _read_request_body(self):
                    # Unique to this application (Alpaca), requests should be x-www-form-urlencoded, in which case content is in path.
                    (request_content_type, request_content_length, request_content_encoding) = self._process_request_headers()
                    if request_content_length is not None:
                        try:
                            request_content = self.rfile.read(request_content_length).decode('utf-8')
                        except (ConnectionResetError, ConnectionAbortedError):
                            print('Connection closed by remote client')
                        except Exception as ex:
                            print('error:')
                            print(ex)
                            return                              
                    else:
                        request_content = None
                    return request_content
                    
                def _respond(self, http_return_code, response_content):
                    # Note: this is application-specific. Alpaca sends json content for valid responses or string for errors
                    print('Response http code: %i, content: "%s"' % (http_return_code, response_content))
                    if http_return_code==200:
                        encoded_content = json.dumps(response_content).encode('utf-8')
                    else:
                        encoded_content = response_content.encode()
                    content_length = len(encoded_content)
                    try:
                        self._set_headers(http_return_code, content_length)
                        #print('Sending response...')
                        self.wfile.write(encoded_content)
                        #print('Sent response ')
                    except Exception as ex:
                        print("exception", ex)                        
                    except (ConnectionResetError, ConnectionAbortedError):
                        print('Connection closed by remote client')
                    
                    
                def _set_headers(self, http_return_code=200, content_length=0):
                    if http_return_code==200:
                        content_type='application/json'
                    else:
                        content_type='text/plain'            
                    #print('Sending headers...')
                    try:
                        self.send_response(http_return_code)
                        self.send_header('Content-type', content_type)
                        self.send_header('Content-Length', str(content_length))
                        self.end_headers()   
                        #print('Sent headers')
                    except Exception as ex:
                        print("exception", ex)                          
            
            return HttpHandler


    class DiscoveryResponder(Thread):
        def __init__(self, address, discovery_port, control_port):
            self.discovery_port = discovery_port
            self.control_port = control_port
            Thread.__init__(self)
            self.device_address = (address, discovery_port) #listen for any IP on Alpaca disc. port
            self.alpaca_response  = "{\"alpacaport\": " + str(control_port) + "}"
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  #share address
            if os.name != 'nt':
                # needed on Linux and OSX to share port with net core. Remove on windows
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            try:
                self.sock.bind(self.device_address)
            except:
                print('Discovery responder failed to bind')
                self.sock.close()
                self.sock = 0
                raise
            # OK start the listener
            self.daemon = True
            print('Starting Alpaca discovery responder on port %i' % discovery_port)
            self.start()
        def run(self):
            while True:
                data, addr = self.sock.recvfrom(1024)
                datascii = str(data, 'ascii')
                print('Alpaca discovery responder received ' + datascii + ' from ' + str(addr))
                if 'alpacadiscovery1' in datascii:
                    print('informing client at %s that ASCOM-Remote server is operating on port %i' % (str(addr),  self.control_port))
                    self.sock.sendto(self.alpaca_response.encode(), addr)