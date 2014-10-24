#!/usr/bin/env python

__author__ = 'Will Dennis'
__email__ = 'wdennis@nec-labs.com'

import logging
from logging.handlers import SysLogHandler
import socket

from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.smi import builder


# load mibs
MYMIBDIR = '/root'
cmdGen = cmdgen.CommandGenerator()
mibBuilder = cmdGen.snmpEngine.msgAndPduDsp.mibInstrumController.mibBuilder
mibSources = mibBuilder.getMibSources() + (
    builder.DirMibSource(MYMIBDIR),
)
mibBuilder.setMibSources(*mibSources)

TARGET = '192.168.1.107'
errorIndication, errorStatus, errorIndex, \
varBindTable = cmdGen.nextCmd(
    cmdgen.CommunityData('testapc'),
    cmdgen.UdpTransportTarget(( TARGET, 161 )),
    cmdgen.MibVariable('PowerNet-MIB', 'rPDULoadStatusLoad'),  # '.1.3.6.1.4.1.318.1.1.12.2.3.1.1.2'
    lookupNames=True, lookupValues=True
)


class ContextFilter(logging.Filter):
    hostname = socket.gethostname()

    def filter(self, record):
        record.hostname = ContextFilter.hostname
        return True


f = ContextFilter()

SYSLOGHOST = '192.168.1.147'
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addFilter(f)
syslog = SysLogHandler(address=(SYSLOGHOST, 514))
formatter = logging.Formatter('%(asctime)s %(hostname)s APC_PDU_LEGAMPS: [%(levelname)s] %(message)s', datefmt='%Y-%m-%dT%H:%M:%S')

syslog.setFormatter(formatter)
logger.addHandler(syslog)

#logger.info("TEST message")

if errorIndication:
    print(errorIndication)
else:
    if errorStatus:
        print('%s at %s' % (
            errorStatus.prettyPrint(),
            errorIndex and varBindTable[-1][int(errorIndex) - 1] or '?'
            )
        )
    else:
        for varBindTableRow in varBindTable:
            for name, val in varBindTableRow:
                #print('%s = %s' % (name.prettyPrint(), val.prettyPrint()))
                leg = name.prettyPrint().lstrip("PowerNet-MIB::rPDULoadStatusLoad.").strip('"')
                amps = float(val.prettyPrint()) / 10
                logmsg = 'PDU=%s Leg=%s Amps=%s' % (TARGET, leg, amps)
                print(logmsg)
                logger.info(logmsg)