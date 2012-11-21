'''
TaskQueue

Tasks are subprocesses which are run asynchronously from the client's persepective.

Does all its work during calls to methods. (No threads).
'''
import subprocess
import logging
import time

class TaskQueue:
    def __init__(self, max_processes):
        self.max_processes = max_processes
        self._waiting = []
        self._running = []
        self._finished = []

    def add(self, name, cmd, priority=1, caller_data=None):
        ''' add a new cmd to the queue  - don't add duplicates'''
        if not name in self.waiting(update=False) + self.running(update=False):
            logging.debug('adding task %s' % name)
            self._waiting.append(TaskInfo(name, cmd, priority, caller_data))
        self._update()

    def pending(self):
        ''' return the number items that are still waiting or running '''
        self._update()
        return len(self._waiting) + len(self._running)

    def waiting(self, update=True):
        ''' return the names of all tasks waiting to run'''
        if update:
            self._update()
        return [i.name for i in self._waiting]

    def running(self, update=True):
        ''' return the names of all the tasks currently running'''
        if update:
            self._update()
        return [i.name for i in self._running]
    
    def finished(self):
        ''' return the TaskInfo for finished tasks
        '''
        self._update()
        tmp = self._finished
        self._finished = []
        return tmp

    def show_status(self):
        s = 'Pending Tasks: %d' % self.pending()
        s += '\nTasks In Progress:'
        for task in self._running:
            s += "\n\trun=%.0f %s" % (time.time() - task.creationtime - task.timespentwaiting, task.name)
        s +=  '\nTasks Finished:'
        for task in self._finished:
            s += "\n\t%s wait=%.0f run=%.0f %s" % (('Succeeded' if task.returncode == 0 else "Failed"),
                                task.timespentwaiting, task.timespentrunning, task.name)
        logging.info(s)

    def _update(self):
        # process completed commands
        tmprunning = self._running[:]
        for task in tmprunning:
            if task.process.poll() is not None:
                self._running.remove(task)
                task.stdout,task.stderr = task.process.communicate()
                task.returncode = task.process.returncode
                t = time.time()
                task.timespentrunning = t - task.creationtime - task.timespentwaiting
                task.process = None
                self._finished.append(task)

        # run waiting items 
        delayed = 0
        # run items in priority order and in with the longest waiting time first
        self._waiting.sort(key=lambda task: task.timespentwaiting, reverse=True)
        self._waiting.sort(key=lambda task: task.priority)
        while delayed < len(self._waiting) and len(self._running) < self.max_processes:
            task = self._waiting.pop(0)
            if task.name in self.running(update=False):
                self._waiting.append(task)
                delayed += 1
            else:
                logging.debug('starting %s' % task.command)
                task.timespentwaiting = time.time() - task.creationtime
                task.process = subprocess.Popen(task.command, stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE, shell=True)
                self._running.append(task)
        for task in self._waiting:
            task.timespentwaiting = time.time() - task.creationtime


class TaskInfo:
    def __init__(self, name, command, priority, data):
        self.name = name
        self.priority = priority
        self.command = command
        self.data = data
        self.returncode = None
        self.stdout = None
        self.stderr = None
        self.creationtime = time.time()
        self.timespentwaiting = 0
        self.timespentrunning = 0
        self.process = None
        
##quick test
##q = TaskQueue(5)
##q.add('x', 'notepad \\tmp\\x.txt', None)
##q.add('y', 'notepad \\tmp\\y.txt', None)
##q.add('z', 'notepad \\tmp\\z.txt', None)
##q.add('w', 'notepad \\tmp\\w.txt', None)
##q.add('good', 'echo hi there', None)
##q.add('bad', 'fred', None)
##
##
##
##while (q.pending()):
##    print 'waiting for', q.pending()
##    import time
##    time.sleep(5)
##
##for i in q.finished():
##    print 'finished', i.name

