#
# $Id: check_ant_timeout.py 10571 2011-07-06 19:41:53Z ahartvigsen $
#
# Proprietary and confidential.
# Copyright $Date:: 2011#$ Perfect Search Corporation.
# All rights reserved.
#
import xml.dom.minidom, sys, os

def checkAntTimeout(buildDir):
    failed = minutes = exitCode = False
    test_folder = os.path.join(buildDir, 'Testing')
    tag_file = os.path.join(test_folder, 'TAG')
    try:
        t = file(tag_file).readline().strip()
        dom = xml.dom.minidom.parse(os.path.join(test_folder, t, 'Test.xml'))
        t.close()
        status = dom.getElementsByTagName('Test')
        for s in status:
            if 'Status' in s.attributes.keys():
                failed = (s.attributes['Status'].value == 'failed')
                break
            time = dom.getElementsByTagName('ElapsedMinutes')
            minutes = (_get_xml_text(time[0].childNodes) == '30')
            named_measurements = dom.getElementsByTagName('NamedMeasurement')
            for nM in named_measurements:
                if nM.attributes['name'].value == 'Exit Code':
                    exitCode = (_get_xml_text(nM.getElementsByTagName('Value')[0].childNodes) == 'Timeout')
                    break
                if failed and minutes and exitCode:
                    rerun = os.path.join(test_folder, 'rerun')
                    if os.path.exists(rerun):
                        os.remove(rerun)
                    else:
                        rerun = open(rerun, 'w')
                        rerun.close()
                        return self._last_started
    except:
        pass
    if not failed and not minutes and not exitCode:
        return 0
    else:
        return 1

if __name__ == '__main__':
    exitCode = checkAntTimeout(sys.argv[1])
    sys.exit(exitCode)