self: { config, lib, pkgs, ... }:

let
  cfg = config.services.samsung-grab;
  arch = config.nixpkgs.hostPlatform.system;
  samsung-grab = self.packages.${arch}.default;
  samsung-grab-wrapped = pkgs.writeShellScriptBin "samsung-grab" ''
    exec ${lib.getExe pkgs.sudo} --user samsung-grab \
      SAMSUNGGRAB_DB=/var/lib/samsung-grab/samsung-grab.json \
      ${lib.getExe samsung-grab} "$@"
  '';
in
{
  options.services.samsung-grab = {
    enable = lib.mkEnableOption "samsung-grab notifications";
    notify = lib.mkOption {
      type = lib.types.str;
      description = "Apprise notification URL";
      default = "";
    };
    notifyFile = lib.mkOption {
      type = lib.types.str;
      description = "File path to Apprise notification URL";
      default = "";
    };
    username = lib.mkOption {
      type = lib.types.str;
      description = "Leaderboard username";
    };
    timerConfig = lib.mkOption {
      type = lib.types.str;
      description = "How often to check for new tasks";
      default = "*:0/15";
    };
  };
  config = lib.mkIf cfg.enable {
    users = {
      groups.samsung-grab = { };
      users.samsung-grab = {
        isSystemUser = true;
        group = "samsung-grab";
      };
    };
    systemd.timers.samsung-grab = {
      wantedBy = [ "timers.target" ];
      timerConfig = {
        OnCalendar = cfg.timerConfig;
        Unit = "samsung-grab.service";
      };
    };
    systemd.tmpfiles.rules = [
      "d /var/lib/samsung-grab 0755 samsung-grab samsung-grab -"
    ];
    systemd.services.samsung-grab = {
      description = "samsung-grab notifications";
      after = [ "network.target" ];
      environment.SAMSUNGGRAB_DB = "/var/lib/samsung-grab/samsung-grab.json";
      serviceConfig = {
        Type = "exec";
        KillMode = "process";
        ExecStart = lib.concatStringsSep " " (
        [
          (lib.getExe samsung-grab)
          "task ${cfg.username} -a"
          (lib.optionalString (cfg.notify != "") "-N ${cfg.notify}")
          (lib.optionalString (cfg.notifyFile != "") "-N ${cfg.notifyFile}")
        ]
      );
        User = "samsung-grab";
        Group = "samsung-grab";
        PrivateDevices = true;
        PrivateTmp = true;
        ProtectHome = true;
        ProtectSystem = "strict";
        RemoveIPC = true;
        RestrictSUIDSGID = true;
        StateDirectory = "samsung-grab";
      };
    };
    environment.systemPackages = [ samsung-grab-wrapped ];
  };
}
