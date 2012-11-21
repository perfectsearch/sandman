#!/usr/bin/env python
'''
Execute a particular verb against a sandbox. Called by the "makesb" and "testsb"
bash scripts or batch files.
'''
import os
import re
import sys

import sadm
import sandbox

_verb_to_cmd = {
    'test': 'test.py',
    'build': 'build.py',
    'clean': 'build.py clean',
    'eval': 'eval.py',
    'verify': 'eval.py --report False',
    'publish': 'publish.py',
    'properties': 'sandbox.py properties',
    'tpv': 'sandbox.py targeted_platform_variant',
    'dependencies': 'metadata.py',
    'tools': 'check_tools.py',
    'config': 'build.py --prompt config'
}

_BZR_VERBS = re.compile('up(date)?|revert|merge|ci|commit|status|add|tags?|push|pull|revno|info|branch')
_SADM_VERBS = re.compile('init|start|stop|remove|reset|path|list')

def main(argv):
    # see if we're supposed to run this command against a different sandbox.
    sbspec = '.'
    del argv[0]
    if len(argv) >= 2:
        first = argv[0]
        if first == '-s':
            del argv[0]
            sbspec = argv[0]
            del argv[0]
        elif first.startswith('--sandbox') or first.startswith('--sb'):
            del argv[0]
            if '=' in first:
                sbspec = first.split('=')[1]
            else:
                sbspec = argv[0]
                del argv[0]

    # check to see if we have enough args.
    if len(argv) < 1:
        supported_verbs = _verb_to_cmd.keys()[:]
        supported_verbs.sort()
        supported_verbs = '|'.join(supported_verbs)
        supported_verbs = '(sandbox_property)|' + supported_verbs
        print('sbverb [-s <sandbox_spec>] %s [args]' % supported_verbs)
        return 1

    # Look up the script that corresponds to our verb.
    verb = argv[0].lower()
    script_args = argv[1:]
    script = _verb_to_cmd.get(verb, None)
    if not script:
        if _BZR_VERBS.match(verb):
            print('This looks like a bzr command.')
            sys.exit(1)
        if _SADM_VERBS.match(verb):
            print('This looks like a sadm command.')
            sys.exit(1)
        script = 'sandbox.py'
        script_args.insert(0, verb)

    # Now find the sandbox to which we're supposed to apply the verb.
    if sbspec == '.':
        root = sandbox.find_root_from_within(sbspec)
        if root:
            sandboxes = [sandbox.Sandbox(root)]
        else:
            print('%s is not within a sandbox.' % os.path.abspath('.'))
            return 1
    else:
        sandboxes = sadm._match_sandboxes('path', None, sbspec)
    if sandboxes:
        if len(sandboxes) == 1:
            sb = sandboxes[0]
            if verb == 'verify' and sb.get_sandboxtype().get_do_quick_build() and '--quick' not in script_args:
                script_args.append('--quick')
            if not sb.get_sandboxtype().get_do_quick_build() and '--quick' in script_args:
                script_args.remove('--quick')
            # Split cmd into script file and rest.
            i = script.find(' ')
            if i > -1:
                rest = script[i:]
                script = script[0:i]
            else:
                rest = ''

            # Now look for the appropriate buildscript .py file.
            script = os.path.join(sb.get_code_root(), 'buildscripts', script)
            if os.path.isfile(script):
                # Make sure we're using backslashes on Windows.
                if os.name == 'nt':
                    script = script.replace('/', '\\')
                # Quote if path has spaces.
                if ' ' in script:
                    script = '"%s"' % script
                script += rest
                # Re-quote any args that contain spaces
                for i in range(len(script_args)):
                    if ' ' in script_args[i] and not script_args[i].startswith('"'):
                        script_args[i] = '"%s"' % script_args[i]
                # Now run the script and report its exit code.
                cmd = 'python %s %s' % (script, ' '.join(script_args))
##                print('cmd=%s' % cmd)
                return os.system(cmd)
            else:
                # If we get here, then we never found the right .py file in the
                # buildscripts component.
                print('Could not find %s.' % script)
                return 1
        else:
            print('%d sandboxes match "%s".' % (len(sandboxes), sbspec))
            return 1
    else:
        print('No sandbox matches "%s".' % sbspec)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
