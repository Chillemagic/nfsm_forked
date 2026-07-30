 # NFSM Forked

  A personal extension of [gvolpe/nfsm](https://github.com/gvolpe/nfsm), adding a custom **full-width window toggle**
  for the [Niri](https://github.com/YaLTeR/niri) scrollable-
  tiling Wayland compositor.

  This fork was created as a practical exploration of Python
  daemon development, event-driven state management, Unix
  socket communication, shell scripting, and integration with
  Niri’s IPC interface.

  ## Project Overview

  Niri provides native actions for fullscreen and maximized
  windows. However, neither behavior matched the visual
  result I wanted:

  - Fullscreen mode hides the status bar and makes the window
  opaque.
  - Maximizing expands the window in both dimensions.
  - I wanted to expand a window to the full available
  **width** while preserving its normal height, transparency,
  and surrounding desktop elements.

  This fork introduces a stateful full-width toggle that
  expands the focused window to 100% width and restores its
  previous width when the command is used again.

  https://github.com/user-attachments/assets/fadd07cc-7e0a-4f5c-9fc9-717e129fa10b

  ## Key Changes

  ### Full-width window toggle

  The daemon now accepts a `FullWidthRequest` command through
  its Unix socket.

  When the command is received, it:

  1. Identifies the currently focused window.
  2. Records the window’s original width, layout position,
  and workspace.
  3. Determines whether the window belongs to a stacked
  column.
  4. Expands the window to 100% width.
  5. Restores the recorded width and layout state when
  toggled again.

  This provides a full-width presentation without entering
  Niri’s native fullscreen mode.

  ### Stateful window restoration

  The daemon’s tracked window state was extended to include:

  - Original column and row position
  - Workspace ID
  - Original window width
  - Whether the window was part of a stack
  - Whether the window is currently expanded or being
  restored

  Tracking this information allows window state to be
  restored more reliably after full-width, fullscreen, and
  maximize operations.

  ### Stacked-window handling

  A full-width operation can affect the surrounding layout
  when the selected window shares a column with other
  windows.

  The `is_window_stacked()` function compares workspace and
  column information to detect this case. The daemon can then
  use Niri’s consume and expel actions when entering or
  leaving full-width mode, preserving the intended layout as
  closely as possible.

  ### Multi-action command execution

  The Niri action runner was expanded to support both
  individual actions and ordered sequences of actions.

  This is required for operations such as:

  1. Moving a stacked window out of its existing column.
  2. Setting its width to 100%.
  3. Reversing those operations when restoring the window.

  Actions are passed to `subprocess.run()` as argument lists,
  avoiding shell command construction.

  ### Non-Nix command-line client

  A standalone Bash client was added for users who are not
  installing the project through Nix.

  The client:

  - Connects to the daemon through its Unix socket.
  - Uses `FullWidthRequest` as its default command.
  - Supports overriding the command through a positional
  argument.
  - Respects the `NFSM_SOCKET` environment variable.
  - Reports connection failures through standard error.

  ## Fullscreen and Full-Width Comparison

  ### Native fullscreen

  Native fullscreen hides surrounding desktop elements and
  changes the window’s visual presentation.

<img width="2736" height="1824" alt="image" src="https://github.com/user-attachments/assets/d3955bb0-a8a2-4419-9358-5351bd9c1834" />


  ### Custom full-width mode

  Full-width mode preserves the window’s normal height,
  transparency, and desktop chrome.

<img width="2736" height="1824" alt="image" src="https://github.com/user-attachments/assets/9296ad3b-e61c-40fc-bb17-60ce281f58e1" />

  ## Technical Approach

  NFSM runs as a Python daemon with two concurrent
  responsibilities:

  - Listening to Niri’s JSON event stream and maintaining an
  in-memory representation of window layout state.
  - Listening for commands from a client over a Unix domain
  socket.

  The full-width feature builds on this architecture by
  treating expansion as a reversible state transition:

  ```text
  Normal window
      |
      | FullWidthRequest
      v
  Record width and layout state
      |
      v
  Expand to 100% width
      |
      | FullWidthRequest
      v
  Restore recorded width and layout state
```
  This work required coordinating asynchronous layout events
  with user-issued commands. In particular, restoration logic
  must distinguish expected layout changes from ordinary
  window movement.


  ## What I Learned

  Developing this fork provided hands-on experience with:

  - Processing a continuous JSON event stream
  - Maintaining state for multiple windows and workspaces
  - Communicating through Unix domain sockets
  - Invoking external programs safely with Python’s
    subprocess module

  - Designing reversible actions around asynchronous
    compositor events

  - Handling layout edge cases involving stacked windows
  - Providing a shell-based client for non-Nix environments
  - Documenting and demonstrating an extension to an existing
    open-source project

  ## Current Status

  The full-width toggle is implemented and has been manually
  tested in a Niri session. The project does not currently
  include an automated test suite, so additional testing is
  still needed for unusual layout transitions and compositor
  edge cases.

  Planned improvements include:

  - Expanding installation and usage documentation
  - Reducing diagnostic output in normal operation
  - Adding automated tests for state-transition logic
  - Improving error handling for unavailable or malformed
    Niri responses

  - Testing restoration across a wider range of stacked and
    multi-workspace layouts

  ## Attribution

  This repository is a fork of gvolpe/nfsm
  (https://github.com/gvolpe/nfsm). The original project
  provides the daemon architecture, Niri event handling, Unix
  socket interface, fullscreen restoration behavior, and Nix
  packaging on which these changes are based.
