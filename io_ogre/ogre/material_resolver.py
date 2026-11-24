"""Resolve local OGRE material imports, inheritance and variables.

LGPL 2.1 or later. This expands data only; shader programs are never executed.
The existing importer still reads the first technique/pass and its basic maps.
"""
from pathlib import Path
from copy import deepcopy
import logging
from ..report import Report

logger = logging.getLogger('material_resolver')


class MaterialResolver:
    def __init__(self, folder, resource_folder=''):
        from .resource_index import ResourceIndex
        self.folder = Path(folder).resolve()
        self.resources = ResourceIndex(folder, resource_folder)
        self.loaded = set()
        self.definitions = {}
        self.abstract = set()
        self.globals = {}
        self.templates = {}
        self.sources = {}

    def warn(self, message):
        logger.warning(message)
        if message not in Report.warnings:
            Report.warnings.append(message)

    def parse(self, text, source):
        from .material_parser import ScriptLexer, ScriptToken as T
        lexer = ScriptLexer()
        tokens = lexer.tokenize(text, str(source))
        if lexer.error:
            raise ValueError(lexer.error)
        index = 0

        def block(depth=0):
            nonlocal index
            if depth > 64:
                raise ValueError('Material nesting exceeds 64 levels')
            nodes = []
            while index < len(tokens):
                while index < len(tokens) and tokens[index].type == T.TID_NEWLINE:
                    index += 1
                if index == len(tokens):
                    break
                if tokens[index].type == T.TID_RBRACKET:
                    index += 1
                    break
                header = []
                while index < len(tokens) and tokens[index].type not in (T.TID_LBRACKET, T.TID_RBRACKET, T.TID_NEWLINE):
                    header.append(':' if tokens[index].type == T.TID_COLON else tokens[index].lexeme)
                    index += 1
                while index < len(tokens) and tokens[index].type == T.TID_NEWLINE:
                    index += 1
                children = None
                if index < len(tokens) and tokens[index].type == T.TID_LBRACKET:
                    index += 1
                    children = block(depth+1)
                if header:
                    nodes.append((header, children))
                elif children is None:
                    raise ValueError('Unexpected material token')
            return nodes
        return block()

    @staticmethod
    def unquote(value):
        return value[1:-1] if len(value) >= 2 and value[0] == value[-1] == '"' else value

    def load(self, path):
        path = Path(path).resolve()
        if path in self.loaded:
            return
        if not self.resources.allowed(path) or not path.is_file():
            self.warn('Material import is missing or outside the asset folder: ' + str(path))
            return
        if len(self.loaded) >= 256 or path.stat().st_size > 8*1024*1024:
            raise ValueError('Material import limit exceeded')
        self.loaded.add(path)
        nodes = self.parse(path.read_text(encoding='utf-8-sig'), path)
        for header, children in nodes:
            if header[0] == 'import' and len(header) >= 4 and header[-2] == 'from':
                pattern = self.unquote(header[-1])
                candidate = path.parent/pattern
                if '*' in pattern or '?' in pattern:
                    # OGRE resource groups are not available here. Limit imports
                    # to local .material assets, never scan outside this folder.
                    if self.resources.allowed(candidate.parent):
                        matches = sorted(candidate.parent.glob(candidate.name))
                        if not matches:
                            self.warn('Material import has no matches: ' + pattern)
                        for match in matches:
                            if match.suffix.lower() == '.material':
                                self.load(match)
                else:
                    found = self.resources.find(pattern, path.parent)
                    if found:
                        self.load(found)
                    else:
                        self.warn('Material script not found in the asset resources: ' + pattern)
            elif header[0] == 'set' and len(header) >= 3:
                self.globals[header[1]] = header[2:]
        # Local declarations override imported declarations of the same name.
        for header, children in nodes:
            if header[0] in ('material', 'pass', 'technique', 'texture_unit', 'abstract'):
                abstract = header[0] == 'abstract'
                if header[0] == 'abstract':
                    header = header[1:]
                if len(header) >= 2 and header[0] in ('material', 'pass', 'technique', 'texture_unit'):
                    name = self.unquote(header[1])
                    key = header[0], name
                    previous = self.sources.get(key)
                    if previous and previous.parent == self.folder and path.parent != self.folder:
                        continue
                    self.templates[key] = (header, children or [])
                    self.sources[key] = path
                    if header[0] != 'material':
                        continue
                    self.definitions[name] = (header, children or [])
                    if abstract:
                        self.abstract.add(name)
                    else:
                        self.abstract.discard(name)

    @staticmethod
    def merge(base, overrides):
        """Merge named objects, or unnamed objects by their ordinal, like OGRE."""
        result = deepcopy(base)
        ordinals = {}
        for header, children in overrides:
            kind = header[0]
            if children is None:
                key = header[:2] if kind == 'set' else header[:1]
                matches = [i for i,(h,c) in enumerate(result) if c is None and h[:len(key)] == key]
            elif len(header) > 1:
                matches = [i for i,(h,c) in enumerate(result) if c is not None and
                    [MaterialResolver.unquote(v) for v in h] == [MaterialResolver.unquote(v) for v in header]]
            else:
                ordinal = ordinals.get(kind, 0)
                ordinals[kind] = ordinal+1
                matches = [i for i,(h,c) in enumerate(result) if c is not None and h == header][ordinal:ordinal+1]
            if matches:
                i = matches[0]
                result[i] = (header, MaterialResolver.merge(result[i][1],children) if children is not None else None)
            else:
                result.append(deepcopy((header, children)))
        return result

    def resolve(self, name, chain=()):
        return self.resolve_object('material', name, chain)

    def resolve_object(self, kind, name, chain=()):
        if len(chain) >= 64:
            raise ValueError('Material inheritance exceeds 64 levels')
        label = kind + ':' + name
        if label in chain:
            raise ValueError('Cyclic %s inheritance: %s' % (kind, ' -> '.join((*chain,label))))
        if (kind,name) not in self.templates:
            raise ValueError('Missing parent %s: %s' % (kind,name))
        chain = (*chain,label)
        header, body = self.templates[kind,name]
        body = self.expand_objects(body, chain)
        if ':' in header:
            i = header.index(':')
            if i+2 != len(header):
                raise ValueError('Only single material inheritance is supported: ' + name)
            base = self.resolve_object(kind, self.unquote(header[i+1]), chain)
            body = self.merge(base, body)
        return deepcopy(body)

    def expand_objects(self, nodes, chain):
        result = []
        for header, children in nodes:
            if children is None:
                result.append((header, None))
                continue
            children = self.expand_objects(children, chain)
            if ':' in header:
                index = header.index(':')
                if index+2 != len(header):
                    raise ValueError('Only single object inheritance is supported')
                base = self.resolve_object(header[0], self.unquote(header[index+1]), chain)
                children = self.merge(base, children)
                header = header[:index]
            result.append((header, children))
        return result

    def discover(self, names):
        def ready():
            try:
                for name in names:
                    self.resolve(name)
                return True
            except ValueError:
                return False
        for path in self.resources.material_files():
            if ready():
                break
            if path not in self.loaded:
                try:
                    self.load(path)
                except (OSError, ValueError) as error:
                    self.warn('Could not read shared material script %s: %s' % (path,error))

    def substitute(self, nodes, variables):
        variables = dict(variables)
        for header, _ in nodes:
            if header[0] == 'set' and len(header) >= 3:
                variables[header[1]] = header[2:]

        def value(token, chain=()):
            if not token.startswith('$'):
                return [token]
            if token in chain or token not in variables:
                raise ValueError('Unresolved or cyclic material variable: ' + token)
            return [v for part in variables[token] for v in value(part, (*chain,token))]

        result = []
        for header, children in nodes:
            if header[0] == 'set':
                continue
            expanded = [v for part in header for v in value(part)]
            result.append((expanded, self.substitute(children,variables) if children is not None else None))
        return result

    def expand(self, path, names=None):
        self.load(path)
        lines = []
        def render(nodes):
            for header, children in nodes:
                lines.append(' '.join(header))
                if children is not None:
                    lines.append('{'); render(children); lines.append('}')
        for name in (list(self.definitions) if names is None else sorted(names)):
            if name in self.abstract:
                continue
            try:
                body = self.substitute(self.resolve(name), self.globals)
                render([(['material', '"'+name.replace('"','\\"')+'"'], body)])
            except ValueError as error:
                self.warn('Material "%s": %s. Its material name will be preserved with a basic placeholder.' % (name,error))
        return '\n'.join(lines)+'\n'
