self:
{
  lib,
  config,
  pkgs,
  ...
}:
let
  inherit (lib)
    mkOption
    mkEnableOption
    mkIf
    types
    getExe'
    ;
  inherit (pkgs.stdenv.hostPlatform) system;
  inherit (self.packages.${system}) nfsm nfsm-cli;

  cfg = config.services.nfsm;
in
{
  options.services.nfsm = {
    enable = mkEnableOption "Fullscreen manager for niri";
    package = mkOption {
      type = types.package;
      default = nfsm;
      description = "nfsm package to use";
    };
    cliPackage = mkOption {
      type = types.package;
      default = nfsm-cli;
      description = "nfsm-cli package to use";
    };
    enableCli = (mkEnableOption "Install nfsm-cli to system") // {
      default = true;
    };
    socketPath = mkOption {
      type = types.str;
      default = "/run/user/1000/nfsm.sock";
      description = "Will open a Unix Socket under this path. This value will set `NFSM_SOCKET` environment variable.";
    };
  };

  config = mkIf cfg.enable {
    systemd.user.services.nfsm = {
      Install = {
        WantedBy = [ "graphical-session.target" ];
      };
      Service = {
        ExecStart = "${getExe' cfg.package "nfsm"}";
        Environment = [
          "NFSM_SOCKET=${cfg.socketPath}"
        ];
        Restart = "on-failure";
        RestartSec = "1";
      };
    };

    home.packages = mkIf cfg.enableCli [
      cfg.cliPackage
    ];
  };
}
