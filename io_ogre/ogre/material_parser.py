
import bpy
import os
import ast
import logging

logger = logging.getLogger('material_parser')

class ScriptToken:
    TID_LBRACKET = 0
    TID_RBRACKET = 1
    TID_COLON = 2
    TID_VARIABLE = 3
    TID_WORD = 4
    TID_QUOTE = 5
    TID_NEWLINE = 6
    TID_UNKNOWN = 7
    TID_END = 8

    types = ["TID_LBRACKET", "TID_RBRACKET", "TID_COLON", "TID_VARIABLE", "TID_WORD", "TID_QUOTE", "TID_NEWLINE", "TID_UNKNOWN", "TID_END"]

    def __init__(self, line):
        self.line = line
        self.type = -1
        self.lexeme = ""

    def __str__(self):
        return("line: %s, type: %s, lexeme: %s" % (self.line, self.types[self.type], self.lexeme))

class ScriptLexer:

    error = ""
    
    def tokenize(self, str, source):

        # States
        READY = 0
        COMMENT = 1
        MULTICOMMENT = 2
        WORD = 3
        QUOTE = 4
        VAR = 5
        POSSIBLECOMMENT = 6

        # Set up some constant characters of interest
        varopener = '$'
        quote = '"'
        slash = '/'
        backslash = '\\'
        openbrace = '{'
        closebrace = '}'
        colon = ':'
        star = '*'
        cr = '\r'
        lf = '\n'

        c = 0
        lastc = 0

        lexeme = ""
        line = 1
        state = READY
        lastQuote = 0
        firstOpenBrace = 0
        braceLayer = 0
        tokens = []

        # Iterate over the input
        for i in str:
        
            lastc = c;
            c = i;
            
            if c == quote:
                lastQuote = line;
            
            if state == READY or state == WORD or state == VAR:
                if c == openbrace:
                    if braceLayer == 0:
                        firstOpenBrace = line;
                    braceLayer += 1

                elif c == closebrace:
                    if braceLayer == 0:
                        self.error = "no matching open bracket '{' found for close bracket '}' at %s:%s" % (source, line)
                        return tokens;
                    braceLayer -= 1
            
            if state == READY:
                if c == slash and lastc == slash:
                    # Comment start, clear out the lexeme
                    lexeme = ""
                    state = COMMENT

                elif c == star and lastc == slash:
                    lexeme = ""
                    state = MULTICOMMENT

                elif c == quote:
                    # Clear out the lexeme ready to be filled with quotes!
                    lexeme = c
                    state = QUOTE

                elif c == varopener:
                    # Set up to read in a variable
                    lexeme = c
                    state = VAR

                elif self.isNewline(c):
                    lexeme = c
                    self.setToken(lexeme, line, tokens)

                elif not self.isWhitespace(c):
                    lexeme = c
                    if c == slash:
                        state = POSSIBLECOMMENT
                    else:
                        state = WORD

            elif state == COMMENT:
                if self.isNewline(c):
                    lexeme = c
                    self.setToken(lexeme, line, tokens)
                    state = READY

            elif state == MULTICOMMENT:
                if c == slash and lastc == star:
                    state = READY

            elif state == POSSIBLECOMMENT:
                if c == slash and lastc == slash:
                    lexeme = ""
                    state = COMMENT

                elif c == star and lastc == slash:
                    lexeme = ""
                    state = MULTICOMMENT

                else:
                    state = WORD
                    # OGRE_FALLTHROUGH;

            elif state == WORD:
                if self.isNewline(c):
                    self.setToken(lexeme, line, tokens)
                    lexeme = c
                    self.setToken(lexeme, line, tokens)
                    state = READY

                elif self.isWhitespace(c):
                    self.setToken(lexeme, line, tokens)
                    state = READY

                elif c == openbrace or c == closebrace or c == colon:
                    self.setToken(lexeme, line, tokens)
                    lexeme = c
                    self.setToken(lexeme, line, tokens)
                    state = READY

                else:
                    lexeme += c

            elif state == QUOTE:
                if c != backslash:
                    # Allow embedded quotes with escaping
                    if c == quote and lastc == backslash:
                        lexeme += c

                    elif c == quote:
                        lexeme += c
                        self.setToken(lexeme, line, tokens)
                        state = READY

                    else:
                        # Backtrack here and allow a backslash normally within the quote
                        if lastc == backslash:
                            lexeme = lexeme + "\\" + c
                        else:
                            lexeme += c

            elif state == VAR:
                if self.isNewline(c):
                    self.setToken(lexeme, line, tokens)
                    lexeme = c
                    self.setToken(lexeme, line, tokens)
                    state = READY

                elif self.isWhitespace(c):
                    self.setToken(lexeme, line, tokens)
                    state = READY

                elif c == openbrace or c == closebrace or c == colon:
                    self.setToken(lexeme, line, tokens)
                    lexeme = c
                    self.setToken(lexeme, line, tokens)
                    state = READY

                else:
                    lexeme += c

            # Separate check for newlines just to track line numbers
            if (c == cr or (c == lf and lastc != cr)):
                line += 1

        # Check for valid exit states
        if state == WORD or state == VAR:
            if lexeme != "":
                self.setToken(lexeme, line, tokens)

        else:
            if state == QUOTE:
                self.error = "no matching \" found for \" at %s:%s" % (source, lastQuote)
                return tokens;
        
        # Check that all opened brackets have been closed
        if braceLayer == 1:
            self.error = "no matching closing bracket '}' for open bracket '{' at %s:%s" % (source, firstOpenBrace)

        elif braceLayer > 1:
            self.error = "too many open brackets (%d) '{' without matching closing bracket '}' in %s" % (braceLayer, source)

        return tokens;

    def setToken(self, lexeme, line, tokens):
        openBracket = '{'
        closeBracket = '}'
        colon = ':'
        quote = '\"'
        var = '$'

        token = ScriptToken(line)
        token.line = line
        ignore = False

        # Check the user token map first
        if(len(lexeme) == 1 and self.isNewline(lexeme[0])):
            token.type = ScriptToken.TID_NEWLINE

            if(len(tokens) != 0 and tokens[-1].type == ScriptToken.TID_NEWLINE):
                ignore = True

        elif(len(lexeme) == 1 and lexeme[0] == openBracket):
            token.type = ScriptToken.TID_LBRACKET

        elif(len(lexeme) == 1 and lexeme[0] == closeBracket):
            token.type = ScriptToken.TID_RBRACKET

        elif(len(lexeme) == 1 and lexeme[0] == colon):
            token.type = ScriptToken.TID_COLON

        else:
            token.lexeme = lexeme

            # This is either a non-zero length phrase or quoted phrase
            if(len(lexeme) >= 2 and lexeme[0] == quote and lexeme[-1] == quote):
                token.type =ScriptToken.TID_QUOTE

            elif(len(lexeme) > 1 and lexeme[0] == var):
                token.type = ScriptToken.TID_VARIABLE

            else:
                token.type = ScriptToken.TID_WORD

        if(not ignore):
            tokens.append(token)

    def isWhitespace(self, c):
        return (c == ' ' or c == '\r' or c == '\t')

    def isNewline(self, c):
        return (c == '\n' or c == '\r')


class MaterialParser:

    def unquote(string):
        return (string[1:-1])
    

    def parameters(i, tokens):
        parameters = []
        j = 1
        while tokens[i + j].type == ScriptToken.TID_WORD:

            try:
                lexeme = ast.literal_eval(tokens[i + j].lexeme)

            except ValueError:
                lexeme = tokens[i + j].lexeme

            except SyntaxError:
                lexeme = tokens[i + j].lexeme
            
            parameters.append(lexeme)

            j += 1
        
        return parameters


    def xParseMaterial(meshMaterials, materialFile, folder):
        from .material_resolver import MaterialResolver
        from .material_reader import read_materials
        from .. import config
        resolver = MaterialResolver(folder, bpy.path.abspath(config.get('IMPORT_RESOURCE_PATH')) if config.get('IMPORT_RESOURCE_PATH') else '')
        try:
            resolver.load(materialFile)
            meshMaterials.update(read_materials(resolver))
        except (OSError, ValueError) as error:
            resolver.warn('Could not parse material file %s: %s' % (materialFile,error))

    def xCollectMaterialData(meshData, onlyName, folder):
        from pathlib import Path
        from .material_resolver import MaterialResolver
        from .material_reader import read_materials
        from .. import config
        resolver = MaterialResolver(folder, bpy.path.abspath(config.get('IMPORT_RESOURCE_PATH')) if config.get('IMPORT_RESOURCE_PATH') else '')
        specific = Path(folder)/(onlyName+'.material')
        local = [specific] if specific.is_file() else sorted(Path(folder).glob('*.material'))
        for path in local:
            try:
                resolver.load(path)
            except (OSError, ValueError) as error:
                resolver.warn('Could not parse material file %s: %s' % (path,error))
        names = {sub.get('materialOrig',sub['material']) for sub in meshData.get('submeshes',())}
        resolver.discover(names)
        meshData['materials'] = read_materials(resolver,names)
