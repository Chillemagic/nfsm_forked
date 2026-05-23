{ lib, libnotify, socat, writeShellApplication }:

let
  name = "nfsm-cli";
in
writeShellApplication {
  inherit name;
  runtimeInputs = [ libnotify socat ];
  text = ''
    SOCKET=''${NFSM_SOCKET:-/run/user/1000/nfsm.sock}
    CMD=''${1:-fullscreen}

    case "$CMD" in
      fullscreen)
        NIRI_ACTION="fullscreen-window"
        SOCKET_CMD="FullscreenRequest"
        ;;
      maximize)
        NIRI_ACTION="maximize-window-to-edges"
        SOCKET_CMD="MaximizeRequest"
        ;;
      *)
        echo "Unknown command: $CMD" >&2
        exit 1
        ;;
    esac

    trap 'notify-send --icon="${./assets/icon.png}" --app-name="NFSM" "Niri FullScreen Manager" "Failed to connect to NFSM_SOCKET: $SOCKET" && niri msg action "$NIRI_ACTION"' ERR
    echo "$SOCKET_CMD" | socat - UNIX-CONNECT:"$SOCKET"
  '';

  meta = {
    description = "Niri FullScreen Manager Client (nfsm-cli)";
    homepage = "https://github.com/gvolpe/nfsm";
    license = lib.licenses.asl20;
    maintainers = with lib.maintainers; [ gvolpe ];
    mainProgram = name;
    platforms = lib.platforms.linux;
  };
}
