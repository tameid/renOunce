# renounce Ren'Py 8.4.1 for Nintendo Switch 2

Ren'Py 8.4.1 with Python 3.12 for Nintendo Switch 2, built with libounce.
The NRO does not include a game. The engine assets and Python standard
library are bundled in RomFS.

## Download

- `renounce-renpy-8.4.1.nro`
- SHA-256: `ca806669449141058b36386d8ae1f397ef6642efd998a9b5819fea53ce8db3e0`

Place the NRO in a subdirectory on the SD card. Runtime data is stored in
`renounce/renpy-8.4.1-engine/` beside the NRO. `Data` holds saves;
`cache` and `Logs` hold engine data. The SD fallback `tmp` directory is
cleared on exit and at the next startup. No files are created at the SD root.

This package provides the engine. A separate application can eventually
prepare a compatible game without rebuilding the engine; that integration
is not part of this release.
