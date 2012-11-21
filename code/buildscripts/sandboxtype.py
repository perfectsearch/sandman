import re
import os
import ConfigParser
import ioutil
import dateutils

'''The canonical name of a sandbox that has continuous semantics.'''
CONTINUOUS_VARIANT = 'continuous'
'''The canonical name of a sandbox that has official semantics.'''
OFFICIAL_VARIANT = 'official'
'''The canonical name of a sandbox that has experimental semantics.'''
EXPERIMENTAL_VARIANT = 'dev'

_OFFICIAL_VARIANT_PAT = re.compile('.*(official).*', re.IGNORECASE)
_STANDARD_NAME_PAT = re.compile(r'^([^.]+)\.(.+)\.([^.]+)$', re.IGNORECASE)

_SETTINGS_SECTION = 'settings'
_SHOULD_PUBLISH_KEY = 'should publish'
_SHOULD_NOTIFY_KEY = 'should notify'
_SHOULD_RESET_ON_START = 'should reset on start'
_TEST_ATTRS_KEY = 'test attrs'
_TEST_MODE_ATTRS_KEY = 'test mode attrs combos'
_REPORT_ALWAYS_KEY = 'report always'
_REPORT_FAILED_NOT_PROBLEMATIC_KEY = 'report failed not problematic'

_SANDBOXTYPES_CONF = os.path.join(os.path.dirname(__file__),'sandboxtypes.conf');
_types_conf=ConfigParser.RawConfigParser()


if os.path.isfile(_SANDBOXTYPES_CONF):
    _types_conf.read(_SANDBOXTYPES_CONF)
else:
    raise Exception( 'Warning! Cannont load sandbox types!')


_BOOL_TRUE_PAT = re.compile('t(rue)?|y(es)?|on|-?1|enabled?')
def _text_to_bool(txt):
    if txt:
        txt = txt.strip().lower()
        return 'yt1'.find(txt[0]) > -1
    return txt


# We've implemented two variations of many methods here -- one that's static and
# called with a string, and one that's a member, called on a Sandbox object. The
# reason for both is that before a Sandbox is created, we often need to look at
# strings/paths to understand what they imply -- and after a Sandbox is created,
# we want to call the equivalent logic on the object instead of figuring out
# which salient characteristic of the object we should pass to the static method
# that takes a string.

def _get_variant_from_path(path):
    # Should only be called on str or unicode objects.
    assert(hasattr(path, 'lower'))
    name = ioutil.norm_seps(path, trailing=False)
    i = name.rfind('/')
    if i > -1:
        name = name[i + 1:]
    m = _STANDARD_NAME_PAT.match(name)
    if m:
        return m.group(3)
    raise SandboxNameError(path)

def _variant_is_continuous(v):
    return v.lower().find(CONTINUOUS_VARIANT) > -1

def _variant_is_official(v):
    return bool(_OFFICIAL_VARIANT_PAT.match(v))

def supports_publish(path):
    '''
    Return True if the specified sandbox could be a candidate for build
    publication.

    Typically publishing is only supported for official sandboxes on canonical
    build machines, and only for platforms where we intend to preserve built
    output. The sandbox layer cannot speak for all those constraints; it
    answers only from the standpoint of sandbox semantics.

    Note: this information only answers a question about possibility, not
    about choice. A sandbox may support publishing but have it disabled. Compare
    the Sandbox.get_should_publish() method.

    @param path An actual or proposed path to a sandbox root. Could be
    relative (as small as just a folder name) or absolute.
    '''
    return SandboxType(None, path=path).supports_publish();

def supports_checkouts(path):
    '''
    Return True if it is valid for this sandbox to have code checked out in
    either its code root or its test root. Typically this is only the case for
    experimental sandboxes.

    @param path An actual or proposed path to a sandbox root. Could be
    relative (as small as just a folder name) or absolute.
    '''
    return SandboxType(None, path=path).supports_checkouts()

class SandboxType():
    def __init__(self, sb, path=None, variant=None):
        self._sb = sb;
        if (self._sb is not None):
            self._variant = self._sb.get_variant().lower()
        elif path is not None:
            self._variant = _get_variant_from_path(path).lower()
        elif variant is not None:
            self._variant = variant.lower()
        else:
            raise Exception("Variant not set!")

    def get_sb(self):
        return self._sb;

    def get_style(self):
        if _types_conf.has_section(self.get_variant()):
            return self.get_variant();
        return 'experimental'

    def get_variant(self):
        return self._variant

    def _is_continuous(self):
        '''
        Return True if the specified sandbox has continuous semantics.

        Continuous semantics imply that a sandbox is intended for regular eval and
        should never have code checked out; eval cycles run at background priority
        with no more than one continuous build running at a time. Continuous
        sandboxes call "make clean" on the first eval cycle after midnight, each
        day, and they may run incremental builds. By default, continuous sandboxes
        run all tests tagged "pushok" in their testing phase.

        On canonical build machines, continous also implies that eval results
        should be reported to our dashboard in the "Continuous" section. However,
        the notion of canonical build machines is outside the scope of concern of
        this module, so only the first half of the semantics are tested here.
        '''
        return _variant_is_continuous(self.get_variant())
    def _is_official(self):
        '''
        Return True if the specified sandbox has official semantics.

        Official semantics imply that a sandbox is intended for occasional,
        automated evaluation (either by schedule or by manual request). Official
        builds can run at any time, and they run at normal priority (possibly
        starving active continuous builds). Such sandboxes should never have code
        checked out; they are fully reset (code root and build root nuked) on each
        eval. By default, official sandboxes run all tests tagged "officialbuild"
        in their testing phase.

        On canonical build machines, official also implies that results of builds
        should be reported to our dashboard in the "Official" section. However, the
        notion of canonical build machines is outside the scope of concern of this
        module, so only the first half of the semantics are tested here.
        '''

        return _variant_is_official(self.get_variant())
    def _is_experimental(self):
        '''
        Return True if the specified sandbox has experimental semantics.

        Experimental semantics imply that a sandbox is intended for use by a
        developer. Code can be checked out. The automated eval cycle encapsulated by
        "sadm start" may occasionally be used, but "sadm verify" will be more
        common, and granular commands (makesb, testsb, etc) are also important.
        Official builds can run at any time, and they run at normal priority
        (possibly starving active continuous builds). The developer decides when and
        if the build root is cleaned.

        Experimental sandboxes should rarely be used on sandboxes hosted by
        canonical build machines, unless a developer is debugging. Build machines
        that run continuous or official builds but that are not canonical (e.g.,
        they're from an OS that we only monitor for informational purposes) always
        report to the "Experimental" section of the build dashboard, but this is
        a behavior invisible to this python module and beyond our scope of concern.
        '''

        v = self.get_variant()
        return (not _variant_is_continuous(v)) and (not _variant_is_official(v))

    def _set_conf(self, section, key, value, persist=True):
        if (self._sb is None):
            raise Exception('sb is None! Cannot save conf value!')
        # We save conf values to
        return self._sb._set_conf(section, key, value, persist)
    def _get_conf(self, section, key, default=None):
        '''
        Get the conf value, first from the sandbox.conf file, then from
        buildtypes.conf file. If the variant doesn't exist in the buildtypes.conf
        file use the default variant.
        '''
        value = None

        if self._sb is not None:
            value = self._sb._get_conf(section, key)

        if value:
            return value

        if _types_conf.has_section(self.get_variant()):
            if _types_conf.has_option(self.get_variant(), key):
                return _types_conf.get(self.get_variant(), key)

        if _types_conf.has_option('DEFAULT', key):
            return _types_conf.get('DEFAULT', key)

        return default
    def _get_date_conf(self, section, key, default=None):
        value = self._get_conf(section, key, default)
        if value:
            value = dateutils.parse_standard_date_with_tz_offset(value)
        return value
    def _set_date_conf(self, section, key, value):
        if value is not None:
            value = dateutils.format_standard_date_with_tz_offset(value)
        self._set_conf(section, key, value)

    def supports_checkouts(self):
        '''
        @return True if it is valid behavior to have checkouts in this sandbox.
        @see sandbox.supports_checkouts().
        '''
        return self._is_experimental()
    def get_should_schedule(self):
        '''
        Should we auto schedule this sandbox type?
        '''
        return self._is_continuous();
    def supports_publish(self):
        '''
        Return True if this sandbox supports publication of build results.
        '''
        return self._is_official()
    def get_should_publish(self):
        '''
        @return True if sandbox's publish feature should be turned on.
        '''
        return _text_to_bool(self._get_conf(_SETTINGS_SECTION, _SHOULD_PUBLISH_KEY, 'f'))
    def set_should_publish(self, value):
        '''
        Change a sandbox's publish setting.

        @param value If True, and the sandbox supports publishing (@see the
               .get_should_publish() method), then publishing is enabled for the
               sandbox.
        '''
        value = bool(value)
        if value:
            if not self.supports_publish():
                raise Exception('This sandbox does not support publication.')
        self._set_conf(_SETTINGS_SECTION, _SHOULD_PUBLISH_KEY, value)
    def get_test_attrs(self):
        '''
        Returns a list of test types to run for a sandbox
        '''
        attrs = self._get_conf(_SETTINGS_SECTION, _TEST_ATTRS_KEY, 'not interactive')
        return attrs
    def get_test_mode_attrs_combo(self):
        '''
        Returns a list of test types to run for a sandbox
        '''
        attrs = self._get_conf(_SETTINGS_SECTION, _TEST_MODE_ATTRS_KEY, '[none; not interactive]')
        return attrs
    def get_notify_on_success(self):
        '''
        Returns if we should notify on success.
        '''
        return self._is_official()
    def get_do_notify(self):
        '''
        Returns if we should email someone.
        '''
        return _text_to_bool(self._get_conf(_SETTINGS_SECTION, _SHOULD_NOTIFY_KEY, 'f'))
    def get_always_report(self):
        '''
        Returns if we should always report the build status.
        '''
        return _text_to_bool(self._get_conf(_SETTINGS_SECTION, _REPORT_ALWAYS_KEY, 'f'))
    def get_failed_build_is_failed_report(self):
        '''
        Returns if the sandbox type should cause a FAILED build, otherwise a PROBLEMATIC build is returned.
        '''
        return _text_to_bool(self._get_conf(_SETTINGS_SECTION, _REPORT_FAILED_NOT_PROBLEMATIC_KEY, 'f'))
    def get_do_quick_build(self):
        '''
        Should this sandbox type do a quickbuild?
        '''
        return self._is_experimental()
    def get_do_build_if_tags_out_of_date(self):
        '''
        Only build if the tags are out of date.
        '''
        return self._is_official()
    def get_reset_on_start(self):
        '''
        Should we reset the sandbox when starting a build.
        '''
        return self._is_official() or _text_to_bool(self._get_conf(_SETTINGS_SECTION, _SHOULD_RESET_ON_START, 'f'))
    def get_clean_on_start(self):
        '''
        Clean sandbox on start? Since we reset an official sandbox, we don't need to clean it here.
        '''
        return self._is_continuous();
    def get_nice_build(self):
        '''
        Should we nice our task?
        '''
        return not self._is_official()
    def get_prompt_on_reset(self):
        '''
        Should we prompt the user when we reset this sandbox?
        '''
        return not self._is_official();
    def get_prompt_on_remove(self):
        '''
        Should we prompt on removal of a sandbox? Prompt on everything except official and continuous
        '''
        return not (self._is_official() or self._is_continuous())

if __name__ == '__main__':
    print 'DEFAULT-'
    for item in _types_conf.items('DEFAULT'):
        print item

    for section in  _types_conf.sections():
        print section + "-";
        for item in _types_conf.items(section):
            print item


