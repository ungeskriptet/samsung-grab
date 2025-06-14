{ config, lib, dream2nix, ... }:

let
  pyproject = lib.importTOML (config.mkDerivation.src + /pyproject.toml);
in
{
  imports = [ dream2nix.modules.dream2nix.pip ];

  deps = {nixpkgs, ...}: {
    python = nixpkgs.python3;
  };

  inherit (pyproject.project) name version;

  mkDerivation = {
    src = lib.cleanSourceWith {
      src = lib.cleanSource ./.;
      filter = name: type:
        !(builtins.any (x: x) [
          (lib.hasSuffix ".nix" name)
          (lib.hasPrefix "." (builtins.baseNameOf name))
          (lib.hasSuffix "flake.lock" name)
        ]);
    };
  };

  buildPythonPackage = {
    pyproject = true;
    pythonImportsCheck = [
      "samsung_grab"
    ];
  };

  pip = {
    requirementsList =
      pyproject.build-system.requires
      ++ pyproject.project.dependencies;

    flattenDependencies = true;
  };
}
