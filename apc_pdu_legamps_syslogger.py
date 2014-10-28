#!/usr/bin/env python

__author__ = 'Will Dennis'
__email__ = 'wdennis@nec-labs.com'
__version__ = '1.0.0'

import sys
import logging
from logging.handlers import SysLogHandler
import socket

from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.smi import builder


# site-specific variables
SYSLOGHOST = '192.168.1.147'
MYMIBDIR = '/root'
ROCOMM = 'testapc'


# load mibs
CMDGEN = cmdgen.CommandGenerator()
MIBBUILDER = CMDGEN.snmpEngine.msgAndPduDsp.mibInstrumController.mibBuilder
MIBSOURCES = MIBBUILDER.getMibSources() + (
    builder.DirMibSource(MYMIBDIR),
)
MIBBUILDER.setMibSources(*MIBSOURCES)


def get_target_list():
    """
    Build list of PDUs to query
    TODO: Come up with way to get list from external source...
    Maybe from DNS?
    """
    all_pdus = ['testpdu1', 'testpdu2']  # for testing
    return all_pdus


class ContextFilter(logging.Filter):
    """ Filter to inject contextual data into the log message."""
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
        cmdgen.CommunityData(ROCOMM),
        cmdgen.UdpTransportTarget((pdu, 161)),
        cmdgen.MibVariable('PowerNet-MIB', 'rPDULoadStatusLoad'),  # '.1.3.6.1.4.1.318.1.1.12.2.3.1.1.2'
        lookupNames=True, lookupValues=True
    )

    if errorIndication:
        print(errorIndication)
    elif errorStatus:
        print('{0:s} at {1:s}'.format(errorStatus.prettyPrint(),
                                      errorIndex and varBindTable[-1][int(errorIndex) - 1] or '?')
             )
    else:
        for varBindTableRow in varBindTable:
            for name, val in varBindTableRow:
                leg = name.prettyPrint().lstrip("PowerNet-MIB::rPDULoadStatusLoad.").strip('"')
                amps = float(val.prettyPrint()) / 10
                logmsg = 'PDU=%s Leg=%s Amps=%s' % (pdu, leg, amps)
                print(logmsg)
                LOGGER.info(logmsg)


def main():
    """
    Main entry point of script.
    """
    pdus = get_target_list()
    for this_pdu in pdus:
        poll_pdu_and_syslog_result(this_pdu)


if __name__ == '__main__':
    sys.exit(main())
