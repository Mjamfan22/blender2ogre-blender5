"""Bounded, read-only lookup of shared asset-pack resources (LGPL 2.1+)."""
from pathlib import Path
import os
from ..report import Report

PACK_MARKERS = {'.truck', '.car', '.boat', '.airplane', '.load', '.terrn2'}


def pack_root(folder):
    folder = Path(folder).resolve()
    # Only a nearby recognized resource pack authorizes automatic traversal.
    # An ordinary standalone mesh never triggers a scan of its whole drive.
    for parent in (folder, *list(folder.parents)[:4]):
        if parent.parent == parent:
            break
        try:
            with os.scandir(parent) as entries:
                for i, item in enumerate(entries):
                    if i >= 2000:
                        break
                    if item.is_file(follow_symlinks=False) and (
                        Path(item.name).suffix.lower() in PACK_MARKERS or
                        item.name.lower() in ('resources.cfg', 'resource.cfg')):
                        return parent
        except OSError:
            continue
    return folder


class ResourceIndex:
    def __init__(self, folder, resource_folder=''):
        self.folder = Path(folder).resolve()
        root = Path(resource_folder).expanduser().resolve() if resource_folder else pack_root(folder)
        self.roots = list(dict.fromkeys((self.folder, root)))
        self._files = None

    def warn(self, message):
        if message not in Report.warnings:
            Report.warnings.append(message)

    def allowed(self, path):
        path = Path(path).resolve()
        return any(path.is_relative_to(root) for root in self.roots)

    def files(self):
        if self._files is not None:
            return self._files
        files, visited = [], set()
        directories = 0
        for root in sorted(self.roots, key=lambda p: len(p.parts)):
            for base, dirs, names in os.walk(root, followlinks=False):
                base = Path(base).resolve()
                if base in visited:
                    dirs[:] = []
                    continue
                visited.add(base)
                directories += 1
                if directories > 2048 or len(files) > 50000:
                    self.warn('Asset resource scan limit reached under: ' + str(root))
                    self._files = files
                    return files
                dirs[:] = sorted(d for d in dirs if not d.startswith('.') and d not in
                    ('ChatGPT', '__pycache__', 'node_modules') and
                    not (base/d).is_symlink() and not os.path.isjunction(base/d) and
                    len((base/d).relative_to(root).parts) <= 12)
                for name in sorted(names):
                    if len(files) >= 50000:
                        self.warn('Asset resource scan limit reached under: ' + str(root))
                        self._files = files
                        return files
                    path = base/name
                    if not path.is_symlink() and self.allowed(path):
                        files.append(path)
        self._files = files
        return files

    def find(self, name, source_folder=None):
        name = str(name).replace('\\', '/')
        folders = list(dict.fromkeys((Path(source_folder or self.folder).resolve(), self.folder, *self.roots)))
        for folder in folders:
            candidate = (folder/name).resolve()
            if self.allowed(candidate) and candidate.is_file():
                return candidate
        suffix = name.casefold().lstrip('./')
        matches = [p for p in self.files() if p.name.casefold() == Path(name).name.casefold()]
        if '/' in suffix:
            exact = [p for p in matches if p.as_posix().casefold().endswith('/'+suffix)]
            if exact:
                matches = exact
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            self.warn('Ambiguous asset resource "%s": %s. Choose a Resource Folder or an explicit relative path.' %
                (name, ', '.join(str(p) for p in matches[:6])))
        return None

    def material_files(self):
        return [p for p in self.files() if p.suffix.lower() == '.material']
