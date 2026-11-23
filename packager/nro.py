"""Minimal NRO asset and Nintendo RomFS reader/writer for renOunce."""

from dataclasses import dataclass, field
from pathlib import Path
import struct

NONE = 0xffffffff


def align(value, amount=4):
    return (value + amount - 1) & ~(amount - 1)


def u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


@dataclass
class Directory:
    name: str
    dirs: dict = field(default_factory=dict)
    files: dict = field(default_factory=dict)
    offset: int = 0
    parent: int = 0


@dataclass
class File:
    name: str
    data: bytes | memoryview
    offset: int = 0
    parent: int = 0
    data_offset: int = 0


def read_romfs(data):
    header = struct.unpack_from('<10Q', data)
    if header[0] != 0x50:
        raise ValueError('Cabecera romfs no reconocida')
    _, _, _, dirs_at, dirs_len, _, _, files_at, files_len, data_at = header
    if max(dirs_at + dirs_len, files_at + files_len, data_at) > len(data):
        raise ValueError('romfs truncado')
    dirs = data[dirs_at:dirs_at + dirs_len]
    files = data[files_at:files_at + files_len]
    seen_dirs = set()
    seen_files = set()

    def read_dir(offset):
        if offset in seen_dirs or offset + 24 > len(dirs):
            raise ValueError('Árbol de directorios romfs inválido')
        seen_dirs.add(offset)
        parent, sibling, child_dir, child_file, _, name_len = struct.unpack_from('<6I', dirs, offset)
        name = bytes(dirs[offset + 24:offset + 24 + name_len]).decode('utf-8')
        node = Directory(name)
        child = child_dir
        while child != NONE:
            entry = read_dir(child)
            node.dirs[entry.name] = entry
            child = u32(dirs, child + 4)
        child = child_file
        while child != NONE:
            if child in seen_files or child + 32 > len(files):
                raise ValueError('Tabla de archivos romfs inválida')
            seen_files.add(child)
            _, next_file, data_offset, size, _, nlen = struct.unpack_from('<IIQQII', files, child)
            filename = bytes(files[child + 32:child + 32 + nlen]).decode('utf-8')
            start = data_at + data_offset
            if start + size > len(data):
                raise ValueError('Contenido romfs truncado')
            node.files[filename] = File(filename, data[start:start + size])
            child = next_file
        return node

    return read_dir(0)


def _hash(parent, name, buckets):
    value = parent ^ 123456789
    for byte in name.encode('utf-8'):
        value = (((value >> 5) | (value << 27)) & NONE) ^ byte
    return value % buckets


def write_romfs(root):
    directory_nodes = []
    file_nodes = []
    dir_size = 0
    file_size = 0

    def assign(directory, parent):
        nonlocal dir_size, file_size
        directory.offset = dir_size
        directory.parent = parent
        directory_nodes.append(directory)
        dir_size += align(24 + len(directory.name.encode('utf-8')))
        for child in directory.dirs.values():
            assign(child, directory.offset)
        for child in directory.files.values():
            child.offset = file_size
            child.parent = directory.offset
            file_nodes.append(child)
            file_size += align(32 + len(child.name.encode('utf-8')))

    assign(root, 0)
    # A prime-sized bucket table keeps chains short; the reader also uses it
    # for normal path lookup, so all entries must appear in these tables.
    def bucket_count(count):
        size = max(3, count * 2 + 1)
        while any(size % divisor == 0 for divisor in range(2, int(size ** .5) + 1)):
            size += 1
        return size

    dir_buckets = [NONE] * bucket_count(len(directory_nodes))
    file_buckets = [NONE] * bucket_count(len(file_nodes))
    dir_table = bytearray(dir_size)
    file_table = bytearray(file_size)
    data = bytearray()

    for directory in directory_nodes:
        offset = directory.offset
        children = list(directory.dirs.values())
        owned_files = list(directory.files.values())
        bucket = _hash(directory.parent, directory.name, len(dir_buckets))
        hash_next = dir_buckets[bucket]
        dir_buckets[bucket] = offset
        sibling = NONE
        if directory.parent != offset:
            siblings = list(next(d for d in directory_nodes if d.offset == directory.parent).dirs.values())
            index = siblings.index(directory)
            if index + 1 < len(siblings):
                sibling = siblings[index + 1].offset
        name = directory.name.encode('utf-8')
        struct.pack_into('<6I', dir_table, offset, directory.parent, sibling,
                         children[0].offset if children else NONE,
                         owned_files[0].offset if owned_files else NONE,
                         hash_next, len(name))
        dir_table[offset + 24:offset + 24 + len(name)] = name

    for directory in directory_nodes:
        owned_files = list(directory.files.values())
        for index, file in enumerate(owned_files):
            file.data_offset = align(len(data), 0x10)
            data.extend(b'\0' * (file.data_offset - len(data)))
            data.extend(file.data)
            bucket = _hash(file.parent, file.name, len(file_buckets))
            hash_next = file_buckets[bucket]
            file_buckets[bucket] = file.offset
            name = file.name.encode('utf-8')
            sibling = owned_files[index + 1].offset if index + 1 < len(owned_files) else NONE
            struct.pack_into('<IIQQII', file_table, file.offset, file.parent, sibling,
                             file.data_offset, len(file.data), hash_next, len(name))
            file_table[file.offset + 32:file.offset + 32 + len(name)] = name

    def bucket_bytes(values):
        return struct.pack('<' + 'I' * len(values), *values)

    data_at = 0x200
    dirs_hash = align(data_at + len(data))
    dirs_meta = align(dirs_hash + 4 * len(dir_buckets))
    files_hash = align(dirs_meta + len(dir_table))
    files_meta = align(files_hash + 4 * len(file_buckets))
    result = bytearray(files_meta + len(file_table))
    struct.pack_into('<10Q', result, 0, 0x50, dirs_hash, 4 * len(dir_buckets),
                     dirs_meta, len(dir_table), files_hash, 4 * len(file_buckets),
                     files_meta, len(file_table), data_at)
    result[data_at:data_at + len(data)] = data
    result[dirs_hash:dirs_hash + 4 * len(dir_buckets)] = bucket_bytes(dir_buckets)
    result[dirs_meta:dirs_meta + len(dir_table)] = dir_table
    result[files_hash:files_hash + 4 * len(file_buckets)] = bucket_bytes(file_buckets)
    result[files_meta:files_meta + len(file_table)] = file_table
    return bytes(result)


def read_nro(path):
    blob = Path(path).read_bytes()
    if blob[0x10:0x14] != b'NRO0':
        raise ValueError('No es un NRO válido')
    assets = u32(blob, 0x18)
    if blob[assets:assets + 4] != b'ASET':
        raise ValueError('El NRO no tiene sección ASET')
    sections = [struct.unpack_from('<QQ', blob, assets + 8 + i * 16) for i in range(3)]
    for offset, length in sections:
        if assets + offset + length > len(blob):
            raise ValueError('Sección ASET truncada')
    return blob, assets, sections


def write_nro(base, romfs, nacp=None, icon=None):
    blob, assets, sections = read_nro(base)
    parts = [blob[assets + offset:assets + offset + length] for offset, length in sections]
    if icon is not None:
        parts[0] = icon
    if nacp is not None:
        parts[1] = nacp
    parts[2] = romfs
    result = bytearray(blob[:assets])
    result.extend(b'ASET\0\0\0\0' + b'\0' * 48)
    for index, part in enumerate(parts):
        struct.pack_into('<QQ', result, assets + 8 + index * 16, len(result) - assets, len(part))
        result.extend(part)
    return bytes(result)
