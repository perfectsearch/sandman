import string
import bzrlib
import re
import string

from bzrlib.commands import Command, register_command

_VALID_COMP_NAME_PAT = re.compile('[a-z][-_a-z0-9]*$', re.IGNORECASE)
class cmd_fast_branches(Command):
    ''' Getting branches must be fast. '''

    takes_args = ['repositorylocation']

    def run(self, repositorylocation):
        ''' return a pure list of valid branches (branch paths) '''
        transport = bzrlib.transport.get_transport(repositorylocation)
        branchinfo = ''
        branches = []
        try:
            branchinfo = transport.get_bytes('.bzrsupport/branchinfocache')
            for b in branchinfo.split('\n'):
                if not b.strip():
                    continue
                try:
                    parts = b.split()
                    if len(parts) == 4:
                        branchname,componentname,aspectname = parts[:3]
                        if componentname and aspectname and branchname and _VALID_COMP_NAME_PAT.match(componentname):
                            branches.append('\t'.join( parts))
                        else:
                            print 'bad branchpath name: %s' % branchpath
                            pass
                except:
                    pass
            if len(branches) < 1:
                raise Exception('not enough branches')
        except Exception as e:
            transport = bzrlib.transport.get_transport(repositorylocation)
            branches = []
            branchnames = transport.list_dir('')
            for branchname in branchnames:
                try:
                    components = [c for c in transport.list_dir(branchname) if _VALID_COMP_NAME_PAT.match(c)]
                    for component in components:
                        possibleaspects = transport.list_dir('/'.join([branchname, component]))
                        for aspect in possibleaspects:
                            if not aspect.startswith('.'):
##                                subdirs = transport.list_dir('/'.join((branch, component, aspect)))
##                                print subdirs
##                                if '.bzr' in subdirs:
                                branches.append('%s\t%s\t%s\t%s' % (branchname, component, aspect, ''))
                except:
                    pass

        branches.sort(key=string.lower)
        for b in branches:
            print b


register_command(cmd_fast_branches)

