# This script will handle the lighting effects run on the RPI's
# The output of the specified pin does need to be connected to a 5v logic converter
# This logic is one directional, a simple buffer (such as the 74HC125)

from xmlrpc.server import SimpleXMLRPCServer
from socketserver import ThreadingMixIn
import xmlrpc.client
import threading
import random
import board
import neopixel
import time
import sys
import os

## Global vars
local_ip = "http://192.168.200.225:8000/"

# RPC
rpc_address = "http://192.168.200.250:8000/"
rpc_port = 8000

# For sending sync requesst upon connection
sync_request_made = False

# Neopixel
pixel_pin = board.D18
num_pixels = 180 # 180

pixels = [0] * num_pixels

sync_value = "done"

connection_refused_counter = 0

# Parameter dictionary
param_dict = {
    ### color
    "color": [255, 0, 0],

    ## Global params
    "animation_speed": 0.05,
    "master_toggle": "on",
    "current_effect" : "color cycle",

    ## Function specific
    "color_train_gap": 5,
    "color_train_lit": 5,
    "strobe_on_time": 0.5,
    "strobe_off_time": 0.5,
    "random_lights_chance": 50,
    "shift_back_forward": 10,
    "sync_time" : 0
}

### RPC SERVER DATA GETTER
# def get_rpc_values():
#     global sync_value, connection_refused_counter, sync_request_made
#     if sync_value == "done":
#         threading.Timer(1.0, get_rpc_values).start()
#     try:
#         with xmlrpc.client.ServerProxy("http://192.168.200.250:8000/") as rpc_server:
#             # Retrieve values from rpc server
#             rpc_data = rpc_server.get_parameters("Yeet")

#         if not sync_request_made and sync_value != "syncing":
#             sync_request()
#             sync_request_made = True

#         update_parameters(rpc_data)
#         connection_refused_counter = 0
#     except Exception:
#         connection_refused_counter += 1
#         print("Unable to connect to rpc, keeping standard params, refused connection counter: ", connection_refused_counter)

def update_parameters(input_dict):
    global param_dict, sync_value
    # loop through parameter dictionary and swap if match
    for param in input_dict:
        if param in param_dict:
            param_dict[param] = input_dict[param]
        elif param == "shutdown":
            param_dict[param] = input_dict[param]
        elif param == "sync_strips":
            if input_dict[param] != sync_value:     
                sync_value = input_dict[param]

                print(sync_value)

    try:
        # Convert params to floats / ints
        param_dict["animation_speed"] = float(param_dict["animation_speed"])
        param_dict["color_train_gap"] = int(param_dict["color_train_gap"])
        param_dict["color_train_lit"] = int(param_dict["color_train_lit"])
        param_dict["strobe_on_time"]  = float(param_dict["strobe_on_time"])
        param_dict["strobe_off_time"] = float(param_dict["strobe_off_time"])
        param_dict["random_lights_chance"] = int(param_dict["random_lights_chance"])
        param_dict["shift_back_forward"] = int(param_dict["shift_back_forward"])
        param_dict["sync_time"] = float(param_dict["sync_time"])
    except TypeError:
        param_dict["animation_speed"] = 0.05
        param_dict["color_train_gap"] = 5
        param_dict["color_train_lit"] = 5
        param_dict["strobe_on_time"] = 0.5
        param_dict["strobe_off_time"] = 0.5
        param_dict["random_lights_chance"] = 50
        param_dict["shift_back_forward"] = 10
        param_dict["sync_time"] = time.time() + 6 +  param_dict["animation_speed"]

## RPC SERVER SYNCING
def sync_request():
    try:
        with xmlrpc.client.ServerProxy("http://192.168.200.250:8000/") as rpc_server:
            rpc_server.sync_strips("sync")
    except Exception:
       print("\nException while sending SYNC request trying to sync\n")
            

## RPC SERVER SETUP
class serverThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
    def run(self):
        localServer = SimpleXMLRPCServer(("0.0.0.0", rpc_port), allow_none=True)
        localServer.register_function(update_parameters)
        localServer.serve_forever()

### LED FUNCTIONS

# Function vars
built = False
fill = True
full_start = True

color_cycle_r = 255
color_cycle_g = 0
color_cycle_b = 0
red_to_green = True
green_to_blue = False
blue_to_red = False

def static_color(chosen_color):
    global pixels
    pixels.fill(chosen_color)

def color_train(gap, lit, chosen_color):
    global built, pixels
    if not built:
        g_counter = 1
        l_counter = 1
        current_gap = False
        for i in range(num_pixels):
            if not current_gap:
                pixels[i] = chosen_color
                l_counter += 1

                if l_counter > lit:
                    l_counter = 1
                    current_gap = True
            else:
                g_counter += 1
                pixels[i] = [0, 0, 0]

                if g_counter > gap:
                    g_counter = 1
                    current_gap = False
        built = True
    else:
        # shift list
        pixels = shift_list(pixels)

def shift_back_forward(amount, chosen_color):
    global pixels, fill, full_start
    counter = 1
    if full_start == True:
        fill = False
        full_start = False
    else:
        fill = True
        full_start = True

    for i in range(num_pixels):
        if fill:
            pixels[i] = chosen_color
            counter += 1
            if counter > amount:
                counter = 1
                fill = False
        else:
            pixels[i] = [0, 0, 0]
            counter += 1
            if counter > amount:
                counter = 1
                fill = True

def strobe(chosen_color):
    global pixels, fill
    if fill:
        pixels.fill(chosen_color)
    else:
        pixels.fill((0,0,0))

def random_lights(chance, chosen_color):
    global pixels
    for i in range(num_pixels):
        if random.randint(0, 100) <= chance:
            pixels[i] = chosen_color
        else:
            pixels[i] = [0, 0, 0]

def color_cycle(smoothness):
    global pixels, red_to_green, green_to_blue, blue_to_red, color_cycle_r, color_cycle_g, color_cycle_b

    if red_to_green:
        color_cycle_g += smoothness
        if color_cycle_g >= 255:
            color_cycle_g = 255
            color_cycle_r -= smoothness
            if color_cycle_r <= 0:
                color_cycle_r = 0
                red_to_green = False
                green_to_blue = True
    elif green_to_blue:
        color_cycle_b += smoothness
        if color_cycle_b >= 255:
            color_cycle_b = 255
            color_cycle_g -= smoothness
            if color_cycle_g <= 0:
                color_cycle_g = 0
                green_to_blue = False
                blue_to_red = True
    elif blue_to_red:
        color_cycle_r += smoothness
        if color_cycle_r >= 255:
            color_cycle_r = 255
            color_cycle_b -= smoothness
            if color_cycle_b <= 0:
                color_cycle_b = 0
                blue_to_red = False
                red_to_green = True
    pixels.fill((color_cycle_r,color_cycle_g,color_cycle_b))

# Rainbow calculations
def wheel(pos):
    if pos < 0 or pos > 255:
        r = g = b = 0
    elif pos < 85:
        r = int(pos * 3)
        g = int(255 - pos * 3)
        b = 0
    elif pos < 170:
        pos -= 85
        r = int(255 - pos * 3)
        g = 0
        b = int(pos * 3)
    else:
        pos -= 170
        r = 0
        g = int(pos * 3)
        b = int(255 - pos * 3)
    return (r, g, b)

def rainbow_cycle(color_index):
    for i in range(num_pixels):
        pixel_index = (i * 256 // num_pixels) + color_index
        pixels[i] = wheel(pixel_index & 255)

# Sync mode effect
# One state of the sync effect will last for 500ms

sync_on = False
def sync_effect():
    global sync_on

    if not sync_on:
        static_color([255, 128, 255])
        pixels.show()
        sync_on = True


# Shift list left or right
def shift_list(list_in=[], shift_dir="right"):
    list_out = list_in

    if shift_dir == "left":
        first_element = list_out[0]
        for i in range(len(list_out) -1):
            list_out[i] = list_out[i+1]
        list_out[-1] = first_element
    elif shift_dir == "right":
        last_element = list_out[-1]
        for i in range(len(list_out) - 1, 0, -1):
            list_out[i] = list_out[i-1]
        list_out[0] = last_element
    else:
        raise Exception("Direction specified doesn't exist: " + str(shift_dir))

    return list_out


effects = {
    "color cycle" : 0,
    "rainbow" : 1,
    "static color" : 2,
    "color train" : 3,
    "shift back forward" : 4,
    "strobe" : 5,
    "random light" : 6
}

def main_loop():
    global built, red_to_green, green_to_blue, blue_to_red, color_cycle_r, color_cycle_g, color_cycle_b, sync_on

    # For checking if the static color was filled in
    static_filled = False

    # Previous color
    prev_color = param_dict["color"]

    prev_color_train_lit = param_dict["color_train_lit"]
    prev_color_train_gap = param_dict["color_train_gap"]

    # previous effect
    prev_effect = param_dict["current_effect"]
    
    # Previous master toggle
    prev_toggle = param_dict["master_toggle"]

    # previous sync mode
    sync_fix = False

    rainbow_sequence = 0

    print("Effect:", prev_effect)
    print("Color:", prev_color)

    next_time = time.time() + param_dict["animation_speed"]

    got_sync_time = False

    while True:
        # Check for the shutdown command
        if "shutdown" in param_dict:
            print("Shutting down!")
            os.system("shutdown now -h")
            break
        elif sync_value == "syncing":
            # Syncing mode, main loop not running, starting after sync is completed
            sync_effect()

            sync_fix = True

            if not got_sync_time:
                next_time = param_dict["sync_time"]
                got_sync_time = True
        else:
            if param_dict["master_toggle"] == "on":
                currently_playing = param_dict["current_effect"]
                if sync_fix:
                        previous_time = time.time()
                        next_time = previous_time + param_dict["animation_speed"]
                        
                        # Reset all effect values
                        sync_fix = False
                        static_filled = False
                        built = False
                        rainbow_sequence = 0
                        red_to_green = True
                        green_to_blue = False
                        blue_to_red = False
                        color_cycle_r = 255
                        color_cycle_g = 0
                        color_cycle_b = 0
                        sync_on = False
                        got_sync_time = False
                        print("Sync fixed, current effect:", param_dict["current_effect"])
                else:
                    if (next_time - time.time()) <= 0 and currently_playing != "strobe":
                        next_time += param_dict["animation_speed"]

                        if currently_playing != prev_effect:
                            static_filled = False
                            built = False
                            prev_effect = currently_playing

                            print("Effect:", currently_playing)
                            
                        if prev_color != param_dict["color"]:
                            static_filled = False
                            built = False
                            prev_color = param_dict["color"]

                            print("Color:", prev_color)
                        if prev_color_train_lit != param_dict["color_train_lit"]:
                            prev_color_train_lit = param_dict["color_train_lit"]
                            built = False
                        if prev_color_train_gap != param_dict["color_train_gap"]:
                            prev_color_train_gap = param_dict["color_train_gap"]
                            built = False


                        if currently_playing == "color cycle":
                            color_cycle(2.5)
                        elif currently_playing == "rainbow":
                            #rainbow()
                            rainbow_cycle(rainbow_sequence)
                            rainbow_sequence += 1
                            if rainbow_sequence > 255:
                                rainbow_sequence = 0
                        elif currently_playing == "static color":
                            if not static_filled:
                                static_color(param_dict["color"])
                                static_filled = True
                        elif currently_playing == "color train":
                            color_train(param_dict["color_train_gap"], param_dict["color_train_lit"], param_dict["color"])
                        elif currently_playing == "shift back forward":
                            shift_back_forward(param_dict["shift_back_forward"], param_dict["color"])
                        elif currently_playing == "random light":
                            random_lights(param_dict["random_lights_chance"],  param_dict["color"])

                        pixels.show()
                        # alter timing on strobe
                    elif currently_playing == "strobe":
                        if currently_playing != prev_effect:
                            static_filled = False
                            built = False
                            prev_effect = currently_playing

                            print("Effect:", currently_playing)

                        if fill and (next_time - time.time()) <= 0:
                            next_time += param_dict["strobe_off_time"]
                            fill = False
                            strobe(param_dict["color"])
                            pixels.show()
                        elif (next_time - time.time()) <= 0:
                            next_time += param_dict["strobe_on_time"]
                            fill = True
                            strobe(param_dict["color"])
                            pixels.show()
                        
            else:
                # Fill empty
                if prev_toggle is not param_dict["master_toggle"]:
                    prev_toggle = param_dict["master_toggle"]
                    static_color([0, 0, 0])
                    pixels.show()

first = True

def identify_client():
    global local_ip, first
    # Try to establish connection with main server and notify   
    try:
        with xmlrpc.client.ServerProxy("http://192.168.200.250:8000/") as rpc_server:
            # Give server our IP
            rpc_server.identify_client(local_ip, first)
            first = False
    except Exception:
       print("Couldn't establish connection defaulting to standard params...")
    
    threading.Timer(20.0, identify_client).start()

if __name__ == '__main__':
    pixels = neopixel.NeoPixel (pixel_pin, num_pixels, auto_write=False)
    # start rpc server in new thread
    server_thread = serverThread()
    server_thread.start()
    identify_client()
    main_loop()