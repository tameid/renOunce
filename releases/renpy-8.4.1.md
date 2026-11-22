# renounce Ren'Py 8.4.1 para Nintendo Switch 2

Motor Ren'Py 8.4.1 con Python 3.12 para Nintendo Switch 2, compilado con
libounce. El NRO no contiene ningún juego. Los recursos del motor y la
biblioteca de Python están integrados en RomFS.

## Archivo

- `renounce-renpy-8.4.1.nro`
- SHA-256: `ca806669449141058b36386d8ae1f397ef6642efd998a9b5819fea53ce8db3e0`

Coloca el NRO en una subcarpeta de la tarjeta SD. Sus datos se guardan en
`renounce/renpy-8.4.1-engine/` junto al NRO. `Data` contiene las partidas;
`cache` y `Logs` guardan los datos del motor. `tmp` se limpia al cerrar y
en el siguiente arranque. No se crean archivos en la raíz de la SD.

Este paquete proporciona el motor. Una aplicación externa podrá preparar
un juego compatible sin recompilar el motor; esa integración todavía no
forma parte de esta entrega.
