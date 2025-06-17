{
  lib,
  python3Packages,
}:

python3Packages.buildPythonPackage {
  pname = "samsung-grab";
  version = "0-unstable-2025-06-17";
  pyproject = true;

  src = ./.;

  build-system = with python3Packages; [
    pdm-backend
  ];

  dependencies = with python3Packages; [
    apprise
    beautifulsoup4
    lxml
    requests
    tinydb
    tqdm
  ];

  meta = {
    description = "Python client for samsung-grab";
    homepage = "https://github.com/ungeskriptet/samsung-grab";
    mainProgram = "samsung-grab";
  };
}
