#
# $Id: locdata.py 9954 2011-06-23 22:03:57Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import sys, os, re, optparse, codecs, zipfile, glob, xml.dom.minidom
import subprocess
import _locpaths
import pslocale, ioutil, metadata, codescan
import sandbox
import vcs
from strdef import *
from textui.colors import *
from textui.ansi import *

STRINGSFILE_PAT = re.compile(r'(?:(.+)-?)?strings-((?:[a-z][a-z])(?:[-_](?:[a-z][a-z]))?)\.(.+)', re.IGNORECASE)
GETTEXT_PAT = re.compile(r'(?<![a-zA-Z0-9_])(_|gettext)\s*\(\s*(["\'])(.*?)(?<!\\)\2\s*[\),]')
FIND_SINGLE_PAT = re.compile(r'([\'])(?!Ps|http|www\.)([\%\=\t \w\.@{}\(\)\<\>#/"\[\]\-:;&+]*?)([\'])', re.IGNORECASE)
FIND_DOUBLE_PAT = re.compile(r'(["])(?!Ps|http|www\.)([\%\=\t \w\.@{}\(\)\<\>#/\'\[\]\-:;&+]*?)(["])', re.IGNORECASE)
ALT_PAT = re.compile(r'alt\=')
FORMAT_SPECIFIERS_PAT = re.compile(r'(["\'])([\s\w][=\s\w\.@{}\(\)<>#/\'";:-]*)(["\'])((\s\+)([\s\w][\s\w\.@{}\(\)\<\>#/]*)(\s\+)([\s\.\w]*)(["\'])([\s\w][\s\w\.@{}\(\)\<\>#/\'"]*)(["\']))+')
COMMENT_PAT = re.compile(r'[ \t]*//[= \w\.@{}\(\)<>#/\'";:-]*')
ESCAPED_QUOTE_PAT = re.compile(r'(?<!\\)\\([\'"])')
CANONICAL_STRINGSFILE_PAT = re.compile(r'(?:(.+)-)?strings-((?:[a-z][a-z])(?:_(?:[A-Z][A-Z]))?)\.(.+)')
TRANS_PAT = re.compile(r'^\s*(["\'])(.*?)(?<!\\)\1[\r\n\t ]*:[\r\n\t ]*(["\'])(.*?)(?<!\\)\3', re.MULTILINE)
JS_HEADER = u'''/*
* $Id: locdata.py 9954 2011-06-23 22:03:57Z ahartvigsen $
*
* Proprietary and confidential.
* Copyright $Date:: 2011#$ Perfect Search Corporation.
* All rights reserved.
*
*/
'''

TRANSFILE_HEADER = u'''<strings>
<!-- ____________________ INSTRUCTIONS FOR TRANSLATOR ________________________

A series of string pairs follow. Each pair contains an english value and an equivalent
in your language. If the equivalent is present, please review it for accuracy and correct
if necessary. If the equivalent has no useful value, please supply one.

In some cases, we have supplied a note providing additional context or explanation to
clarify how the string will be used. You can create your own notes as well, to ask us
questions; just add a <note lang="%s">...</note> to the appropriate string.

Strings may contain format specifiers (placeholders like "{0}") that will be replaced
with filenames, dates, and similar values at runtime. These placeholders are numbered
beginning with 0 (NOT 1). Please reorder them as needed to match the natural ordering
of your language. It is not necessarily an error to repeat a format specifier, so if
you see a string that uses {0} more than once, for example, preserve the duplication in
your translation.

You may also see an occasional <warning> tag. These are used to flag problems with our
English strings that we need to correct. We've included them so you can anticipate
tweaks we might make in the future.
-->

'''

def _stripJs(txt):
    txt = txt.replace(u'\ufeff', u'')
    txt = txt.strip()
    if txt.startswith(u'/*'):
        i = txt.find(u'*/')
        assert(i > -1)
        txt = txt[i + 2:]
    lines = [x.strip() for x in txt.split(u'\n') if x.strip()]
    txt = u'\n'.join(lines)
    return txt

def jsIsDifferent(old, new):
    old = _stripJs(old)
    new = _stripJs(new)
    return old != new

def undoEscapes(txt):
    return ESCAPED_QUOTE_PAT.sub(r'\1', txt)

def prepForJson(txt):
    return txt.replace('"', '\\"')

def prepForXml(txt):
    prepChars = [u'&',u'<',u'>',u'"',u"'"]
    reChars = [u'&amp;',u'&lt;',u'&gt;',u'&quot;',u'&apos;']
    for i in range(len(prepChars)):
        txt = txt.replace(prepChars[i], reChars[i])
    return txt

def undoPrepForXml(txt):
    prepChars = [u'<',u'>',u'"',u"'",u'&']
    reChars = [u'&lt;',u'&gt;',u'&quot;',u'&apos;',u'&amp;']
    for i in range(len(prepChars)):
        txt = txt.replace(reChars[i], prepChars[i])
    return txt

_ACCENTS = {
    u'&aacute;':unichr(225),
    u'&Aacute;':unichr(193),
    u'&agrave;':unichr(224),
    u'&Agrave;':unichr(192),
    u'&acirc;':unichr(226),
    u'&Acirc;':unichr(194),
    u'&aring;':unichr(229),
    u'&Aring;':unichr(197),
    u'&atilde;':unichr(227),
    u'&Atilde;':unichr(195),
    u'&auml;':unichr(228),
    u'&Auml;':unichr(196),
    u'&aelig;':unichr(230),
    u'&AElig;':unichr(198),
    u'&ccedil;':unichr(231),
    u'&Ccedil;':unichr(199),
    u'&eacute;':unichr(233),
    u'&Eacute;':unichr(201),
    u'&egrave;':unichr(232),
    u'&Egrave;':unichr(200),
    u'&ecirc;':unichr(234),
    u'&Ecirc;':unichr(202),
    u'&euml;':unichr(235),
    u'&Euml;':unichr(203),
    u'&iacute;':unichr(237),
    u'&Iacute;':unichr(205),
    u'&igrave;':unichr(236),
    u'&Igrave;':unichr(204),
    u'&icirc;':unichr(238),
    u'&Icirc;':unichr(206),
    u'&iuml;':unichr(239),
    u'&Iuml;':unichr(207),
    u'&ntilde;':unichr(241),
    u'&Ntilde;':unichr(209),
    u'&oacute;':unichr(243),
    u'&Oacute;':unichr(211),
    u'&ograve;':unichr(242),
    u'&Ograve;':unichr(210),
    u'&ocirc;':unichr(244),
    u'&Ocirc;':unichr(212),
    u'&oslash;':unichr(248),
    u'&Oslash;':unichr(216),
    u'&otilde;':unichr(245),
    u'&Otilde;':unichr(213),
    u'&ouml;':unichr(246),
    u'&Ouml;':unichr(214),
    u'&szlig;':unichr(223),
    u'&uacute;':unichr(250),
    u'&Uacute;':unichr(218),
    u'&ugrave;':unichr(249),
    u'&Ugrave;':unichr(217),
    u'&ucirc;':unichr(251),
    u'&Ucirc;':unichr(219),
    u'&uuml;':unichr(252),
    u'&Uuml;':unichr(220),
    u'&yuml;':unichr(255)
}
def accentChars(txt):
    for escape, char in _ACCENTS.items():
        txt = txt.replace(escape, char)
    return txt

def _get_xml_text(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)

_STR_TYPE = type('')
_USTR_TYPE = type(u'')
_REGEX_TYPE = type(NOTE_PAT)

def _read(path):
    f = codecs.open(path, 'r', 'utf-8')
    txt = f.read()
    f.close()
    return txt

def cvtMatches(matches, txt, path, idGrp, valGrp, locale):
    m2 = []
    for m in matches:
        offset = m.start()
        linenum = codescan.getLineNumForOffset(txt, offset)
        strdef = StrDef(undoEscapes(m.group(idGrp)), undoEscapes(m.group(valGrp)), locale)
        strdef.addLoc(FileLocation(path, linenum))
        m2.append(strdef)
    return m2

def findMisses(txt):
    excludeIfBefore = [
'(tag|style|path|field|action|displayField|load|root|property|id|mode|action|size|dataIndex|itemSelector|uiprovider|Template|class|scale|align|ddGroup|record|theme|layout|margins|methond|name|region|mapping|type|pack|cls|event)\s*:\s?',
'(Events|attribute|class|\.get|Ext\.getCmp|fireEvent|\.on|Ext\.get|Ext\.reg|\.set|child|\.selectValue|class)\(\s*',
'throw ', 'var [\w]+ \=\s?', '\w=', 'attr\s?=\s?', 'return ', 'record\.data\[']
    excludeIfAfter = [':']
    found = [f for f in FIND_SINGLE_PAT.finditer(txt)] + [f for f in FIND_DOUBLE_PAT.finditer(txt)]
    i = 0
    while i < len(found):
        deleted = False
        for f in found:
            if found[i].start() > f.start() and found[i].end() < f.end():
                del found[i]
                deleted = True
                break
        if deleted:
            continue
        for a in excludeIfAfter:
            after = re.compile(r'%s' % a, re.IGNORECASE)
            if after.findall(txt[found[i].end():found[i].end()+2]):
                #print txt[found[i].start():found[i].end()+2]
                del found[i]
                deleted = True
                break
        if deleted:
            continue
        for b in excludeIfBefore:
            before = re.compile(r'%s' % b, re.IGNORECASE)
            if found[i].start() < 30:
                start = 0
            else:
                start = found[i].start()-30
            if before.findall(txt[start:found[i].start()]):
                #print txt[start:found[i].end()]
                del found[i]
                deleted = True
                break
        if deleted:
            continue
        check = found[i].group(2)
        if check == '':
            del found[i]
            continue
        if check[0] == '{' and check[len(check)-1] == '}':
            del found[i]
            continue
        if check[0] == '.' or check[0] == '/':
            del found[i]
            continue
        vowels = ['a', 'e', 'i', 'o', 'u']
        vowel = False
        alpha = False
        for c in check:
            if c in vowels:
                vowel = True
            if c.isalpha():
                alpha = True
            if alpha and vowel:
                break
        if (not vowel) or (not alpha):
            del found[i]
            continue
        if pureHTML(check):
            del found[i]
            continue
        i += 1
    return found

def pureHTML(txt):
    if txt[0] == '<' and txt[len(txt)-1] == '>':
        find = ALT_PAT.findall(txt)
        if find:
            return False
        prev = False
        for c in txt:
            if prev:
                if c != '<' and c != '{':
                    return False
                prev = False
            if c == '>':
                prev = True
        lastFound = txt.find('>')
        while lastFound > -1 and lastFound < len(txt)-1:
            if txt[lastFound+1] != '<':
                if txt[lastFound+1] != '{':
                    return False
                close = txt.find('}',lastFound)
                if txt[close+1] != '<':
                    return False
            lastFound = txt.find('>', lastFound+1)
        return True
    return False

def parseSrc(path, relpath, component):
    txt = _read(path)
    nextInactiveBlock = codescan.pickInactiveBlockFinder(path)
    # Remove all the inactive blocks from our analysis.
    txt = codescan.getActiveBlocksOnly(txt, nextInactiveBlock)
    matches = cvtMatches([m for m in GETTEXT_PAT.finditer(txt)], txt, relpath, 3, 3, 'en')
    found = cvtMatches(findMisses(txt), txt, relpath, 2, 2, 'en')
    formatSpecErr = cvtMatches([m for m in FORMAT_SPECIFIERS_PAT.finditer(txt)], txt, relpath, 0, 0, 'en')
    comments = cvtMatches([m for m in COMMENT_PAT.finditer(txt)], txt, relpath, 0, 0, 'en')
    if found:
        cr = path[0:path.find(relpath)]
        doNotExtract = file(os.path.join(cr, 'buildscripts/.do-not-extract.txt').replace('\\', '/')).read().split('\n')
        doNotExtract += file(os.path.join(cr, component, '.do-not-extract.txt').replace('\\', '/')).read().split('\n')
        i = 0
        while i < len(found):
            deleted = False
            if found[i].id in doNotExtract:
                del found[i]
                continue
            for m in matches:
                if deleted:
                    break
                if m.id == found[i].id:
                    if m.fileLocs[0].line == found[i].fileLocs[0].line:
                        del found[i]
                        deleted = True
            for err in formatSpecErr:
                if deleted:
                    break
                if err.fileLocs[0].line == found[i].fileLocs[0].line:
                    del found[i]
                    deleted = True
            for c in comments:
                if deleted:
                    break
                if c.fileLocs[0].line == found[i].fileLocs[0].line:
                    del found[i]
                    deleted = True
            if deleted:
                continue
            i += 1
    if matches:
        pass  #print(relpath)
    return matches, found, formatSpecErr

def parseTrans(path, relpath, locale):
    txt = _read(path)
    nextInactiveBlock = codescan.pickInactiveBlockFinder(path)
    # Remove all the inactive blocks from our analysis.
    txt = codescan.getActiveBlocksOnly(txt, nextInactiveBlock)
    matches = cvtMatches([m for m in TRANS_PAT.finditer(txt)], txt, relpath, 2, 4, locale)
    if matches:
        pass  #print(relpath)
    return matches

class FakeFile:
    def __init__(self):
        self.txt = ''
    def write(self, txt):
        self.txt += txt
    def printf(self, txt):
        print (txt)
        self.write('%s\n' % txt)

class LocData:
    def __init__(self, root, testing=False):
        self._svnInfo = None
        self.trans = {}
        self.src = {}
        self.byLocale = {}
        self.pathsByComponent = {}
        self.possibleMisses = {}
        self.formatErrors = {}
        root = ioutil.norm_folder(root)
        self.conf = metadata.Conf(root, report=False)
        if type(root) == _STR_TYPE:
            root = unicode(root, 'utf-8')
        self.root = root
        if not testing:
            fileCount, folderCount = metadata.visit(self.root, visitor=self, recurser=self, report=False)
            self._connect()
    def getComponent(self, relpath):
        if os.name == 'nt':
            relpath = relpath.replace('\\', '/')
        i = relpath.find('/')
        if i > -1:
            return relpath[0:i]
        return relpath
    def getNamingPat(self, relpath):
        if os.name == 'nt':
            relpath = relpath.replace('\\', '/')
        m = STRINGSFILE_PAT.match(relpath)
        assert(m)
        pat = 'strings-%s'
        if m.group(1):
            pat = m.group(1) + pat
        if m.group(3):
            pat = pat + '.' + m.group(3)
        return pat
    def select(self, folder, dirs):
        if folder == self.root:
            for d in dirs[:]:
                conf = metadata.Conf(os.path.join(folder, d), report=False)
                tl = conf.getTargetedLocales()
                if tl:
                    if len(tl) == 1 and 'en' in tl:
                        if conf.report:
                            print("Ignoring %s, since it doesn't support localization." % d)
                        dirs.remove(d)
        for d in dirs[:]:
            if d.lower().startswith('test'):
                dirs.remove(d)
        return dirs
    def visit(self, folder, item, relativePath):
        baseFolder = folder.replace(relativePath, '')
        truncated = folder
        if baseFolder[-1] == '/':
            startFolder = baseFolder[0:baseFolder.rfind('/')]
        else:
            startFolder = baseFolder
        while truncated != startFolder:
            truncated = truncated[0:truncated.rfind('/')]
            if metadata.METADATA_FILE in os.listdir(truncated):
                conf = metadata.Conf(truncated, report=False)
                break
        else:
            conf = None
        uiPaths = conf.getUiPaths()
        for ui in uiPaths:
            if relativePath.find(uiPaths[ui]) > -1:
                files = os.listdir(folder)
                fullpath = os.path.join(folder, item)
                relpath = relativePath + item
                if type(relpath) == _STR_TYPE:
                    relpath = unicode(relativePath + item, 'utf-8')
                m = STRINGSFILE_PAT.match(item)
                if m:
                    component = self.getComponent(relpath)
                    namingPat = self.getNamingPat(relpath)
                    old = self.pathsByComponent.get(component, None)
                    if old:
                        for o in old:
                            oldUI, oldPat = o
                            if oldUI == conf.getUi(relativePath):
                                if namingPat != oldPat:
                                    print('Warning: %s does not match naming pattern %s. Components have some flexibility in how strings files are named and located, but must be internally consistent.' % (relpath, namingPat))
                            else:
                                if self.pathsByComponent[component].count((conf.getUi(relativePath), namingPat)) == 0:
                                    self.pathsByComponent[component].append((conf.getUi(relativePath), namingPat))
                    else:
                        self.pathsByComponent[component] = [(conf.getUi(relpath), namingPat)]
                    if not CANONICAL_STRINGSFILE_PAT.match(item):
                        print('Warning: %s does not match the canonical naming pattern for strings files ([prefix-]strings-xx[_YY]*.*).' % item)
                    self.trans[relpath] = parseTrans(fullpath, relpath, m.group(2))
                else:
                    data, misses, formatErr = parseSrc(fullpath, relpath, self.getComponent(relpath))
                    if data:
                        self.src[relpath] = data
                    if misses:
                        self.possibleMisses[relpath] = misses
                    if formatErr:
                        self.formatErrors[relpath] = formatErr
    def getTargetedLocales(self, component):
        x = self.conf.getTargetedLocales(component)
        if not x:
            x = pslocale.getStandardLocales()
        return x
    def update(self, relpath):
        txt = self.getTransText(relpath)
        if txt:
            fullpath = self.root + relpath
            add = not os.path.isfile(fullpath)
            if ioutil.write_if_different(fullpath, txt, compare_func=jsIsDifferent):
                if add:
                    os.system('bzr add %s' % fullpath)
                else:
                    print('%s has been modified and needs to be checked in.' % relpath)
                return True
        return False
    def getTransText(self, relpath):
        txt = u''
        m = STRINGSFILE_PAT.match(relpath)
        locale = m.group(2)
        trans = self.byLocale.get(locale, None)
        if trans:
            en = self.byLocale['en']
            ids = trans.keys()[:]
            ids.sort()
            for id in ids:
                if id in en:
                    t = trans[id]
                    txt += u'    "%s": "%s",\n' % (prepForJson(t.id), prepForJson(t.txt))
            if txt:
                txt = u'{\n  vocabulary: {\n' + txt[0:-2] + u'\n  }\n}\n'
            else:
                txt += u'{\n}\n'
            txt = JS_HEADER + txt
        return txt
    def fileNeedsSync(self, relpath):
        txt = self.getTransText(relpath)
        if txt:
            return ioutil.file_differs_from_text(self.root + relpath, txt, compare_func=jsIsDifferent)
        return False
    def exportFile(self, fullpath, relpath):
        m = STRINGSFILE_PAT.match(fullpath)
        locale = m.group(2)
        fullpath += '.xml'
        txt = TRANSFILE_HEADER % locale
        trans = self.byLocale.get(locale, None)
        if not trans:
            trans = {}
        en = self.byLocale['en']
        ids = en.keys()[:]
        ids.sort()
        newCount = 0
        reviewCount = 0
        wordCountEng = 0
        wordCountTrans = 0
        chunk = u''
        for id in ids:
            enstr = en[id]
            add = False
            for loc in enstr.fileLocs:
                if relpath[0:relpath.rfind('/')] in loc.path:
                    add = True
            if add:
                if not id in trans or trans[id].getValue() == u'?':
                    newCount += 1
                else:
                    reviewCount += 1
                    if id in trans:
                        wordCountTrans += trans[id].getWordCount()
                wordCountEng += en[id].getWordCount()
                if id in trans:
                    strdef = trans[id]
                else:
                    strdef = StrDef(id, '?', locale)
                chunk += u'  <string>\n'
                chunk +=  u'    <val lang="en">%s</val>\n' % prepForXml(enstr.getValue())
                note = enstr.getNote()
                if note:
                    chunk += u'    <note lang="en">%s</note>\n' % note
                warnings = enstr.getWarnings()
                if warnings:
                    enstr.warn()
                    chunk += u'    <warnings>' + ' '.join(warnings) + u'</warnings>\n'
                chunk += u'    <val lang="%s">%s</val>\n' % (locale, prepForXml(strdef.getValue()))
                chunk += u'  </string>\n\n'
        txt += u'  <info>\n'
        txt += u'    <newStrings>%d</newStrings>\n' % newCount
        txt += u'    <reviewStrings>%d</reviewStrings>\n' % reviewCount
        txt += u'    <numStrings>%d</numStrings>\n' % (newCount + reviewCount)
        txt += u'    <wordCountEnglish>%d</wordCountEnglish>\n' % wordCountEng
        txt += u'    <wordCount%s>%d</wordCount%s>\n' % (locale, wordCountTrans, locale)
        txt += u'    <relativePath>%s</relativePath>\n' % relpath
        txt += u'  </info>\n\n'
        txt += chunk
        txt += u'</strings>\n'
        ioutil.write_if_different(fullpath, txt)
        print(fullpath)
    def generateMartian(self):
        en = self.byLocale['en']
        ma = {}
        for id in en.keys():
            strdef = en[id]
            ma[id] = StrDef(strdef.id, martian.convert(strdef.txt), 'ma')
        return ma
    def getProject(self):
        return sandbox.create_from_within(self.conf.path).get_top_component()
    def get_branch(self):
        return sandbox.create_from_within(self.conf.path).get_branch()
    def getRevision(self):
        sb = sandbox.create_from_within(self.conf.path)
        branchLocation = os.path.join(sb.get_code_root(), sb.get_top_component())
        return vcs.revno(branchLocation, True)
        cwd = os.getcwd()
        os.chdir(branchLocation)
        p = subprocess.Popen(['bzr', 'revno', '--tree'], stdout=subprocess.PIPE)
        revno = p.stdout.read().strip()
        os.chdir(cwd)
        return revno
    def getBatchName(self):
        bn = self.getProject() + '-'
        br = self.get_branch()
        if br != 'trunk':
            bn += br + '-'
        return bn + str(self.getRevision())
    def export(self, folder):
        if os.path.exists(folder):
            assert(os.path.isdir(folder))
        path = ioutil.norm_folder(folder) + self.getBatchName() + '/'
        print('exporting to %s' % path)
        if os.path.exists(path):
            ioutil.nuke(path)
        os.makedirs(path)
        for component in self.pathsByComponent:
            locales = self.getTargetedLocales(component)
            pathPats = self.pathsByComponent[component]
            for paths in pathPats:
                pathPat = paths[1]
                for loc in locales:
                    if loc != 'en':
                        relpath = pathPat % loc
                        fullpath = path + relpath
                        fldr = os.path.dirname(fullpath)
                        if not os.path.exists(fldr):
                            os.makedirs(fldr)
                        self.exportFile(fullpath, relpath)
        self.zip(folder)
    def sync(self):
        updateCount = 0
        for component in self.pathsByComponent:
            locales = self.getTargetedLocales(component)
            if not ('ma' in locales):
                locales.append('ma')
            self.byLocale['ma'] = self.generateMartian()
            for component in self.pathsByComponent.keys():
                pathPats = self.pathsByComponent[component]
                for paths in pathPats:
                    pathPat = paths[1]
                    for loc in locales:
                        if loc != 'en':
                            relpath = pathPat % loc
                            if self.update(relpath):
                                updateCount += 1
        print('Updated %d files.' % updateCount)
    def check(self, component=''):
        strsWithWarnings = [self.byLocale['en'][id] for id in self.byLocale['en'].keys()]
        strsWithWarnings = [x for x in strsWithWarnings if x.getWarnings()]
        needsSync = []
        locales = self.getTargetedLocales(component)
        if not ('ma' in locales):
            locales.append('ma')
        self.byLocale['ma'] = self.generateMartian()
        for component in self.pathsByComponent.keys():
            pathPats = self.pathsByComponent[component]
            for paths in pathPats:
                pathPat = paths[1]
                for loc in locales:
                    if loc != 'en':
                        relpath = pathPat % loc
                        if self.fileNeedsSync(relpath):
                            needsSync.append(relpath)
        return strsWithWarnings, needsSync
    def checkComplete(self, component=''):
        supportedLocales = []
        exitCode = 0
        locales = pslocale.getStandardLocales()
        for loc in self.getTargetedLocales(component):
            if not (loc in locales):
                locales.append(loc)
        for loc in self.byLocale.keys():
            if not (loc in locales):
                locales.append(loc)
        if not ('ma' in locales):
            locales.append('ma')
        self.byLocale['ma'] = self.generateMartian()
        missing = {}
        for loc in locales:
            if loc != 'en':
                if (not loc in self.byLocale.keys()):
                    if loc in self.getTargetedLocales(component):
                        missing[loc] = self.byLocale['en'].keys()
                    continue
                for id in self.byLocale['en'].keys():
                    if not id in self.byLocale[loc].keys():
                        if missing.get(loc, 0) == 0:
                            missing[loc] = [id]
                        else:
                            missing[loc].append(id)
                if missing.get(loc, 0) == 0:
                    supportedLocales.append(loc)
        print('Supported locales: %s' % supportedLocales)
        #print('Targeted locales: %s' % self.conf.targetedLocales)
        complete = True
        for x in self.getTargetedLocales(component):
            if x != 'en':
                if not (x in supportedLocales):
                    complete = False
        if not complete:
            exitCode = 1
            '''print ('Missing Translations')
            for key in self.conf.targetedLocales:
                print ('%s is missing: %s' % (key, missing[key]))'''
            print ('Missing translations for '),
            miss = []
            for key in missing.keys():
                if key in self.getTargetedLocales(component):
                    miss.append(key)
            print (miss)
        strWithWarnings, needsSync = self.check(component)
        return exitCode, strWithWarnings, needsSync
    def _connect(self):
        self.byLocale = {}
        en = {}
        for file in self.src.keys():
            for strdef in self.src[file]:
                if strdef.id in en:
                    # Merge the two identical strings
                    en[strdef.id].addLoc(strdef.fileLocs[0])
                else:
                    en[strdef.id] = strdef
        #print('english has %d strings' % len(en.keys()))
        self.byLocale['en'] = en
        for file in self.trans.keys():
            i = 1
            for strdef in self.trans[file]:
                if i == 1:
                    locale = strdef.locale
                    if locale in self.byLocale:
                        thisLoc = self.byLocale[locale]
                    else:
                        thisLoc = {}
                        self.byLocale[locale] = thisLoc
                i += 1
                thisLoc[strdef.id] = strdef
                # See if this string exists in English.
                if strdef.id in en:
                    src = en[strdef.id]
                    src.trans.append(strdef)
                    strdef.src = src
    def gatherLocales(self, baseFolder, folder, loc):
        files = os.listdir(baseFolder+folder)
        locFiles = []
        find = '-strings-%s.js.xml' % loc
        for f in files:
            if os.path.isdir(baseFolder+os.path.join(folder, f)):
                locFiles.extend(self.gatherLocales(baseFolder, os.path.join(folder,f), loc))
            elif os.path.isfile(baseFolder+folder+'/'+f):
                if f.find(find) != -1:
                    locFiles.append(folder+'/'+f)
        return locFiles
    def zip(self, folder):
        '''Zip translations by locale'''
        if os.path.exists(folder):
            assert(os.path.isdir(folder))
        files = os.listdir(folder)
        for component in self.pathsByComponent:
            locales = self.getTargetedLocales(component)
            for f in files:
                if os.path.isdir(folder+'/'+f) and f.find('.zip') == -1:
                    for loc in locales:
                        zipFiles = self.gatherLocales(folder, f, loc)
                        if zipFiles != []:
                            zipName = f+'-'+loc+'.zip'
                            print 'Creating zip folder %s' % os.path.join(folder, zipName)
                            if os.path.exists(zipName):
                                ioutil.nuke(zipName)
                            z = zipfile.ZipFile(folder+zipName, "w", zipfile.ZIP_DEFLATED)
                            for zf in zipFiles:
                                z.write(folder+zf,zf)
    def importZip(self, folder, fileLoc):
        if os.path.exists(folder):
            assert(os.path.isdir(folder))
        else:
            os.mkdir(folder)
        fileFolder = fileLoc[0:fileLoc.find('.zip')]
        fileFolder = fileFolder[0:fileFolder.rfind('/')]
        if os.path.exists(fileFolder):
            if fileLoc.find('.zip') > -1:
                files = [fileLoc.strip('/')]
            else:
                files = glob.glob(fileLoc+'*.zip')
            for f in files:
                z = zipfile.ZipFile(f, 'r')
                print ('Extracting folder %s' % f)
                z.extractall(folder)
                for x in z.namelist():
                    if x.find('.xml') > -1:
                        self.loadFile(folder, x)
    def loadFile(self, baseFolder, fileName):
        fileXML = codecs.open(baseFolder+fileName, 'r')
        fileXML = fileXML.read().decode('UTF-8')
        fileXML = accentChars(fileXML)
        dom = xml.dom.minidom.parseString(fileXML.encode('UTF-8', 'xmlcharrefreplace'))
        strings = dom.getElementsByTagName('string')
        info = dom.getElementsByTagName('relativePath')
        for i in info:
            locale = _get_xml_text(i.childNodes)
        loc = locale[locale.rfind('-')+1:locale.rfind('.js')]
        tran = []
        byLoc = {}
        for s in strings:
            vals = s.getElementsByTagName('val')
            for v in vals:
                if v.attributes['lang'].value == 'en':
                    id = _get_xml_text(v.childNodes)
                if v.attributes['lang'].value == loc:
                    txt = _get_xml_text(v.childNodes)
            if not txt or txt == u'?':
                continue
            notes = s.getElementsByTagName('note')
            for note in notes:
                id += '@@' + _get_xml_text(note.childNodes)
            strdef = StrDef(undoPrepForXml(id), undoPrepForXml(txt), loc)
            warnings = strdef.getWarnings()
            for w in warnings:
                print(w)
            tran.append(strdef)
            byLoc[id] = strdef
        if byLoc and tran:
            self.trans[locale] = tran
            self.byLocale[loc] = byLoc
            self.update(locale)
    def find(self, path):
        for key in self.formatErrors:
            print ('%s%s\n' % (path, key))
            for line in self.formatErrors[key]:
                printc(WARNING_COLOR + 'Please change to the correct format specifiers on line %d.' % line.fileLocs[0].line + ERROR_COLOR)
                printc("%s\n" % line.id + NORMTXT)
        printc(CMD_COLOR + ''.rjust(80, '*') + NORMTXT)
        doNotExtract = open(path+'.do-not-extract.txt', 'a')
        num = 0
        ff = FakeFile()
        for key in self.possibleMisses:
            num += len(self.possibleMisses[key])
        try:
            try:
                print ("%d possible missed strings." % num)
                fileNum = 1
                for key in self.possibleMisses:
                    printc(CMD_COLOR + '\nFile %d of %d Files' % (fileNum, len(self.possibleMisses)) + NORMTXT)
                    fileNum += 1
                    ff.printf('%s%s\n' % (path,key))
                    printc(CMD_COLOR + '%s possible misses in this file.\n' % len(self.possibleMisses[key]) + NORMTXT)
                    f = open(path+'/'+key, 'r+')
                    lines = f.readlines()
                    for miss in self.possibleMisses[key]:
                        start = lines[miss.fileLocs[0].line-1].find(miss.id)-1
                        end = start + len(miss.id)+2
                        autoCorrect = ['text:\s?', 'header:\s?', 'title:\s?', 'msg:\s?', 'label:\s?']
                        auto = False
                        for ac in autoCorrect:
                            correct = re.compile(r'%s' % ac, re.IGNORECASE)
                            if correct.search(lines[miss.fileLocs[0].line-1][start-len(ac):start]):
                                ff.printf('Auto change (from-to) line %s\n %s' % (miss.fileLocs[0].line, lines[miss.fileLocs[0].line-1].strip()))
                                line = lines[miss.fileLocs[0].line-1]
                                lines[miss.fileLocs[0].line-1] = line[0:start] + '_(' + line[start:end] + ')' + line[end:len(line)]
                                ff.printf('%s\n' % lines[miss.fileLocs[0].line-1].strip())
                                f.seek(0)
                                f.writelines(lines)
                                auto = True
                                break
                        if auto:
                            continue
                        answer = ''
                        while not answer:
                            printc(DELIM_COLOR + '%s %s' % (miss.fileLocs[0].line-1, lines[miss.fileLocs[0].line-2].strip()) + NORMTXT)
                            printc(DELIM_COLOR + str(miss.fileLocs[0].line) + ' ' + TITLE_COLOR + lines[miss.fileLocs[0].line-1][0:start].lstrip() + WARNING_COLOR + lines[miss.fileLocs[0].line-1][start:end] + TITLE_COLOR + lines[miss.fileLocs[0].line-1][end:len(lines[miss.fileLocs[0].line-1])] + NORMTXT)
                            if miss.fileLocs[0].line < len(lines):
                                printc(DELIM_COLOR +'%s %s' % (miss.fileLocs[0].line+1, lines[miss.fileLocs[0].line].strip()) + NORMTXT)
                            print ('')
                            answer = raw_input('Is this string suppose to be translated {(y)es/(n)o/(s)kip/(e)dit}?[s]\n%s\t: ' % miss.id)
                            print ('')
                            if answer == '':
                                answer = 's'
                            if 'ty1'.find(answer.lower()[0]) != -1:
                                ff.write('Auto change (from-to) line %s\n %s' % (miss.fileLocs[0].line, lines[miss.fileLocs[0].line-1].strip()))
                                line = lines[miss.fileLocs[0].line-1]
                                lines[miss.fileLocs[0].line-1] = line[0:start] + '_(' + line[start:end] + ')' + line[end:len(line)]
                                ff.write('%s\n' % lines[miss.fileLocs[0].line-1].strip())
                                f.seek(0)
                                f.writelines(lines)
                            elif 'fn0'.find(answer.lower()[0]) != -1:
                                doNotExtract.write(miss.id+'\n')
                            elif 's'.find(answer.lower()[0]) != -1:
                                pass
                            elif 'e'.find(answer.lower()[0]) != -1:
                                if os.name == 'nt':
                                    os.system('start notepad %s' % ('%s/%s' % (path,key)))
                                else:
                                    os.system('vi -R %s' % ('%s/%s' % (path,key)))
                            else:
                                print ('Not a vaild response')
                                answer = ''
                    f.close()
            except KeyboardInterrupt:
                f.close()
        finally:
            sb = sandbox.create_from_within(path)
            if not os.path.exists(os.path.join(sb.get_root(), 'translations')):
                os.mkdir(os.path.join(sb.get_root(), 'translations'))
            cl = open(os.path.join(sb.get_root(),'translations','LocChanges.log'), 'w')
            cl.write(ff.txt)
            doNotExtract.close()

