{
    inputs.nixpkgs.url = "nixpkgs";

    outputs = { nixpkgs, ... }:
        let
            pkgs = nixpkgs.legacyPackages.x86_64-linux;
            python = pkgs.python313;
        in {
            packages.x86_64-linux.default = pkgs.writeShellApplication {
                name = "calendar";
                runtimeInputs = [ python ];
                text = ''
                    export PYTHONPATH="${./.}:''${PYTHONPATH:-}"
                    cd ${./.} ; exec ${python}/bin/python main.py "$@"
                '';
            };

            devShells.x86_64-linux.default = pkgs.mkShell {
                packages = [ python ];
            };
        };
}
