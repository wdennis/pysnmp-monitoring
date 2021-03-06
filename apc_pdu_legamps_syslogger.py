#!/usr/bin/env python

__author__ = 'Will Dennis'
__email__ = 'wdennis@nec-labs.com'
__version__ = '1.2.1'

import sys
import logging
import socket

from logging.handlers import SysLogHandler
from multiprocessing import Process, Queue, current_process
from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.smi import builder
from device_list_generator import yield_device_list


# site-specific variables
SYSLOGHOST = '192.168.1.147'
MYMIBDIR = '/root'
ROCOMM = 'testapc'
PDUCSV = '/var/opt/pdu-list.csv'
NUM_WORKER_PROCS = 2


# load mibs
CMDGEN = cmdgen.CommandGenerator()
MIBBUILDER = CMDGEN.snmpEngine.msgAndPduDsp.mibInstrumController.mibBuilder
MIBSOURCES = MIBBUILDER.getMibSources() + (
    builder.DirMibSource(MYMIBDIR),
)
MIBBUILDER.setMibSources(*MIBSOURCES)


class ContextFilter(logging.Filter):
    """ Filter to inject contextual data into the log message. """
    hostname = socket.gethostname()

    def filter(self, record):
        record.hostname = ContextFilter.hostname
        return True


# syslog settings
FILTER = ContextFilter()
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)
LOGGER.addFilter(FILTER)
SYSLOG = SysLogHandler(address=(SYSLOGHOST, 514))
FORMATTER = logging.Formatter('%(asctime)s %(hostname)s APC_PDU_LEGAMPS: [%(levelname)s] %(message)s',
                              datefmt='%Y-%m-%dT%H:%M:%S')
SYSLOG.setFormatter(FORMATTER)
LOGGER.addHandler(SYSLOG)


def poll_pdu_and_syslog_result(pdu):
    """
    Poll PDU for amps per leg, and write to syslog
    :param pdu:
    """
    errorIndication, errorStatus, errorIndex, varBindTable = CMDGEN.nextCmd(
        cmdgen.CommunityData(ROCOMM, mpModel=0),  # mpModel=0 == use SNMP v1
        cmdgen.UdpTransportTarget((pdu, 161)),
        cmdgen.MibVariable('PowerNet-MIB', 'rPDULoadStatusLoad'),  # '.1.3.6.1.4.1.318.1.1.12.2.3.1.1.2'
        lookupNames=True, lookupValues=True
    )

    if errorIndication:
        #print(errorIndication)
        return 'Unsuccessful - error was: %s' % errorIndication
    elif errorStatus:
        print('{0:s} at {1:s}'.format(errorStatus.prettyPrint(),
                                      errorIndex and varBindTable[-1][int(errorIndex) - 1] or '?')
        )
        return 'Failed'
    else:
        for varBindTableRow in varBindTable:
            for name, val in varBindTableRow:
                leg = name.prettyPrint().lstrip("PowerNet-MIB::rPDULoadStatusLoad.").strip('"')
                amps = float(val.prettyPrint()) / 10
                logmsg = 'PDU=%s Leg=%s Amps=%s' % (pdu, leg, amps)
                # print(logmsg)
                LOGGER.info(logmsg)
        return 'Successful'


def worker(work_queue, done_queue):
    """
    Worker function for multiprocessing stage
    :param work_queue:
    :param done_queue:
    """
    try:
        for pdu in iter(work_queue.get, 'STOP'):
            status_code = poll_pdu_and_syslog_result(pdu)
            done_queue.put("%s - %s logging was %s." % (current_process().name, pdu, status_code))
    except Exception, e:
        done_queue.put("%s failed on %s with: %s" % (current_process().name, pdu, e.message))
    return True


def main():
    """
    Main entry point of script.
    """
    pdus = yield_device_list(PDUCSV)

    work_queue = Queue()
    done_queue = Queue()
    processes = []

    for this_pdu in pdus:
        work_queue.put(this_pdu)

    for w in xrange(NUM_WORKER_PROCS):
        p = Process(target=worker, args=(work_queue, done_queue))
        p.start()
        processes.append(p)
        work_queue.put('STOP')

    for p in processes:
        p.join()

    done_queue.put('STOP')

    for status in iter(done_queue.get, 'STOP'):
        print status


if __name__ == '__main__':
    sys.exit(main())
