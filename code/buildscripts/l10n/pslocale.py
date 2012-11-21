#!/usr/bin/env python
# 
# $Id: pslocale.py 9318 2011-06-10 02:37:10Z nathan_george $
# 
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.

_NAMES_BY_CODE = {
    'en': 'English',
    'fr': 'French',
    'pt': 'Portuguese',
    'it': 'Italian',
    'de': 'German',
    'es': 'Spanish',
    'ja': 'Japanese',
    'ko': 'Korean',
    'zh_TW': 'Chinese Traditional',
    'zh_CN': 'Chinese Simplified'
}
_STD_LOCALES = _NAMES_BY_CODE.keys()
_NAMES_BY_CODE['ma'] = 'Martian'

def getStandardLocales():
    '''
    Get list of locales that we commonly work with.
    '''
    global _STD_LOCALES
    return _STD_LOCALES

def standardize(code):
    '''
    Convert a locale code to something that PS locale-dependent layers expect. This value
    will always be valid in a call to python's locale module (e.g., setlocale()), but it
    will be simpler than some of the locales that the system might support, because it will
    not contain a codepage or currency annotation at the end (uz_UZ.utf8@cyrillic becomes
    uz_UZ).
    '''
    code = str(code).strip().lower().replace(' ','')
    n = len(code)
    if n > 5:
        j = code.find('@')
        if j > -1:
            code = code[0:j]
        j = code.find('.')
        if j > -1:
            code = code[0:j]
        n = len(code)
    if n == 2:
        if code == 'zh':
            code = 'zh_CN'
        return code
    if (n == 5) and (not code[2].isalnum()):
        return code[0:2] + '_' + code[3:].upper()
    if (n == 4):
        return code[0:2] + '_' + code[2:].upper()
    return None

def bestFit(code, noneOnExotic = False):
    '''
    Given a locale code, find the corresponding locale that is part of Perfect Search's
    standard inventory. This may change "fr_CA" into "fr", for example.
    '''
    code = standardize(code)
    if code:
        if code in _NAMES_BY_CODE:
            return code
        if (len(code) == 5):
            code = code[0:2]
            if code in _NAMES_BY_CODE:
                return code
        if not noneOnExotic:
            return code
    return None

def nameForCode(code, bestFit = False):
    '''
    Given a locale code, find a corresponding friendly name. For example,
    "en" is mapped to "English".
    '''
    code = standardize(code)
    if code:
        if code in _NAMES_BY_CODE:
            return _NAMES_BY_CODE[code]
        if (len(code) == 5) and bestFit:
            return nameForCode(code[0:2])
    return None
