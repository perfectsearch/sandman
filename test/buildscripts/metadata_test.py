import os
import sys
import StringIO
import tempfile
import shutil
import subprocess
from unittest2 import TestCase
try:
    import bzrlib
except:
    sys.path.append('c:/Program Files (x86)/Bazaar/lib/library.zip')
    import bzrlib
import vcs
import metadata
import component
from testsupport import checkin, officialbuild

MY_DIR = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
MY_DATA_DIR = MY_DIR + '/data'


def save(path, txt):
    f = open(path, 'w')
    f.write(txt)
    f.close()


@officialbuild
class MetadataTest(TestCase):
    def test_dependencies(self):
        tmpdir = tempfile.mkdtemp()
        #print('running test in temporary repo %s' % tmpdir)
        cwd = os.getcwd()
        try:
            template1 = '[%s]' % metadata.DEPENDENCIES_SECTION
            template2 = template1 + '''
%s: code,%s.trunk.1.1 use: reusable
%s: code,%s.trunk.1.1 use: reusable
'''
            template3 = template1 + '''
%s: code,%s.trunk.2.1 use: reusable
%s: code,%s.trunk.1.1 use: reusable
'''
            files = {
                'a': template2 % ('b', 'b', 'c', 'c'),
                'b': template1,
                'c': template3 % ('b', 'b', 'd', 'd'),
                'd': template1
            }
            testRepos = ['a', 'b', 'c', 'd']
            for t in testRepos:
                repoPath = os.path.join(tmpdir, 'trunk', t)
                os.makedirs(os.path.join(tmpdir, 'trunk', t))
                branchPath = repoPath + '/code'
                #print('init %s' % branchPath)
                vcs.init(branchPath, False)
                filePath = branchPath + '/' + metadata.METADATA_FILE
                save(filePath, files[t])
                os.chdir(branchPath)
                #print('adding %s' % filePath)
                vcs.add(filePath)
                #print('checking in %s' % filePath)
                vcs.checkin(filePath, 'Test', True)
                vcs.tag('%s.trunk.1.1 use: reusable' % t)
                if t == 'b':
                    #subprocess.Popen(['bzr', 'tag', 'first'], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
                    filePath = branchPath + '/dependencies2.txt'
                    save(filePath, files[t])
                    vcs.add(filePath)
                    vcs.checkin(filePath, 'Test', True)
                    vcs.tag('%s.trunk.2.1 use: reusable' % t)
                #subprocess.Popen(['bzr', 'tags'])
            working_repo = vcs.WorkingRepository()
            working_repo._init(tmpdir, tmpdir, tmpdir)
            prob = metadata.get_components_inv_dep_order(working_repo, 'win_x64', 'a', tmpdir, 'trunk', '')
            comp = [
                component.Component('b', 'trunk', 'b.trunk.1.1 use: reusable', 'code'),
                component.Component('d', 'trunk', 'd.trunk.1.1 use: reusable', 'code'),
                component.Component('c', 'trunk', 'c.trunk.1.1 use: reusable', 'code'),
                component.Component('a', 'trunk', 'a.trunk.1.1 use: reusable', 'code')
                ]
            if False:
                for c in comp:
                    print("comp = " + str(c))
                for c in prob:
                    print("prob = " + str(c))
            # prob will have buildscripts; comp doesn't
            prob = [p for p in prob if p.name != 'buildscripts']
            self.assertEquals(len(comp), len(prob))
            for i in range(len(comp)):
                self.assertEquals(comp[i].name, prob[i].name)
        finally:
            os.chdir(cwd)
            shutil.rmtree(tmpdir)

    @checkin
    def test_visit(self):
        class Visitor:
            def __init__(self):
                self.visited = []

            def visit(self, folder, item, relativePath):
                #print('visited %s' % item)
                self.visited.append(item)
        visitor = Visitor()
        path = os.path.join(MY_DATA_DIR, 'visit_test')
        visitedFiles, visitedFolders = metadata.visit(path, visitor, report=False)
        self.assertEqual(6, visitedFiles)
        self.assertEqual(3, visitedFolders)
        self.assertTrue('x.txt' in visitor.visited)
        self.assertTrue('c.txt' in visitor.visited)
        self.assertFalse('d.txt' in visitor.visited)

    @checkin
    def test_shouldRecurse(self):
        conf = metadata.Conf(MY_DATA_DIR)
        self.assertTrue(conf.shouldRecurse('subdir'))
        self.assertFalse(conf.shouldRecurse('built.win64'))

    @checkin
    def test_shouldCheck(self):
        conf = metadata.Conf(MY_DATA_DIR)
        self.assertTrue(conf.shouldCheck('y.java'))
        self.assertTrue(conf.shouldCheck('y.cpp'))
        self.assertTrue(conf.shouldCheck('y.py'))
        self.assertTrue(conf.shouldCheck('y.js'))
        self.assertTrue(conf.shouldCheck('y.h'))
        self.assertFalse(conf.shouldCheck('x.txt'))

    @checkin
    def test_normLocales(self):
        abby = ['EN', 'fr-ca', 'zh']
        normal = ['en', 'fr', 'zh_CN']
        self.assertEqual(normal, metadata._normLocales(abby))

    @checkin
    def test_normPlatforms(self):
        abby = ['win32', 'lin64']
        normal = ['Linux 64-bit', 'Windows 32-bit']
        self.assertEqual(normal, metadata._normPlatforms(abby))
