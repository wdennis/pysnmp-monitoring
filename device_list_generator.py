#!/usr/bin/env python

__author__ = 'Will Dennis'
__email__ = 'wdennis@nec-labs.com'

import pandas

def yield_device_list(csvfile):
    """
    Takes 'Hostname' column entries from CSV file, and returns a list of device hostnames
    (Obviously, the CSV file must have a column with the first row entry being 'Hostname')

    :param csvfile:
    :return:
    """
    dl = pandas.read_csv(csvfile)
    return dl.Hostname.tolist()

if __name__ == '__main__':
    pass