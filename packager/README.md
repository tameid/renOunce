# renOunce Packager

Aplicación gráfica para convertir un proyecto Ren'Py 7.6.1 u 8.4.1 en un NRO de
Switch 2 sin instalar devkitPro, CMake ni Podman en el equipo del usuario.

## Preparar la publicación (desarrolladores)

1. Compilar el motor actualizado con `build-engine.bash 7.6.1` dentro del
   entorno de desarrollo. El NRO debe contener la cadena
   `romfs:/Contents/renounce-game-id`; el empaquetador la comprueba.
2. Copiar el NRO resultante a `packager/renounce-base-7.6.1.nro`.
   Para 8.4.1, preparar `packager/renounce-base-8.4.1.nro` a partir del
   NRO de motor Python 3 de esa versión. Su `lib.zip` debe incluir
   `renounce_engine_boot.py` y `pygame_sdl2`, y el ejecutable debe
   enlazar los módulos nativos `fcntl` y `_ctypes`.
3. Instalar `packager/requirements.txt` y generar la aplicación:

   ```sh
   python3 -m PyInstaller --noconfirm --windowed --name renOunce-Packager \
     --add-data 'packager/renounce-base-7.6.1.nro:.' \
     --add-data 'packager/renounce-base-8.4.1.nro:.' \
     --collect-all PySide6 --collect-all PIL \
     packager_gui.py
   ```

   Ejecutar desde la raíz del repositorio. Adaptar el separador de
   `--add-data` a `;` en Windows. Publicar la carpeta resultante de `dist/`.

## Uso

Abrir la aplicación, elegir la versión de Ren'Py, seleccionar la carpeta del
proyecto que contiene `game/`, revisar los datos y pulsar **Crear NRO**. Si
la aplicación incluye los NRO base, su ruta aparece automáticamente. La
ventana usa los controles nativos del sistema y permite cambiar entre
Español e Inglés desde el selector superior; Inglés es el idioma inicial.
La vista previa muestra el icono, el nombre y el creador a medida que se
editan. El archivo generado incluye
los recursos del motor, el juego, el icono y los metadatos. **Motor detectado**
indica la versión del NRO base; **Versión del juego** es el número que se
muestra en los metadatos del juego. `lib.zip` se construye una vez durante
la preparación del motor (`build.bash`) y se conserva dentro del NRO base;
la aplicación no necesita construirlo. Cada juego usa una carpeta de
guardados propia identificada por su ID.

La aplicación admite otro NRO base en el selector para desarrolladores. El
motor 7.6.1 lee el ID de guardado desde romfs en C. El motor 8.4.1 usa
`renounce_engine_boot.py` dentro de `lib.zip`; el empaquetador lo adapta
para leer el mismo ID y sustituye el ID fijo del lanzador nativo. Así no
se crea la carpeta `renpy-8.4.1-engine/` con los nuevos NRO. El ID de 8.4.1
admite hasta 18 caracteres ASCII, el espacio disponible en el ejecutable
base para ese dato.
