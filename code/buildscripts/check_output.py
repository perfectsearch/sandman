# I'd like to use subprocess.check_output, even in python 2.6. However, it wasn't
# introduced till python 2.7. This patches the problem on old revs.

import subprocess

if not hasattr(subprocess, 'check_output'):
    import tempfile, os, time
    _TIMEOUT_AFTER_SEC = 600
    def check_output(*popenargs, **kwargs):
        # We're going to some significant effort here to capture stdout in a file.
        # The reason is that if we just redirect to a pipe, stdout can fill up
        # and cause the called process to stall. On Windows, this happens as soon
        # as stdout contains about 64K of data. By redirecting to a file, the
        # length of stdout for the process essentially becomes unlimited, and we
        # never stall.
        fdesc, fpath = tempfile.mkstemp(prefix='check_output', suffix='.stdout')
        # Convert low-level descriptor to a true file object.
        fstdout = os.fdopen(fdesc)
        kwargs['stdout'] = fstdout
        err = None
        msg = None
        stdout = ''
        try:
            process = subprocess.Popen(*popenargs, **kwargs)
            time_limit = time.time() + _TIMEOUT_AFTER_SEC
            delay = .1
            while True:
                if time.time() > time_limit:
                    msg = 'Pid %d (%s) timed out after %d seconds' % (process.pid, str(*popenargs), _TIMEOUT_AFTER_SEC)
                    err = -1
                    break
                time.sleep(delay)
                err = process.poll()
                if err is not None:
                    break
                if (delay < 1):
                    delay += .1
        finally:
            fstdout.seek(0, 0)
            stdout = fstdout.read()
            fstdout.close()
            for i in range(3):
                try:
                    os.remove(fpath)
                    break
                except:
                    if i < 2:
                        time.sleep(.25)
        if err:
            if not msg:
                msg = 'Process returned %s' % str(err)
            msg += '; stdout contained:\n%s' % stdout
            raise Exception(msg)
        return stdout
    subprocess.check_output = check_output
