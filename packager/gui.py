"""Native desktop interface for the renOunce NRO packager."""

from pathlib import Path
import re
import sys

from PySide6.QtCore import QObject, QThread, QUrl, Signal, Slot, Qt
from PySide6.QtGui import QDesktopServices, QFont, QPixmap
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QFormLayout,
                               QFrame, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QMainWindow, QMessageBox, QProgressBar, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

from .build import build, engine_version, project_defaults
from .nro import read_nro

WORDS = {
    'es': {
        'title': 'renOunce · Empaquetador NRO', 'heading': 'Crear NRO',
        'intro': 'Empaqueta un juego Ren’Py para Switch 2.',
        'language': 'Idioma', 'engine_group': '1. Motor y proyecto',
        'details_group': '2. Datos del juego', 'preview_group': 'Vista previa',
        'output_group': '3. Salida', 'no_icon': 'Sin icono',
        'untitled': 'Nombre del juego', 'creator_prefix': 'Creador: {name}',
        'engine': 'Versión Ren’Py', 'detected': 'Motor detectado',
        'project': 'Carpeta del proyecto', 'base_nro': 'NRO base',
        'name': 'Nombre', 'author': 'Autor', 'version': 'Versión del juego',
        'game_id': 'ID de guardado', 'icon': 'Icono', 'output': 'Archivo NRO',
        'browse': 'Examinar…', 'create': 'Crear NRO', 'open': 'Abrir carpeta',
        'id_hint': 'Cada juego necesita un ID distinto. En 8.4.1: máximo 18 caracteres.',
        'project_hint': 'Carpeta que contiene game/', 'base_hint': 'Se selecciona por versión',
        'name_hint': 'Título mostrado en el menú', 'author_hint': 'Autor mostrado en el menú',
        'id_placeholder': 'Letras ASCII, números, punto, _ o -',
        'icon_hint': 'Opcional: PNG, JPEG, WebP o ICO', 'output_hint': 'Destino del NRO',
        'ready': 'Selecciona un proyecto para comenzar',
        'project_ready': 'Proyecto listo: {name}',
        'project_invalid': 'Selecciona una carpeta que contenga game/.',
        'base_missing': 'NRO base no encontrado', 'base_unknown': 'NRO base no reconocido',
        'base_mismatch': '{version} · No coincide con la versión elegida',
        'missing_engine': 'No se encontró el NRO base de Ren’Py {version}.',
        'wrong_version': 'El NRO base no corresponde a la versión seleccionada.',
        'incomplete': 'Completa nombre, autor, versión, ID y archivo de salida.',
        'invalid_id': 'El ID solo admite letras ASCII, números, punto, _ y -.',
        'long_id': 'Ren’Py 8.4.1 admite hasta 18 caracteres en el ID.',
        'missing_icon': 'Selecciona un archivo de icono existente.',
        'preparing': 'Preparando el NRO…', 'done': 'Empaquetado terminado',
        'result': 'NRO creado: {name}', 'failed': 'No se pudo crear el NRO',
        'error_title': 'Error al empaquetar', 'invalid_project_title': 'Proyecto inválido',
        'missing_engine_title': 'Falta el motor', 'invalid_base_title': 'NRO base inválido',
        'wrong_version_title': 'Versión incorrecta', 'incomplete_title': 'Datos incompletos',
        'invalid_id_title': 'ID inválido', 'long_id_title': 'ID demasiado largo',
        'missing_icon_title': 'Icono no encontrado',
        'project_dialog': 'Proyecto Ren’Py', 'save_dialog': 'Guardar NRO',
        'select_dialog': 'Seleccionar archivo',
    },
    'en': {
        'title': 'renOunce · NRO Packager', 'heading': 'Create NRO',
        'intro': 'Package a Ren’Py game for Switch 2.',
        'language': 'Language', 'engine_group': '1. Engine and project',
        'details_group': '2. Game details', 'preview_group': 'Preview',
        'output_group': '3. Output', 'no_icon': 'No icon',
        'untitled': 'Game title', 'creator_prefix': 'Creator: {name}',
        'engine': 'Ren’Py version', 'detected': 'Detected engine',
        'project': 'Project folder', 'base_nro': 'Base NRO',
        'name': 'Name', 'author': 'Author', 'version': 'Game version',
        'game_id': 'Save ID', 'icon': 'Icon', 'output': 'NRO file',
        'browse': 'Browse…', 'create': 'Create NRO', 'open': 'Open folder',
        'id_hint': 'Use a unique ID for each game. In 8.4.1: up to 18 characters.',
        'project_hint': 'Folder containing game/', 'base_hint': 'Selected by version',
        'name_hint': 'Title shown in the menu', 'author_hint': 'Author shown in the menu',
        'id_placeholder': 'ASCII letters, digits, dot, _ or -',
        'icon_hint': 'Optional: PNG, JPEG, WebP or ICO', 'output_hint': 'NRO destination',
        'ready': 'Select a project to begin',
        'project_ready': 'Project ready: {name}',
        'project_invalid': 'Select a folder containing game/.',
        'base_missing': 'Base NRO not found', 'base_unknown': 'Base NRO not recognized',
        'base_mismatch': '{version} · Does not match the selected version',
        'missing_engine': 'No base NRO was found for Ren’Py {version}.',
        'wrong_version': 'The base NRO does not match the selected version.',
        'incomplete': 'Enter a name, author, version, ID and output file.',
        'invalid_id': 'The ID only accepts ASCII letters, digits, dot, _ and -.',
        'long_id': 'Ren’Py 8.4.1 supports save IDs up to 18 characters.',
        'missing_icon': 'Select an existing icon file.',
        'preparing': 'Preparing the NRO…', 'done': 'Packaging complete',
        'result': 'NRO created: {name}', 'failed': 'Could not create the NRO',
        'error_title': 'Packaging error', 'invalid_project_title': 'Invalid project',
        'missing_engine_title': 'Engine missing', 'invalid_base_title': 'Invalid base NRO',
        'wrong_version_title': 'Wrong version', 'incomplete_title': 'Missing details',
        'invalid_id_title': 'Invalid ID', 'long_id_title': 'ID too long',
        'missing_icon_title': 'Icon not found',
        'project_dialog': 'Ren’Py project', 'save_dialog': 'Save NRO',
        'select_dialog': 'Select file',
    },
}

BACKEND_ERRORS_EN = {
    'Cabecera romfs no reconocida': 'Unrecognized romfs header',
    'romfs truncado': 'Truncated romfs',
    'Árbol de directorios romfs inválido': 'Invalid romfs directory tree',
    'Tabla de archivos romfs inválida': 'Invalid romfs file table',
    'Contenido romfs truncado': 'Truncated romfs content',
    'No es un NRO válido': 'Not a valid NRO',
    'El NRO no tiene sección ASET': 'The NRO has no ASET section',
    'Sección ASET truncada': 'Truncated ASET section',
    'NACP del motor no reconocido': 'Unrecognized engine NACP',
    'El motor 8.4.1 no contiene renounce_engine_boot.py': 'The 8.4.1 engine is missing renounce_engine_boot.py',
    'El arranque de Ren\'Py 8.4.1 no tiene el formato esperado': 'Unexpected Ren’Py 8.4.1 boot script format',
    'No se encontró la inicialización de Ren\'Py 8.4.1': 'Ren’Py 8.4.1 initialization was not found',
    'No se encontró el arranque de Ren\'Py 8.4.1': 'Ren’Py 8.4.1 startup was not found',
    'No se encontró path_to_saves en el arranque de Ren\'Py 8.4.1': 'path_to_saves was not found in the Ren’Py 8.4.1 boot script',
    'El bootstrap de Ren\'Py 8.4.1 no tiene el formato esperado': 'Unexpected Ren’Py 8.4.1 bootstrap format',
    'En Ren\'Py 8.4.1 el ID de guardado admite como máximo 18 caracteres': 'Ren’Py 8.4.1 save IDs can have at most 18 characters',
    'El NRO base de Ren\'Py 8.4.1 no tiene el ID nativo esperado': 'The 8.4.1 base NRO has an unexpected native save ID',
    'La carpeta game/ está vacía': 'The game/ folder is empty',
    'ID inválido: usa letras ASCII, números, punto, _ o - (máximo 126)': 'Invalid ID: use ASCII letters, digits, dot, _ or - (max 126)',
    'Nombre, autor y versión son obligatorios': 'Name, author and version are required',
    'Este NRO base no admite el ID de guardado empaquetado; recompila el motor actualizado': 'This base NRO cannot use a packaged save ID; rebuild the updated engine',
    'El NRO base no contiene Contents/': 'The base NRO is missing Contents/',
    'El NRO base no contiene lib.zip y renpy.py': 'The base NRO is missing lib.zip or renpy.py',
    'El NRO base contiene un lib.zip inválido': 'The base NRO contains an invalid lib.zip',
    'El NRO base tiene un lib.zip incompleto; faltan módulos de arranque o pygame_sdl2': 'The base NRO has an incomplete lib.zip; boot modules or pygame_sdl2 are missing',
}


class Worker(QObject):
    message = Signal(str)
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, args):
        super().__init__()
        self.args = args

    @Slot()
    def run(self):
        try:
            self.done.emit(str(build(**self.args, progress=self.message.emit)))
        except Exception as exc:
            self.failed.emit(str(exc))


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(760, 800)
        self.setMinimumSize(650, 570)
        self.thread = None
        self.fields = {}
        self.labels = {}
        self.browse_buttons = []
        self._base_preview_path = None
        self._base_preview_pixmap = QPixmap()
        self.bundle_root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
        self.lang = 'en'

        root = QWidget()
        outer = QVBoxLayout(root)
        header = QHBoxLayout()
        self.heading = QLabel()
        font = QFont(self.heading.font())
        font.setPointSize(font.pointSize() + 5)
        font.setBold(True)
        self.heading.setFont(font)
        header.addWidget(self.heading, 1)
        self.language_label = QLabel()
        header.addWidget(self.language_label)
        self.language_choice = QComboBox()
        self.language_choice.addItem('Español', 'es')
        self.language_choice.addItem('English', 'en')
        self.language_choice.setCurrentIndex(1)
        header.addWidget(self.language_choice)
        outer.addLayout(header)
        self.intro = QLabel()
        outer.addWidget(self.intro)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        self.engine_box = QGroupBox()
        engine_form = QFormLayout(self.engine_box)
        self.engine_choice = QComboBox()
        self.engine_choice.addItems(['7.6.1', '8.4.1'])
        self._add_row(engine_form, 'engine', self.engine_choice)
        self.engine_label = QLabel()
        self._add_row(engine_form, 'detected', self.engine_label)
        self._add_path(engine_form, 'project', 'dir')
        self._add_path(engine_form, 'base_nro', 'file')
        content_layout.addWidget(self.engine_box)

        self.details_box = QGroupBox()
        details_form = QFormLayout(self.details_box)
        for key in ('name', 'author', 'version', 'game_id'):
            field = QLineEdit()
            self.fields[key] = field
            self._add_row(details_form, key, field)
        self.id_hint = QLabel()
        details_form.addRow('', self.id_hint)
        self._add_path(details_form, 'icon', 'image')
        content_layout.addWidget(self.details_box)

        self.preview_box = QGroupBox()
        preview_layout = QHBoxLayout(self.preview_box)
        self.preview_icon = QLabel()
        self.preview_icon.setFixedSize(128, 128)
        self.preview_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_icon.setFrameShape(QFrame.Shape.Box)
        preview_layout.addWidget(self.preview_icon)
        preview_text = QVBoxLayout()
        self.preview_name = QLabel()
        preview_font = QFont(self.preview_name.font())
        preview_font.setPointSize(preview_font.pointSize() + 3)
        preview_font.setBold(True)
        self.preview_name.setFont(preview_font)
        self.preview_name.setWordWrap(True)
        preview_text.addWidget(self.preview_name)
        self.preview_creator = QLabel()
        self.preview_creator.setWordWrap(True)
        preview_text.addWidget(self.preview_creator)
        preview_text.addStretch()
        preview_layout.addLayout(preview_text, 1)
        content_layout.addWidget(self.preview_box)

        self.output_box = QGroupBox()
        output_form = QFormLayout(self.output_box)
        self._add_path(output_form, 'output', 'save')
        content_layout.addWidget(self.output_box)
        content_layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        footer = QHBoxLayout()
        self.status = QLabel()
        self.status.setWordWrap(True)
        footer.addWidget(self.status, 1)
        self.create_button = QPushButton()
        footer.addWidget(self.create_button)
        outer.addLayout(footer)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.hide()
        outer.addWidget(self.progress)
        result = QHBoxLayout()
        self.result_label = QLabel()
        result.addWidget(self.result_label, 1)
        self.open_button = QPushButton()
        self.open_button.clicked.connect(self.open_output_folder)
        result.addWidget(self.open_button)
        self.result_widget = QWidget()
        self.result_widget.setLayout(result)
        self.result_widget.hide()
        outer.addWidget(self.result_widget)
        self.setCentralWidget(root)

        self.fields['author'].setText('renOunce')
        self.language_choice.currentIndexChanged.connect(self.change_language)
        self.engine_choice.currentTextChanged.connect(self.engine_changed)
        self.fields['base_nro'].editingFinished.connect(self.base_changed)
        self.fields['project'].editingFinished.connect(self.project_changed)
        for key in ('name', 'author', 'icon'):
            self.fields[key].textChanged.connect(self.update_preview)
        self.create_button.clicked.connect(self.create)
        self.retranslate()
        self.engine_changed()

    def t(self, key, **values):
        return WORDS[self.lang][key].format(**values)

    def _add_row(self, form, key, widget):
        label = QLabel()
        self.labels[key] = label
        form.addRow(label, widget)

    def _add_path(self, form, key, picker):
        field = QLineEdit()
        self.fields[key] = field
        row = QWidget()
        horizontal = QHBoxLayout(row)
        horizontal.setContentsMargins(0, 0, 0, 0)
        horizontal.addWidget(field, 1)
        button = QPushButton()
        button.clicked.connect(lambda _=False, k=key, p=picker: self.browse(k, p))
        horizontal.addWidget(button)
        self.browse_buttons.append(button)
        self._add_row(form, key, row)

    def change_language(self):
        self.lang = self.language_choice.currentData()
        self.retranslate()

    def retranslate(self):
        self.setWindowTitle(self.t('title'))
        self.heading.setText(self.t('heading'))
        self.intro.setText(self.t('intro'))
        self.language_label.setText(self.t('language'))
        for box, key in ((self.engine_box, 'engine_group'),
                         (self.details_box, 'details_group'),
                         (self.preview_box, 'preview_group'), (self.output_box, 'output_group')):
            box.setTitle(self.t(key))
        for key, label in self.labels.items():
            label.setText(self.t(key))
        for button in self.browse_buttons:
            button.setText(self.t('browse'))
        self.fields['project'].setPlaceholderText(self.t('project_hint'))
        self.fields['base_nro'].setPlaceholderText(self.t('base_hint'))
        self.fields['name'].setPlaceholderText(self.t('name_hint'))
        self.fields['author'].setPlaceholderText(self.t('author_hint'))
        self.fields['game_id'].setPlaceholderText(self.t('id_placeholder'))
        self.fields['icon'].setPlaceholderText(self.t('icon_hint'))
        self.fields['output'].setPlaceholderText(self.t('output_hint'))
        self.id_hint.setText(self.t('id_hint'))
        self.create_button.setText(self.t('create'))
        self.open_button.setText(self.t('open'))
        self.base_changed()
        self.update_preview()
        if hasattr(self, 'output_path') and self.result_widget.isVisible():
            self.result_label.setText(self.t('result', name=self.output_path.name))
        elif self.fields['project'].text().strip() and (Path(self.fields['project'].text().strip()) / 'game').is_dir():
            self.status.setText(self.t('project_ready', name=Path(self.fields['project'].text()).name))
        else:
            self.status.setText(self.t('ready'))

    def browse(self, key, picker):
        current = self.fields[key].text().strip()
        if picker == 'dir':
            path = QFileDialog.getExistingDirectory(self, self.t('project_dialog'), current)
        elif picker == 'save':
            path, _ = QFileDialog.getSaveFileName(self, self.t('save_dialog'), current, 'NRO (*.nro)')
        else:
            filters = 'NRO (*.nro)' if picker == 'file' else 'Images (*.png *.jpg *.jpeg *.webp *.ico)'
            path, _ = QFileDialog.getOpenFileName(self, self.t('select_dialog'), current, filters)
        if path:
            self.fields[key].setText(path)
            if key == 'project':
                self.project_changed()
            elif key == 'base_nro':
                self.base_changed()

    def base_changed(self):
        text = self.fields['base_nro'].text().strip()
        if not text or not Path(text).is_file():
            self.engine_label.setText(self.t('base_missing'))
            self.update_preview()
            return
        try:
            version = engine_version(text)
            self.engine_label.setText(version if version == self.engine_choice.currentText()
                                      else self.t('base_mismatch', version=version))
        except (OSError, ValueError):
            self.engine_label.setText(self.t('base_unknown'))
        self.update_preview()

    def update_preview(self):
        self.preview_name.setText(self.fields['name'].text().strip() or self.t('untitled'))
        self.preview_creator.setText(self.t('creator_prefix',
                                            name=self.fields['author'].text().strip() or '—'))
        pixmap = QPixmap()
        icon = self.fields['icon'].text().strip()
        if icon and Path(icon).is_file():
            pixmap.load(icon)
        elif not icon:
            base = self.fields['base_nro'].text().strip()
            if base and Path(base).is_file():
                if base != self._base_preview_path:
                    self._base_preview_path = base
                    self._base_preview_pixmap = QPixmap()
                    try:
                        blob, assets, sections = read_nro(base)
                        offset, length = sections[0]
                        self._base_preview_pixmap.loadFromData(blob[assets + offset:assets + offset + length])
                    except (OSError, ValueError):
                        pass
                pixmap = self._base_preview_pixmap
        if pixmap.isNull():
            self.preview_icon.setPixmap(QPixmap())
            self.preview_icon.setText(self.t('no_icon'))
        else:
            self.preview_icon.setText('')
            self.preview_icon.setPixmap(pixmap.scaled(126, 126,
                Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def engine_changed(self):
        base = self.bundle_root / f'renounce-base-{self.engine_choice.currentText()}.nro'
        self.fields['base_nro'].setText(str(base) if base.is_file() else '')
        self.base_changed()

    def project_changed(self):
        text = self.fields['project'].text().strip()
        project = Path(text) if text else None
        if project is None or not (project / 'game').is_dir():
            self.status.setText(self.t('project_invalid'))
            return
        name, version = project_defaults(project)
        self.fields['name'].setText(name)
        self.fields['version'].setText(version)
        game_id = ''.join(c if c.isascii() and (c.isalnum() or c in '._-') else '_' for c in name) or 'game'
        if self.engine_choice.currentText() == '8.4.1':
            game_id = game_id[:18]
        self.fields['game_id'].setText(game_id)
        self.fields['output'].setText(str(project.parent / (game_id + '.nro')))
        for candidate in (project / 'game/icon.png', project / 'game/gui/window_icon.png'):
            if candidate.is_file():
                self.fields['icon'].setText(str(candidate))
                break
        self.status.setText(self.t('project_ready', name=project.name))
        self.result_widget.hide()

    def _error(self, title, message):
        self.status.setText(self.t(message))
        QMessageBox.warning(self, self.t(title), self.t(message))

    def show_progress(self, message):
        if self.lang == 'en':
            translations = {
                'Leyendo el NRO base…': 'Reading the base NRO…',
                'Añadiendo archivos del juego…': 'Adding game files…',
                'Reconstruyendo romfs y NRO…': 'Building romfs and NRO…',
            }
            message = translations.get(message, message)
        self.status.setText(message)

    def create(self):
        values = {key: field.text().strip() for key, field in self.fields.items()}
        if not values['project'] or not (Path(values['project']) / 'game').is_dir():
            self._error('invalid_project_title', 'project_invalid')
            return
        if not values['base_nro']:
            self.status.setText(self.t('missing_engine', version=self.engine_choice.currentText()))
            QMessageBox.warning(self, self.t('missing_engine_title'), self.status.text())
            return
        try:
            selected_version = engine_version(values['base_nro'])
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, self.t('invalid_base_title'), str(exc))
            return
        if selected_version != self.engine_choice.currentText():
            self._error('wrong_version_title', 'wrong_version')
            return
        if not all(values[key] for key in ('name', 'author', 'version', 'game_id', 'output')):
            self._error('incomplete_title', 'incomplete')
            return
        if not re.fullmatch(r'[A-Za-z0-9._-]+', values['game_id']) or values['game_id'] in ('.', '..'):
            self._error('invalid_id_title', 'invalid_id')
            return
        if selected_version == '8.4.1' and len(values['game_id']) > 18:
            self._error('long_id_title', 'long_id')
            return
        if values['icon'] and not Path(values['icon']).is_file():
            self._error('missing_icon_title', 'missing_icon')
            return
        args = {key: value for key, value in values.items() if key != 'icon'}
        args['icon'] = values['icon'] or None
        self.result_widget.hide()
        self.create_button.setEnabled(False)
        self.progress.setRange(0, 0)
        self.progress.show()
        self.status.setText(self.t('preparing'))
        self.thread = QThread(self)
        self.worker = Worker(args)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.message.connect(self.show_progress)
        self.worker.done.connect(self.finished)
        self.worker.failed.connect(self.failed)
        self.worker.done.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def finished(self, output):
        self.create_button.setEnabled(True)
        self.progress.hide()
        self.output_path = Path(output).resolve()
        self.status.setText(self.t('done'))
        self.result_label.setText(self.t('result', name=self.output_path.name))
        self.result_widget.show()

    def failed(self, message):
        self.create_button.setEnabled(True)
        self.progress.hide()
        self.status.setText(self.t('failed'))
        if self.lang == 'en':
            message = BACKEND_ERRORS_EN.get(message, message)
            if message.startswith('No existe '):
                message = 'Missing folder: ' + message[len('No existe '):]
            elif message.startswith('El juego contiene un enlace simbólico: '):
                message = 'The game contains a symbolic link: ' + message.split(': ', 1)[1]
            elif message.startswith('Texto demasiado largo: '):
                message = 'Text is too long: ' + message.split(': ', 1)[1]
            elif message.startswith('El motor Ren\'Py ') and 'aún no está admitido' in message:
                version = message.split(' ')[3]
                message = f'Ren’Py {version} is not supported by this packager yet'
        QMessageBox.critical(self, self.t('error_title'), message)

    def open_output_folder(self):
        if hasattr(self, 'output_path'):
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_path.parent)))


def main():
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
