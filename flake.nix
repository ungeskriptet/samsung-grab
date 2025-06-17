{
  description = "Flake for samsung-grab";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
  let
    eachSystem = nixpkgs.lib.genAttrs [
      "aarch64-linux"
      "x86_64-linux"
    ];
  in {
    packages = eachSystem (system: {
      default = self.packages.${system}.samsung-grab;
      samsung-grab = nixpkgs.legacyPackages.${system}.callPackage ./pkg.nix { };
    });

    nixosModules.default = self.nixosModules.samsung-grab;
    nixosModules.samsung-grab = import ./config.nix self;
  };
}
