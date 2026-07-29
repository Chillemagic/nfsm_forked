#!/usr/bin/env python3
# Adapted from Andrew Song's impl: https://github.com/YaLTeR/niri/issues/426#issuecomment-3367714198
import json
import os
import socket
import subprocess
import sys
import threading
import time
# tracks current position (column/row) of all windows { window_id -> (col, row) }
window_positions = {}
# dict that tracks fullscreen windows and their restore positions { window_id -> { position: (col, row), workspace_id: num, stacked: Bool, exit: Bool } }
fullscreen_windows = {}
# dict that tracks maximized windows and their restore positions { window_id -> { position: (col, row), workspace_id: num, stacked: Bool, exit: Bool } }
maximize_windows = {}
# dict that tracks windows that run the full_width_cmd
full_width_cmd_windows = {} 

# bugs -------------------------------------------------------------------------------
    # 1. Maximised window does not have it's original state resotred
    # 2. 


def main():
    t1 = threading.Thread(target=nfsm_stream)
    t2 = threading.Thread(target=nfsm_socket)
    t1.start()
    t2.start()
    try:
        t1.join()
        t2.join()
    except KeyboardInterrupt:
        sys.exit()

def run_niri_action(action_parts, window_id):
    # action_parts will be either:
    # - str: a single command name
    # - tuple/list of strings: a single action with args, e.g. ("set-window-width", "100%")
    # - tuple/list of tuples: multiple actions, e.g. (("cmd1",), ("cmd2", "arg"))

    if not action_parts:
        return

    # Normalize into a list of action tuples
    if isinstance(action_parts, str):
        action_list = [(action_parts,)]
    elif isinstance(action_parts, (list, tuple)) and action_parts and isinstance(action_parts[0], (list, tuple)):
        # sequence of actions
        action_list = [tuple(a) for a in action_parts]
    else:
        # single action expressed as tuple/list of strings
        action_list = [tuple(action_parts)]
    
        
    for one_action in action_list:
        if not one_action:
            continue
        # diagnostic log
        print(f"RUNNING niri action: {one_action} --id {window_id}")
        res = subprocess.run(
            ["niri", "msg", "action", *one_action, "--id", str(window_id)],
            capture_output=True,
            text=True,
        )
        # print result for debugging
        print(f" -> rc={res.returncode}, stdout={res.stdout.strip()!r}, stderr={res.stderr.strip()!r}")
        # small pause so niri can process sequential actions
        # time.sleep(0.08)



def handle_request(tracked_windows, action):
    # get focused window
    # tracked_windows is either fullscreen_windows or maximise_windows
    props = subprocess.run(
        ["niri", "msg", "--json", "focused-window"],
        capture_output=True,
        text=True,
    )
    window = json.loads(props.stdout)
    window_id = window["id"]
    workspace_id = window["workspace_id"]
 

    # expanded = window["exit"]
    
    # the window is exiting
    if window_id in tracked_windows: 
       
        if action == "FullWidthRequest": 
            # determine the sequence of actions to run
            actions = determine_action(window_id, tracked_windows)
            print(f"Actions have been set to: {actions}")
            run_niri_action(actions, window_id) 
        else: 
            tracked_windows[window_id]["exit"] = True
            run_niri_action(action, window_id)
        return
    # the window is entering
    if window_id in window_positions:
        # check window if it is stacked
 
        col, row = window_positions[window_id]["position"]
        window_width = window["layout"]["window_size"][0]
        tracked_windows[window_id] = {
            "position": (col, row),
            "exit": False,
            "expanded": False,
            "stacked": False,
            "width": window_width,
            "workspace_id": workspace_id
        }
        
        current_window = tracked_windows[window_id]
        if action == "FullWidthRequest":
            stacked = is_window_stacked(window_id, tracked_windows)
            tracked_windows[window_id]["stacked"] = stacked
            print(f"Window:{window_id} has been added to full_width_cmd_windows, is it stacked? {stacked} ")
            # redefine action for FullWidthRequest toggle
            actions = determine_action(window_id, tracked_windows)
            print(f"Actions have been set, they read as: {actions} ")
            if actions:
                run_niri_action(actions, window_id)
            return
        # Handle empty string returned from determine_action  
        if action:
            run_niri_action(action, window_id)

def handle_fullscreen_request():
    handle_request(fullscreen_windows, "fullscreen-window")

def handle_maximize_request():
    handle_request(maximize_windows, "maximize-window-to-edges")

def handle_full_width_request():
    handle_request(full_width_cmd_windows, "FullWidthRequest" )

def is_window_stacked(window_id, tracked_windows):
    # define column and workspace_id for comparison
    #printing variables for debugging:workspace 
    window = window_positions[window_id] 
    column = window["position"][0] 
    workspace_id = window["workspace_id"]
    stacked = tracked_windows[window_id]["stacked"] 
    # iterate through window_positions to see if there is a matching column_id and workspace
    for other_id, data in window_positions.items():
        if other_id == window_id:
            continue

        if data["position"][0] == column and data["workspace_id"] == workspace_id:
            stacked = True
            break
   
    return stacked

def determine_action(window_id, tracked_windows):
    # Return a tuple of action-tuples describing what to run.

    # Always return something like: (("cmd",), ("cmd2","arg"))
    
    window = tracked_windows[window_id]
    expanded = window.get("expanded", False)
    stacked = window.get("stacked", False)
    window_width = window.get("width")

    # Expand to full-width
    if not expanded:
        actions = []
        if stacked:
            actions.append(("consume-or-expel-window-right",))
        actions.append(("set-window-width", "100%"))
        tracked_windows[window_id]["expanded"] = True
        tracked_windows[window_id]["exit"] = False
        return tuple(actions)

    # Restore previous width
    actions = []
    if stacked:
        actions.append(("consume-or-expel-window-left",))
    actions.append(("set-window-width", str(window_width)))
    tracked_windows[window_id]["expanded"] = False
    tracked_windows[window_id]["exit"] = True
    return tuple(actions)
def nfsm_socket():
    server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    socket_path = os.getenv("NFSM_SOCKET", "/run/user/1000/nfsm.sock")

    # remove the socket file if it already exists
    try:
        os.unlink(socket_path)
    except OSError:
        if os.path.exists(socket_path):
            raise

    try:
        server_socket.bind(socket_path)
    except socket.error as message:
        print(f"Failed to bind socket: {message}")
        sys.exit()

    # allow five connections to have some buffer for concurrent clients, but a single connection should be enough
    server_socket.listen(5)
    print(f"Socket server listening on: {socket_path}")

    while True:
        # client connection
        client_socket = server_socket.accept()[0]

        try:
            data = client_socket.recv(1024)
            if data:
                cmd = data.decode('utf-8').strip()
                if cmd == "FullscreenRequest":
                    handle_fullscreen_request()
                elif cmd == "MaximizeRequest":
                    handle_maximize_request()
                elif cmd == "FullWidthRequest":
                    handle_full_width_request()
        except socket.error as e:
            print(f"Socket error: {e}")
        finally:
            client_socket.close()

def handle_window_closed(window_id):
    if window_id in window_positions:
        col, row = window_positions[window_id]["position"]
        del window_positions[window_id]
    if window_id in fullscreen_windows:
        del fullscreen_windows[window_id]
    if window_id in maximize_windows:
        del maximize_windows[window_id]
    if window_id in full_width_cmd_windows:
            del full_width_cmd_windows[window_id]

def niri_cmd(command):
    subprocess.run(["niri", "msg", "action", command])

def restore_position(tracked_windows, window_id, col, row):
    if window_id not in tracked_windows or not tracked_windows[window_id]["exit"]:
        return False
    dest_col, dest_row = tracked_windows[window_id]["position"]
    # move window to the right column if necessary
    if dest_col < col:
        niri_cmd("consume-or-expel-window-left")
        return True
    # move window to the correct row if necessary
    if dest_row != row:
        for _ in range(row - dest_row):
            niri_cmd("move-window-up")
    # window is already back at its last recorded position
    del tracked_windows[window_id]
    return False

def nfsm_stream():
    proc = subprocess.Popen(
        ["stdbuf", "-oL", "niri", "msg", "--json", "event-stream"],
        stdout=subprocess.PIPE,
        text=True,
    )

    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue

        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            print("Failed to parse JSON")
            continue

        # initial window positions
        if "WindowsChanged" in event and not window_positions:
            windows = event["WindowsChanged"]["windows"]

            for window in windows:
                window_id = window["id"]
                workspace_id = window["workspace_id"]
                layout = window.get("layout", {})
                pos = layout.get("pos_in_scrolling_layout")
                if pos is None:
                    continue  # skip floating windows
                window_positions[window_id] = {
                    "workspace_id" : workspace_id,
                    "position" : tuple(pos)
                }

        # it occurs when a window is closed; only the id is available
        if "WindowClosed" in event:
            window_id = event["WindowClosed"]["id"]
            handle_window_closed(window_id)

        # it occurs when a window is opened or moved to a new workspace
        if "WindowOpenedOrChanged" in event:
            window = event["WindowOpenedOrChanged"]["window"]
            window_id = window["id"]
            workspace_id = window["workspace_id"]
            layout = window.get("layout", {})
            pos = layout.get("pos_in_scrolling_layout")
            if pos is not None:
                window_positions[window_id] = {
                    "workspace_id" : workspace_id,
                    "position" : tuple(pos)
                }


        if "WindowLayoutsChanged" not in event:
            continue

        changes = event["WindowLayoutsChanged"]["changes"]

        for change in changes:
            window_id = change[0]
            window_data = change[1]

            try:
                col, row = window_data["pos_in_scrolling_layout"]
            except TypeError:
                # ignore floating windows that are made fullscreen and then go back to floating
                continue

            # move the window to the last recorded position when necessary
            if restore_position(fullscreen_windows, window_id, col, row):
                continue
            if restore_position(maximize_windows, window_id, col, row):
                continue
            if restore_position(full_width_cmd_windows, window_id, col, row):
                continue

            print(f"DEBUG window_id={window_id}")
            print(f"DEBUG window_data={window_data}")
            if window_id in window_positions:
                window_positions[window_id]["position"] = (col, row)
            else:
                window_positions[window_id] = { "position": (col, row) }


            sys.stdout.flush()

    proc.wait()
    if proc.returncode != 0:
        os._exit(1)

if __name__ == "__main__":
    main()
