# Web Server for controlling led

from flask import Flask, request, redirect, render_template
from xmlrpc.server import SimpleXMLRPCServer
import xmlrpc.client
import threading
import time
import os

# FLASK SETTINGS
app = Flask(__name__)
# port
flask_port = 5000
# Page template
page_template = "index.html"

# RPC SETTINGs
rpc_port = 8000

#List of addresses that have identified themselves
client_addresses = []

MAX_CLIENT_EXCEPTION = 5

## Dictionary of all preset colors
color_dict = {
    "red" : [255, 0, 0],
    "yellow" : [255, 255, 0],
    "green" : [0, 255, 0],
    "cyan" : [0, 255, 255],
    "blue" : [0, 0, 255],
    "magenta" : [255, 0, 255],
    "white" : [255, 255, 255],
}

# Effect counter
effect_counter = 0

# List of effects
effects = {
    0 : "color cycle",
    1 : "rainbow",
    2 : "static color",
    3 : "color train",
    4 : "shift back forward",
    5 : "strobe",
    6 : "random light"
}

# create parameter dictionary using default parameters
param_dict = {
    ### color
    "color": [255, 0, 0],

    ## Global params
    "animation_speed": 0.075,
    "master_toggle": "on",
    "current_effect" : "color cycle",

    ## Function specific
    "color_train_gap": 5,
    "color_train_lit": 5,
    "strobe_on_time": 0.75,
    "strobe_off_time": 0.75,
    "random_lights_chance": 50,
    "shift_back_forward": 10,
    "sync_strips": "done",
    "scroll" : "top",
    "sync_time": 0.0
}

def identify_client(param_list, first):
    global client_addresses, param_dict
    print (client_addresses)
    addresses = client_addresses
    if param_list not in client_addresses:
        # Try sending data to client, if error don't add
        try:
            with xmlrpc.client.ServerProxy(param_list) as rpc_server:
                rpc_server.update_parameters(param_dict)
            addresses.append(param_list)
            if param_dict["sync_strips"] != "syncing":
                sync_strips("sync")
            
        except Exception as e:
            print("Error while trying to add: " + param_list + " to the client list")
    if first:
        if param_dict["sync_strips"] != "syncing":
                sync_strips("sync")
    client_addresses = addresses

def shutdown_server():
    os.system("shutdown now -h")

def reset_param():
    global param_dict
    del param_dict["shutdown"]

def shutdown(param_list):
    global param_dict

    if param_list == "all":
        print("Shutting down everything!")
        threading.Timer(5.0, shutdown_server).start()
    else:
        print("Shutting down clients!")
        threading.Timer(5.0, reset_param).start()
    param_dict["shutdown"] = True
    
def sync_done():
    global param_dict
    print("Syncing Done!")
    param_dict["sync_strips"] = "done"
    send_data_to_rpc()

def sync_strips(param_list):
    global param_dict
    if param_list == "sync":
        print("Syncing LED Strips!")
        param_dict["sync_strips"] = "syncing"
        param_dict["sync_time"] = time.time() + float(param_dict["animation_speed"]) + 6
        send_data_to_rpc()
        threading.Timer(5.0, sync_done).start()

def send_data_to_rpc():
    global param_dict, client_addresses

    for address in client_addresses:
        exception_counter = 0
        send_success = False

        while exception_counter != (MAX_CLIENT_EXCEPTION - 1) and send_success == False:
            try:
                print(address)
                with xmlrpc.client.ServerProxy(address) as rpc_server:
                    # Send all parameters to the rpc server
                    rpc_server.update_parameters(param_dict)
                    send_success = True
                    print("Success!")
            except Exception as e:
                print(e)
                exception_counter += 1
        
        # Remove client address from saved addresses
        if not send_success:
            client_addresses.pop(client_addresses.index(address))

def get_rpc_values():
    global param_dict, color_dict

    rpc_data = param_dict.copy()
    for color in color_dict:
        if color_dict[color] == rpc_data["color"]:
            rpc_data["color"] = color
    return rpc_data

def constrain_parameters(parameter_list):
    global param_dict
    is_custom = False
    # check each parameter in the dictionary and constrain to proper value
    try:
        try:
            color_constrained = parameter_list["color"]

            if color_constrained == False:
                param_dict["color"] = param_dict["color"]
            elif not isinstance(color_constrained, list):
                
                is_custom = True
                color_constrained = str(color_constrained)
                print(color_constrained)
                if color_constrained.find(",") != -1 or color_constrained.find("#") != -1:
                    r_value = 0
                    g_value = 0
                    b_value = 0
                    if color_constrained.find(",") != -1:
                        color_constrained = color_constrained.split(",")
                        r_value = int(color_constrained[0])
                        g_value = int(color_constrained[1])
                        b_value =int(color_constrained[2])
                    else:
                        # convert hex number to int
                        # remove first char
                        color_constrained = color_constrained[1:]
                        r_value = int(color_constrained[:2], 16)
                        g_value = int(color_constrained[2:4], 16)
                        b_value = int(color_constrained[4:6], 16)

                    if r_value > 255:
                        r_value = 255
                    elif r_value < 0:
                        r_value = 0

                    if g_value > 255:
                        g_value = 255
                    elif g_value < 0:
                        g_value = 0
                    
                    if b_value > 255:
                        b_value = 255
                    elif b_value < 0:
                        b_value = 0
                
                    param_dict["color"] = [r_value, g_value, b_value]
                else:
                    param_dict["color"] = [255, 0, 0]
            else:
                param_dict["color"] = color_constrained
        except:
            param_dict["color"] = [255, 0, 0]
            print("DEFAULTING TO COLOR")

        # constrain all integer/ float values
        param_dict["animation_speed"] = float(param_dict["animation_speed"])
        if param_dict["animation_speed"] < 0:
            param_dict["animation_speed"] = 0

        param_dict["color_train_gap"] = int(param_dict["color_train_gap"])
        param_dict["color_train_lit"] = int(param_dict["color_train_lit"])
        if param_dict["color_train_gap"] < 0:
            param_dict["color_train_gap"] = 0
        if param_dict["color_train_lit"] < 0:
            param_dict["color_train_lit"] = 0

        param_dict["strobe_on_time"] = float(param_dict["strobe_on_time"])
        param_dict["strobe_off_time"] = float(param_dict["strobe_off_time"])
        if param_dict["strobe_on_time"] < 0:
            param_dict["strobe_on_time"] = 0
        if param_dict["strobe_off_time"] < 0:
            param_dict["strobe_off_time"] = 0

        param_dict["random_lights_chance"] = int(param_dict["random_lights_chance"])
        param_dict["shift_back_forward"] = int(param_dict["shift_back_forward"])

        if param_dict["random_lights_chance"] < 0:
            param_dict["random_lights_chance"] = 0
        elif param_dict["random_lights_chance"] > 100:
            param_dict["random_lights_chance"] = 100
        
        if param_dict["shift_back_forward"] < 0:
            param_dict["shift_back_forward"] = 0

        # After successful parsing of the variables update the parameter dictionary
        for params in parameter_list:
            if params in param_dict and parameter_list[params] is not False:
                if params != "color":
                    param_dict[params] = parameter_list[params]
                elif is_custom is False:
                    param_dict[params] = parameter_list[params]
            elif params == "switch_effect_button" and parameter_list[params] is not False:
                # Load effect counter from global scope
                global effect_counter
                if parameter_list[params] == "prev":
                    effect_counter -= 1
                    if effect_counter < 0:
                        effect_counter = len(effects) - 1
                elif parameter_list[params] == "next":
                    effect_counter += 1
                    if effect_counter > len(effects) - 1:
                        effect_counter = 0
                # modify parameter dictionary
            param_dict["current_effect"] = effects[effect_counter]
    except Exception as e:
        print(e)
    print(param_dict)

# main routing
@app.route("/")
def main_page():
    # Return template
    return render_template(page_template, **get_rpc_values())

# Post request routing
@app.route("/", methods=["POST"])
def post_handler():
    global color_dict
    ### Check every form

    key_value = ""
    f = request.form
    for key in f.keys():
        key_value = str(key)

    ### Colors ###
    color_button = request.args.get("color_button", False)
    if not color_button:
        color_button = request.form.get("color_button", False)

    color_custom = request.args.get("custom_color", False)
    if not color_custom:
        color_custom = request.form.get("custom_color", False)

    ### Global parameters ###
    # timing
    animation_speed = request.args.get("animation_speed", False)
    if not animation_speed:
        animation_speed = request.form.get("animation_speed", False)
    # Master on/ off
    master_toggle = request.args.get("master_toggle", False)
    if not master_toggle:
        master_toggle = request.form.get("master_toggle", False)
    # shutdown client button
    shutdown_client_button = request.args.get("shutdown_client_button", False)
    if not shutdown_client_button:
        shutdown_client_button = request.form.get("shutdown_client_button", False)
    # Shutdown all button
    shutdown_all_button = request.args.get("shutdown_all_button", False)
    if not shutdown_all_button:
        shutdown_all_button = request.form.get("shutdown_all_button", False)
    # Switching effect
    switch_effect_button = request.args.get("switch_effect_button", False)
    if not switch_effect_button:
        switch_effect_button = request.form.get("switch_effect_button", False)

    ### Function specific paramters ###

    ## Color train
    color_train_gap = request.args.get("color_train_gap", False)
    if not color_train_gap:
        color_train_gap = request.form.get("color_train_gap", False)
    color_train_lit = request.args.get("color_train_lit", False)
    if not color_train_lit:
        color_train_lit = request.form.get("color_train_lit", False)

    ## Strobe
    strobe_on_time = request.args.get("strobe_on_time", False)
    if not strobe_on_time:
        strobe_on_time = request.form.get("strobe_on_time", False)
    strobe_off_time = request.args.get("strobe_off_time", False)
    if not strobe_off_time:
        strobe_off_time = request.form.get("strobe_off_time", False)

    ## Random light up
    random_lights_chance = request.args.get("random_lights_chance", False)
    if not random_lights_chance:
        random_lights_chance = request.form.get("random_lights_chance", False)
    
    ## Shift back forward
    shift_back_forward = request.args.get("shift_back_forward", False)
    if not shift_back_forward:
        shift_back_forward = request.form.get("shift_back_forward", False)

    ## Sync LED Strips
    sync_value = request.args.get("sync_strips", False)
    if not sync_value:
        sync_value = request.form.get("sync_strips", False)

    if sync_value != False:
        sync_strips("sync")

    # Built in colors
    if color_button in color_dict:
        color_custom = color_dict[color_button]

    if shutdown_client_button != False or shutdown_all_button != False:
        payload = "clients"
        if shutdown_all_button != False:
            print("Shutting down everything!")
            payload = "all"
        else:
            print("Shutting down clients!")

        shutdown(payload)

    if color_custom == "":
        color_custom = False
    if animation_speed == "":
        animation_speed = False
    if master_toggle == "":
        master_toggle = False
    if switch_effect_button == "":
        switch_effect_button = False
    if color_train_gap == "":
        color_train_gap = False
    if color_train_lit == "":
        color_train_lit = False
    if strobe_on_time == "":
        strobe_on_time = False
    if strobe_off_time == "":
        strobe_off_time = False
    if random_lights_chance == "":
        random_lights_chance = False
    if shift_back_forward == "":
        shift_back_forward = False
    if key_value == "":
        key_value = False

    ## Add all parameters into dict for rpc server
    param_out_dict = {
        ### color
        "color": color_custom,

        ## Global params
        "animation_speed": animation_speed,
        "master_toggle": master_toggle,
        "switch_effect_button": switch_effect_button,

        ## Function specific
        "color_train_gap": color_train_gap,
        "color_train_lit": color_train_lit,
        "strobe_on_time": strobe_on_time,
        "strobe_off_time": strobe_off_time,
        "random_lights_chance": random_lights_chance,
        "shift_back_forward": shift_back_forward,
        "scroll" : key_value
    }

    print("sending...")
    constrain_parameters(param_out_dict)
    
    # Send data to clients
    send_data_to_rpc()

    # Request parameters
    return render_template(page_template, **get_rpc_values())

class serverThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
    def run(self):
        localServer = SimpleXMLRPCServer(("0.0.0.0", rpc_port), allow_none=True)
        localServer.register_function(identify_client)
        localServer.serve_forever()

class flaskThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
    def run(self):
        # run flask app on local ip
        app.run(host="0.0.0.0", port=flask_port, debug=False)

if __name__ == "__main__":
    # start rpc server in new thread
    server_thread = serverThread()
    flask_thread = flaskThread()
    server_thread.start()
    flask_thread.start()

    print("Local server running!")

    print("RPC server started...")