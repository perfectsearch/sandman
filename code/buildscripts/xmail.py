#!/usr/bin/env python
# 
# $Id: xmail.py 9318 2011-06-10 02:37:10Z nathan_george $
# 
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
# 
import smtplib, mimetypes, os, re, platform
if platform.python_version().startswith('2.4'):
    # In Python 2.4, the modules we want sere structured somewhat differently...
    from email import Encoders
    from email.Message import Message
    from email.MIMEAudio import MIMEAudio
    from email.MIMEBase import MIMEBase
    from email.MIMEImage import MIMEImage
    from email.MIMEMultipart import MIMEMultipart
    from email.MIMEText import MIMEText
    encoders = Encoders
else:
    from email import encoders
    from email.message import Message
    from email.mime.audio import MIMEAudio
    from email.mime.base import MIMEBase
    from email.mime.image import MIMEImage
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
from email.Header import Header
from email.Utils import parseaddr, formataddr

_PREFERRED_NONASCII_CHARSET = 'UTF-8'
_7BIT_CHARSET = 'US-ASCII'

ADDRLIST_METAVAR = "ADDRLIST"
ADDRLIST_DESC = "Semicolon- or comma-delimited list of emails."

def addMailOptions(parser, to=True, cc=True, bcc=True, 
    attach=False, sender=False, subject=False):
    parser.add_option('--host', dest="host", help="SMTP host to relay message. Localhost assumed by default.")
    parser.add_option('--port', dest="port", help="Override standard port on SMTP host. (gmail=587)")
    parser.add_option('--tls', dest='tls', action='store_true', help='Use TLS (SSL) to talk to SMTP host.')
    parser.add_option('--username', dest="username", metavar="USER", help="Username to authenticate with SMTP host.")
    parser.add_option('--password', dest="password", metavar="PWD", help="Password to authenticate with SMTP host.")
    if to:
        parser.add_option('--to', dest="to", metavar=ADDRLIST_METAVAR, help=ADDRLIST_DESC)
    if cc:
        parser.add_option('--cc', dest="cc", metavar=ADDRLIST_METAVAR, help=ADDRLIST_DESC)
    if bcc:
        parser.add_option('--bcc', dest="bcc", metavar=ADDRLIST_METAVAR, help=ADDRLIST_DESC)
    if attach:
        parser.add_option('--attach', dest='attach', metavar="FILELIST", help='Semicolon- or comma-delimited list of files to attach')
    if subject:
        parser.add_option('--subject', dest="subject", metavar="SUB", help="Subject for message.")
    if sender:
        parser.add_option('--sender', dest="sender", metavar="ADDR", help="Address to use as message sender.")

def _getUnique(items):
    uniques = {}
    for x in items:
        uniques[x] = 1
    uniques = uniques.keys()[:]
    uniques.sort()
    return uniques

_UNICODE_TYPE = type(u'')
_STR_TYPE = type('')

def normAddressList(txt, assumedCharset=_7BIT_CHARSET):
    items = []
    if txt:
        if type(txt) == _UNICODE_TYPE or type(txt) == _STR_TYPE:
            txt, assumedCharset = safelyEncode(txt, assumedCharset)
            txt = txt.replace(';', ',')
            items = [formataddr(parseaddr(x.strip())) for x in txt.split(',') if x.strip()]
        else:
            assert(type(txt) == type([]))
            items = txt
            newItems = []
            for addr in items:
                txt, assumedCharset = safelyEncode(txt, assumedCharset)
                newItems.append(formataddr(parseaddr(txt)))
            items = newItems
        items = _getUnique(items)
        items.sort()
    return items, assumedCharset

def getRawAddress(address):
    name, addr = parseaddr(address)
    return addr

def complementList(items, rawList):
    complement = []
    if items:
        for addr in items:
            if not (getRawAddress(addr) in rawList):
                complement.append(addr)
    return complement

def safelyEncode(value, assumedCharset = _7BIT_CHARSET):
    if not value:
        return '', assumedCharset
    if type(value) != _UNICODE_TYPE:
        #print('checking encoding of non-unicode %s' % value)
        charset = assumedCharset
        try:
            #print('trying encoding %s' % charset)
            utxt = unicode(value, charset)
            #print('yep')
            return value, charset
        except:
            # Must try UTF-8 first, because it can be validated;
            # if we fall back to iso 8859-1, we don't have any way
            # to prove it's correct.
            charset = _PREFERRED_NONASCII_CHARSET
            try:
                #print('trying encoding %s' % charset)
                value = unicode(value, charset)
                #print('yep')
            except:
                #print('trying encoding ISO-8859-1')
                value = unicode(value, 'ISO-8859-1')
                #print('yep')
    else:
        charset = assumedCharset
        if assumedCharset == _7BIT_CHARSET:
            # See if 7-bit is adequate...
            try:
                value.encode(assumedCharset)
            except:
                charset = _PREFERRED_NONASCII_CHARSET
    # Any time we have non-ASCII, prefer transmitting in utf-8.
    #print('value is now %s' % repr(value))
    value = value.encode(_PREFERRED_NONASCII_CHARSET)
    return value, charset

def attachFile(path, multipart, assumedCharset=_7BIT_CHARSET):
    # Guess the content type based on the file's extension.  Encoding
    # will be ignored, although we should check for simple things like
    # gzip'd or compressed files.
    ctype, encoding = mimetypes.guess_type(path)
    if ctype is None or encoding is not None:
        # No guess could be made, or the file is encoded (compressed), so
        # use a generic bag-of-bits type.
        ctype = 'application/octet-stream'
    maintype, subtype = ctype.split('/', 1)
    if maintype == 'text':
        fp = open(path, 'rt')
        txt = fp.read()
        txt, charset = safelyEncode(txt, assumedCharset)
        # If the file was not pure ascii, but we encoded it,
        # report the encoding we're *going* to use, not the one
        # the file was in originally.'
        if charset != _7BIT_CHARSET:
            charset = _PREFERRED_NONASCII_CHARSET
        msg = MIMEText(txt, subtype, charset)
        fp.close()
    elif maintype == 'image':
        fp = open(path, 'rb')
        msg = MIMEImage(fp.read(), _subtype=subtype)
        fp.close()
    elif maintype == 'audio':
        fp = open(path, 'rb')
        msg = MIMEAudio(fp.read(), _subtype=subtype)
        fp.close()
    else:
        fp = open(path, 'rb')
        msg = MIMEBase(maintype, subtype)
        txt = fp.read()
        msg.set_payload(fp.read())
        
        fp.close()
    # Set the filename parameter
    msg.add_header('Content-Disposition', 'attachment', filename=os.path.basename(path))
    multipart.attach(msg)

def sendmail(body, sender=None, subject=None, to=[], cc=[], bcc=[], 
    attach=[], host=None, port=None, assumedCharset=_7BIT_CHARSET, hdrCharset=None, 
    username=None, password=None, tls=None, mailerName='xmail.py', mailer=None,
    options=None, simulate=False):
    if not (options is None):
        if sender is None and hasattr(options, 'sender'):
            sender = getattr(options, 'sender')
        if subject is None and hasattr(options, 'subject'):
            subject = getattr(options, 'subject')
        if (not to) and hasattr(options, 'to'):
            to = getattr(options, 'to')
        if (not cc) and hasattr(options, 'cc'):
            cc = getattr(options, 'cc')
        if (not bcc) and hasattr(options, 'bcc'):
            bcc = getattr(options, 'bcc')
        if (not attach) and hasattr(options, 'attach'):
            attach = getattr(options, 'attach')
        if host is None and hasattr(options, 'host'):
            host = getattr(options, 'host')
        if port is None and hasattr(options, 'port'):
            port = getattr(options, 'port')
        if username is None and hasattr(options, 'username'):
            username = getattr(options, 'username')
        if password is None and hasattr(options, 'password'):
            password = getattr(options, 'password')
        if tls is None and hasattr(options, 'tls'):
            tls = getattr(options, 'tls')
        # Change next bool to True for debugging
        if False:
            pwd = ''
            if password:
                pwd = '*****'
            print('sendmail(body, sender=' + repr(sender) + ', subject=' + repr(subject) +
                ',\n  to=' + repr(to) +
                ',\n  cc=' + repr(cc) +
                ',\n  bcc=' + repr(bcc) +
                ',\n  attach=' + repr(attach) +
                ',\n  host=' + repr(host) + ', port=' + repr(port) + 
                ',\n  username=' + repr(username) + ', password=' + repr(pwd) +
                ',\n  tls=' + repr(tls) + ')')
    if tls is None: 
        tls = not bool(port is None) and not (str(port) == '25')
    else:
        tls = bool(tls)
    # In the code below, we're going to a fair amount of trouble to
    # make sure we send the message in a way that supports extended characters.
    # We examine all the headers before we decide what charset to actually
    # use for header encoding. We do a similar calculation for the body,
    # although emails can use different charsets for the two sections.
    body, bodyCharset = safelyEncode(body)
    #body = unicode(body, bodyCharset)
    # If the file was not pure ascii, but we encoded it,
    # report the encoding we're *going* to use, not the one
    # the file was in originally.'
    if bodyCharset != _7BIT_CHARSET:
        bodyCharset = _PREFERRED_NONASCII_CHARSET
    if attach:
        if type(attach) == _STR_TYPE:
            attach = [x.strip() for x in attach.replace(';',',').split(',')]
        outer = MIMEMultipart()
        outer.preamble = 'This is a multi-part MIME message.\n'
        if body:
            bodyPart = MIMEText(body, 'plain', bodyCharset)
            bodyPart['Content-Disposition'] = 'inline'
            outer.attach(bodyPart)
        for item in attach:
            if item:
                attachFile(item, outer)
    else:
        outer = MIMEText(body, 'plain', bodyCharset)
        outer['Content-Disposition'] = 'inline'
    if host == 'localhost':
        host = None
    if hdrCharset is None:
        hdrCharset = assumedCharset
    sender, hdrCharset = safelyEncode(sender, hdrCharset)
    mailerName, hdrCharset = safelyEncode(mailerName, hdrCharset)
    subject, hdrCharset = safelyEncode(subject, hdrCharset)
    if to:
        to, hdrCharset = normAddressList(to, hdrCharset)
    rawTo = [getRawAddress(x) for x in to]
    dest = rawTo
    if cc:
        cc, hdrCharset = normAddressList(cc, hdrCharset)
    # Don't cc: anyone who's already on the to: line
    cc = complementList(cc, dest)
    dest.extend([getRawAddress(x) for x in cc])
    if bcc:
        bcc, hdrCharset = normAddressList(bcc, hdrCharset)
    # Don't bcc: anyone who's already on the to: or cc: line
    bcc = complementList(bcc, dest)
    dest.extend([getRawAddress(x) for x in bcc])
    dest.sort()
    if to:
        outer['To'] = str(Header(', '.join(to), hdrCharset))
    outer['From'] = str(Header(sender, hdrCharset))
    if cc:
        outer['CC'] = str(Header(', '.join(cc), hdrCharset))
    # Don't add a header for bcc; that's what makes it "blind"
    outer['Subject'] = str(Header(subject, hdrCharset))
    if mailerName:
        outer['X-Mailer'] = str(Header(mailerName, hdrCharset))
    if simulate:
        print(outer.as_string())
    else:
        if port:
            port = int(port)
        if mailer is None:
            #print('initing smtplib with SMTP(%s, %s)' % (repr(host), repr(port)))
            mailer = smtplib.SMTP(host, port)
        if tls:
            #print('starting TLS')
            mailer.starttls()
        else:
            #print('connecting')
            mailer.connect()
        if username:
            #print('logging in')
            mailer.login(username, password)
        mailer.sendmail(sender, dest, outer.as_string())
        mailer.quit()

def _hasValue(options, name):
    return hasattr(options, name) and bool(getattr(options, name))

def hasDest(options):
    return bool(options) and (_hasValue(options, 'to') or _hasValue(options, 'cc') or _hasValue(options, 'bcc'))

def hasHostInfo(options):
    return bool(options) and (_hasValue(options, 'host') or _hasValue(options, 'port')) 

