import os
import time

import buildinfo
import build_id
import dateutils
import sandboxtype

RESULTS_FILE = 'results.txt'
MAX_RETAINED_SECONDS = 86400 * 14

def enum_to_str(cls, num):
    for key, val in cls.__dict__.iteritems():
        if num == val:
            return key

def str_to_enum(cls, val):
    if val[0].isdigit():
        return int(val)
    return cls.__dict__[val.upper()]

class EvalResult:
    OK = 0
    PROBLEMATIC = 1
    FAILED = 2
    UNKNOWN = 3

class EvalPhase:
    UPDATE = 0
    BUILD = 1
    TEST = 2
    PUBLISH = 3

def parse_eval_summary_line(line):
    '''
    Convert a line of text into an EvalResult. Raise exception on bad format.
    '''
    fields = [x.strip() for x in line.split(',')]
    fields[-6] = dateutils.parse_standard_date_with_tz_offset(fields[-6])
    fields[-5] = [float(val) for val in fields[-5].split(' ')]
    try:
        return EvalSummary(*fields)
    except:
        import traceback
        traceback.print_exc()

def _time_as_serializable_str(secs):
    if secs:
        return '%0.2f' % secs
    return ''

class EvalSummary:
    '''
    Summarize what happened when a sandbox was evaluated.
    '''
    def __init__(self, bid, style, host, final_phase, failure_reason, start_time, durations, tpv, os, bitness, version):
        try:
            assert(bid)
            assert(host)
            assert(tpv)
            assert(os)
            assert(bitness)
            assert(version)
            assert(final_phase is not None)
            style = style.upper()
            if not isinstance(final_phase, int):
                final_phase = str_to_enum(EvalPhase, final_phase)
            ts = durations[0]
            assert(isinstance(ts, float) or isinstance(ts, int))
            assert(len(durations) == final_phase + 1)
            # For string data types, convert to the named tuple.
            if hasattr(bid, 'lower'):
                #print('build_id was a str')
                bid = build_id.build_id_from_str(bid)

            else:
                #print('build_id was a named tuple')
                assert(isinstance(bid, build_id.BuildID))
            self.build_id = bid
            self.style = style
            self.host = host
            self.final_phase = final_phase
            self.failure_reason = failure_reason
            self.start_time = start_time
            self.durations = durations
            self.tpv = tpv
            self.os = os
            self.bitness = bitness
            self.version = version
        except AssertionError:
            import traceback
            traceback.print_exc()
            # Make the error a bit more useful by echoing what we received.
            raise Exception('Bad EvalSummary: "%s"' % (
                '%s.%s.%s.%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s' % (
                    build_id.component,
                    build_id.branch,
                    build_id.code_revno,
                    build_id.test_revno,
                    style,
                    host,
                    final_phase,
                    failure_reason,
                    start_time,
                    str(durations),
                    tpv,
                    os,
                    bitness,
                    version
            )))
    def __str__(self):
        fr = self.failure_reason
        if not fr:
            fr = ''
        return '%s.%s.%s.%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s' % (
            self.build_id.component,
            self.build_id.branch,
            self.build_id.code_revno,
            self.build_id.test_revno,
            self.style,
            self.host,
            enum_to_str(EvalPhase, self.final_phase),
            fr,
            dateutils.format_standard_date_with_tz_offset(self.start_time),
            ' '.join([str(round(x, 2)) for x in self.durations]),
            self.tpv,
            self.os,
            self.bitness,
            self.version
        )
    def get_reported_result(self):
        '''
        Return the result that was reported for this eval. This value is not
        used directly to compute dashboard status; see get_imputed_result() for
        that.
        '''
        if self.failure_reason:
            return EvalResult.FAILED
        return EvalResult.OK
    def get_imputed_result(self):
        '''
        Return the result that this eval should contribute to the dashboard
        status. Official and continuous builds contribute their status directly,
        but experimental evals are only suggestive rather than definitive, so
        a failed experimental eval contributes a problematic status.
        '''
        if not self.failure_reason:
            return EvalResult.OK
        if sandboxtype.SandboxType(None, variant=self.style).get_failed_build_is_failed_report():
            return EvalResult.FAILED
        return EvalResult.PROBLEMATIC
    def get_start_time(self):
        return self.start_time
    def get_end_time(self):
        return self.start_time + self.get_elapsed_seconds()
    def get_elapsed_seconds(self, phase=None):
        if phase is None:
            n = 0
            for m in self.durations:
                n += m
            return n
        if not isinstance(phase, int):
            phase = str_to_enum(EvalPhase, phase)
        return self.durations[phase]
