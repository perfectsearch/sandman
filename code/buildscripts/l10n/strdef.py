#
# $Id: strDef.py 9934 2011-06-23 18:51:56Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import re
import _locpaths
import martian
from codescan import codescan

NOTE_PAT = re.compile(r'^(.*?)@@(.*)')
FORMAT_SPEC_PAT = re.compile(r'(?<!\\)({([0-9]+).*?(?<!\\)})')
WORDSPLIT_PAT = re.compile(r'[-\r\n\t ;,.?!=@&#\$"\*\(\)]+')

_STR_TYPE = type('')
_USTR_TYPE = type(u'')
_REGEX_TYPE = type(NOTE_PAT)
class TextCheck:
    def __init__(self, num, regexOrFunc, msg=None):
        rtype = type(regexOrFunc)
        if type(regexOrFunc) == _STR_TYPE or type(regexOrFunc) == _USTR_TYPE:
            regexOrFunc = re.compile(regexOrFunc)
        if type(regexOrFunc) == _REGEX_TYPE:
            self.regex = regexOrFunc
            assert(msg)
        else:
            self.func = regexOrFunc
        self.num = num
        self.msg = msg
    def check(self, txt, notes):
        if notes:
            suppressPat = re.compile(r'-w%d(?![0-9])' % self.num)
            if suppressPat.search(notes):
                return []
        probs = []
        if hasattr(self, 'func'):
            func = getattr(self, 'func')
            probs = func(txt)
        else:
            m = self.regex.search(txt)
            if m:
                probs = [self.msg]
        if probs:
            return 'Warning %d: %s' % (self.num, ' '.join(probs))
        return probs

def _checkFormatSpecs(txt):
    probs = []
    specs = FORMAT_SPEC_PAT.finditer(txt)
    if not specs:
        return
    nums = {}
    minSpec = 999
    maxSpec = -1
    for s in specs:
        num = int(s.group(2))
        if num < minSpec:
            minSpec = num
        if num > maxSpec:
            maxSpec = num
        nums[num] = 1
    if maxSpec > 10:
        probs.append('Passing %d args to String.format() is not supported.' % (maxSpec + 1))
        maxSpec = 10
    for i in range(maxSpec):
        if not i in nums:
            probs.append('Format specifier {%d} not found.' % i)
            if len(probs) > 3:
                break
    return probs

class TransCorrCheck:
    def __init__(self, num, regexOrFunc, msg=None):
        rtype = type(regexOrFunc)
        if type(regexOrFunc) == _STR_TYPE or type(regexOrFunc) == _USTR_TYPE:
            regexOrFunc = re.compile(regexOrFunc, re.IGNORECASE)
        if type(regexOrFunc) == _REGEX_TYPE:
            self.regex = regexOrFunc
            assert(msg)
        else:
            self.func = regexOrFunc
        self.num = num
        self.msg = msg
    def check(self, txt, notes, eng):
        if notes:
            suppressPat = re.compile(r'-w%d(?![0-9])' % self.num)
            if suppressPat.search(notes):
                return []
        probs = []
        if hasattr(self, 'func'):
            func = getattr(self, 'func')
            probs = func(txt, eng)
        else:
            m = self.regex.search(txt)
            if m:
                probs = [self.msg]
            if probs:
                return 'Warning %d: %s' % (self.num, ' '.join(probs))
        return probs

def _checkShout(txt):
    if txt.find('!') > -1:
        return ["Don't shout at the user (avoid exclamation points)."]
    return []

def _checkSizeCorrel(txt, eng):
    if eng.find(' ') > -1:
        size = 3
    else:
        size = 6
    if len(txt)/len(eng) > size or len(eng)/len(txt) > size:
        return ["Size of translation doesn't seem to correlate with English string."]
    return []

def _checkBandwidthAbbreviation(txt):
    bw = re.compile(r"\b[mgkt]bps", re.IGNORECASE)
    if bw.match(txt):
        for i in range(1,len(txt)):
            if txt[i] in txt.upper():
                return ['Use all lower case for "bps" in bandwidth abbreviations.']
    return []

def _checkKeyOrder(txt):
    keys = ['CTRL', 'SHIFT', 'COMMAND', 'ALT', 'FN']
    txtSplit = txt.split('+')
    if len(txtSplit) > 1:
        for i in range(len(txtSplit)-1):
            if txtSplit[i] in keys:
                for j in range(i+1,len(txtSplit)):
                    if txtSplit[j] in keys:
                        if keys.index(txtSplit[i]) > keys.index(txtSplit[j]):
                            return ["Use correct order for keys. ['CTRL', 'SHIFT', 'COMMAND', 'ALT', 'FN']"]
            elif txtSplit[i].strip() in keys:
                return["Don't use spaces between '+' int 'CTRL+ALT+DEL'"]
    return []

def _checkTransFormatSpecs(txt, eng):
    probs = []
    specsTrans = FORMAT_SPEC_PAT.finditer(txt)
    specsEng = FORMAT_SPEC_PAT.finditer(eng)
    if not specsTrans:
        return
    numsTrans = {}
    numsEng = {}
    minSpecTrans = 999
    maxSpecTrans = -1
    minSpecEng = 999
    maxSpecEng = -1
    for s in specsTrans:
        num = int(s.group(2))
        if num < minSpecEng:
            minSpecEng = num
        if num > maxSpecTrans:
            maxSpecTrans = num
        numsTrans[num] = 1
    for s in specsEng:
        num = int(s.group(2))
        if num < minSpecEng:
            minSpecEng = num
        if num > maxSpecEng:
            maxSpecEng = num
        numsEng[num] = 1
    if maxSpecEng != maxSpecTrans and minSpecEng != minSpecTrans:
        probs.append("Range of args doesn't match between translation and English.")
    if maxSpecTrans > 10:
        probs.append('Passing %d args to String.format() is not supported.' % (maxSpecTrans + 1))
        maxSpecTrans = 10
    for i in range(maxSpecTrans):
        if not i in numsTrans:
            probs.append('Format specifier {%d} not found.' % i)
            if len(probs) > 3:
                break
        else:
            if not i in numsEng:
                probs.append("Format specifier {%d} doesn't appear in English Translation"  % i)
                if len(probs) > 3:
                    break
    return probs

ABBREVIATION_PAT = re.compile(r"e\.?g\.?",re.IGNORECASE)
COMMON_TYPOS_PAT = re.compile(r"\s?(adn|teh|definately|instiute|sotp|pythno|aswell|impirt)\s",re.IGNORECASE)
AND_OR_BUT_PAT = re.compile(r"^(but|and)|\.(\s)?(but|and)",re.IGNORECASE)
CAN_NOT_PAT = re.compile(r"can\snot",re.IGNORECASE)
DIR_PAT = re.compile(r"dir(?![a-z])|directory",re.IGNORECASE)
FNAME_PAT = re.compile(r"fname|filename",re.IGNORECASE)
SHOULD_OF_PAT = re.compile(r"(((sh)|(w)|(c)(ould))|(must))(\s)(of)",re.IGNORECASE)
FIND_CURLY_QUOTE_PAT = re.compile(r"s/%s|%s|%s|%s/g" % (chr(145), chr(146), chr(147), chr(148)))

CHECK_SEMIPLURAL = TextCheck(1, '[a-z]\(s\)(?![a-z])', 'Use plural instead of English-only "xxx(s)" construction.')
CHECK_OLDSTYLE_PUNCT = TextCheck(2, r'[-;:!.?]  [A-Za-z]', 'In English, use only a single space after punctuation.')
CHECK_FORMAT_SPECIFIERS = TextCheck(3, _checkFormatSpecs)
CHECK_SHOUT = TextCheck(4, _checkShout)

CHECK_SIZE = TransCorrCheck(5, _checkSizeCorrel)
CHECK_FORMAT_SPECIFIERS_CORRELATION = TransCorrCheck(6, _checkTransFormatSpecs)

CHECK_BRACKET_PAIRS = TextCheck(7, codescan.matchPairs)
CHECK_ORPHANED_BACKSLASHES = TextCheck(8, r"\\(?!\\)", 'Orphaned backslash.')
CHECK_EG = TextCheck(9, ABBREVIATION_PAT,"Don't abbreviate eg.")
CHECK_COMMON_TYPOS = TextCheck(10, COMMON_TYPOS_PAT, 'There is a common typo in this string.')
CHECK_CAN_NOT = TextCheck(12, CAN_NOT_PAT, "Use cannot instead of can not.")
CHECK_AND_OR_BUT = TextCheck(11, AND_OR_BUT_PAT, "Don't start sentences with 'and' or 'but'.")
CHECK_CONTRACTIONS = TextCheck(13, r"([A-Za-z0-9-]+)\'(t|ll)", "Try to avoid contractions.")
CHECK_DIR = TextCheck(14, DIR_PAT, "Don't use both dir or directory. Use folder instead.")
CHECK_FNAME = TextCheck(15, FNAME_PAT, 'Use file name instead of filename or fname.')
CHECK_INTERNET = TextCheck(16, r'internet', 'Capitalize the "I" in Internet.')
CHECK_EMAIL = TextCheck(17, r'e-mail', 'Use email(without the hyphen) instead of e-mail.')
CHECK_SPACES = TextCheck(18, r"\s(\,|\.|\?|\;|\:)", "Make sure there are no spaces before punctuation")
CHECK_COMMA = TextCheck(19, r",\s?([A-Za-z0-9-]+)\s?and", "Use a comma before 'and'.")
CHECK_SEMI_COLON = TextCheck(20, r",(\s?)(?=[however])", 'In English "however" should be preceded by a semi-colon and not a comma.')
CHECK_ALOT = TextCheck(21, r"\s?(alot|Alot)\s", 'Use "a lot" not "alot".')
CHECK_CPU_RAM = TextCheck(22, r"cpus?|ram|((dv)|(c))ds?|usb", 'Capitalize common acronyms.')
CHECK_SHOULD_OF = TextCheck(23, SHOULD_OF_PAT, "Correct grammer is 'have' not 'of'.")
CHECK_TTY = TextCheck(24, r"(\*|\_)[A-Za-z0-9-]+(\*|\_)", "Don't empasize words with *bold* or _underlined_.")
CHECK_BACKWARDS = TextCheck(25, r"((any|some)\s(where|more))|(back|for)\s?wards", 'It is (back/for)ward not (back/for)wards')
CHECK_DEPRICATED = TextCheck(26, r"depreciate(d?)", "It is spelled depricate(d).")
CHECK_SHORTEN = TextCheck(27, r"((((d|D)ue)\stoo?)|(in\sspite\sof))(\sthe\sfact(\sthat)?)", 'Try to shorten this string.')
CHECK_REGARDING = TextCheck(28, r"\s((r|R)(e|E))+?(\.|\:)?(re|RE)?\s", "Don't abbreviate regarding.")
CHECK_ETC = TextCheck(29, r"(e|E)tc(\.?)+", "Don't abbreviate etcetera.")
CHECK_PERCENT = TextCheck(30, r"(p|P)er\scent", "Don't put a space in the middle of percent.'")
CHECK_CTRL_ALT_F = TextCheck(31, _checkKeyOrder)
CHECK_SIZE_ABBREVIATION = TextCheck(32, r"\b[MGKT]b|\b[mgkt][bB]|[a-z][bB]ytes|\b[kKmMgGtT]i[Bb]", "Use size abbreviations like this: MB, KB, GB, etc.")
CHECK_MHZ = TextCheck(33, r"[mgkt][hH][zZ]|[mgktMGKT]h[zZ]", "Correct form is MHz or GHz")
CHECK_ELLIPSIS = TextCheck(34, r"\[\.*\]", "Avoid using ellipsis.")
CHECK_BANDWIDTH_ABBREVIATION = TextCheck(35, _checkBandwidthAbbreviation)
CHECK_CURLY_QUOTES = TextCheck(36, FIND_CURLY_QUOTE_PAT, "Don't use curly quotes.")

STANDARD_TEXT_CHECKS = [CHECK_SEMIPLURAL, CHECK_OLDSTYLE_PUNCT, CHECK_FORMAT_SPECIFIERS,
CHECK_SHOUT, CHECK_BRACKET_PAIRS, CHECK_ORPHANED_BACKSLASHES,CHECK_EG, CHECK_COMMON_TYPOS,
CHECK_AND_OR_BUT, CHECK_CAN_NOT, CHECK_CONTRACTIONS, CHECK_DIR, CHECK_FNAME, CHECK_INTERNET,
CHECK_EMAIL, CHECK_SPACES, CHECK_COMMA, CHECK_SEMI_COLON, CHECK_ALOT, CHECK_SHOULD_OF, CHECK_TTY,
CHECK_BACKWARDS, CHECK_DEPRICATED, CHECK_SHORTEN, CHECK_REGARDING, CHECK_ETC, CHECK_PERCENT,
CHECK_CTRL_ALT_F, CHECK_SIZE_ABBREVIATION, CHECK_MHZ, CHECK_ELLIPSIS, CHECK_BANDWIDTH_ABBREVIATION,
CHECK_CURLY_QUOTES]

STANDARD_TRANS_TEXT_CHECKS = [CHECK_FORMAT_SPECIFIERS, CHECK_SHOUT, CHECK_ORPHANED_BACKSLASHES, CHECK_BRACKET_PAIRS,
CHECK_EG, CHECK_INTERNET, CHECK_EMAIL, CHECK_CPU_RAM, CHECK_TTY, CHECK_REGARDING, CHECK_ETC, CHECK_CTRL_ALT_F, CHECK_ELLIPSIS,
CHECK_CURLY_QUOTES]

TRANS_CORRELATION_CHECKS = [CHECK_SIZE, CHECK_FORMAT_SPECIFIERS_CORRELATION]

class FileLocation:
    def __init__(self, path, line=0):
        self.path = path
        self.line = line
    def __setattr(self, attr, val):
        if attr == 'path':
            val = unicode(val, 'utf-8')
        elif attr == 'line':
            val = int(line)
        else:
            return
        self.__dict__[attr] = val
    def __str__(self):
        return self.__unicode__().encode('utf-8')
    def __unicode__(self):
        if self.line:
            return u'%s(%d)' % (self.path, self.line)
        return self.path

def screenEnglish(value, notes):
    warnings = []
    for tc in STANDARD_TEXT_CHECKS:
        msg = tc.check(value, notes)
        if msg:
            warnings.append(msg)
    return warnings

def screenTrans(value, notes, eng):
    warnings = []
    for tc in STANDARD_TRANS_TEXT_CHECKS:
        msg = tc.check(value, notes)
        if msg:
            warnings.append(msg)
    for cc in TRANS_CORRELATION_CHECKS:
        msg = cc.check(value, notes, eng)
        if msg:
            warnings.append(msg)
    return warnings

_UNICODE_TYPE = type(u'')
class StrDef:
    def __setattr__(self, attr, val):
        vtype = type(val)
        if attr == 'txt':
            if vtype != _UNICODE_TYPE:
                vtype = unicode(str(val), 'utf-8')
            self.__dict__['warnings'] = None
        self.__dict__[attr] = val
    def __cmp__(self, rhs):
        return cmp(self.id, rhs.id)
    def __init__(self, id, txt, locale):
        self.id = id
        self.txt = txt
        self.locale = locale
        self.fileLocs = []
        self.src = None
        self.trans = []
        self._warnings = None
        self.warned = False
    def getWarningText(self):
        wtxt = u''
        warnings = self.getWarnings()
        if warnings:
            val = self.getValue()
            if len(val) > 20:
                val = val[0:20] + u'...'
            wtxt += ',\n    '.join([str(x) for x in self.fileLocs]) + ' -- "%s":\n' % val
            wtxt += '    ' + '\n    '.join(warnings)
        return wtxt
    def warn(self):
        if not self.warned:
            wtxt = self.getWarningText()
            if wtxt:
                print(wtxt)
                self.warned = True
            return bool(wtxt)
    def addLoc(self, floc):
        self.fileLocs.append(floc)
    def getNote(self):
        m = NOTE_PAT.match(self.txt)
        if m:
            return m.group(2)
        return u''
    def getValue(self):
        m = NOTE_PAT.match(self.txt)
        if m:
            return m.group(1)
        return self.txt
    def getId(self):
        m = NOTE_PAT.match(self.id)
        if m:
            return m.group(1)
        return self.id
    def getWordCount(self):
        words = [w for w in WORDSPLIT_PAT.split(self.getValue()) if w]
        return len(words)
    def getWarnings(self):
        if self._warnings is None:
            v = self.getValue()
            n = self.getNote()
            i = self.getId()
            if self.locale.startswith('en'):
                self._warnings = screenEnglish(v, n)
            else:
                self._warnings = screenTrans(v, n, i)
        return self._warnings
    def __str__(self):
        return self.__unicode__().encode("utf-8")
    def __unicode__(self):
        if self.locale == 'en':
            txt = u'_("%s")' % self.txt
        else:
            txt = u'"%s": "%s"' % (self.id, self.txt)
        loc = unicode(self.fileLocs[0])
        return loc + u':\n    ' + txt

