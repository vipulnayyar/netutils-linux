from re import match
from os import listdir
from copy import deepcopy
from random import randint
from optparse import Option
from collections import namedtuple
from netutils_linux_monitoring.base_top import BaseTop

Stat = namedtuple('Stat', ['filename', 'shortname'])


class LinkRateTop(BaseTop):
    """ Utility for monitoring network devices' pps and error rate """
    stats = [
        Stat('rx_packets', 'packets'),
        Stat('rx_bytes', 'bytes'),
        Stat('rx_errors', 'errors'),
        Stat('rx_dropped', 'dropped'),
        Stat('rx_missed_errors', 'missed'),
        Stat('rx_fifo_errors', 'fifo'),
        Stat('rx_length_errors', 'length'),
        Stat('rx_over_errors', 'overrun'),
        Stat('rx_crc_errors', 'crc'),
        Stat('rx_frame_errors', 'frame'),
        Stat('tx_packets', 'packets'),
        Stat('tx_bytes', 'bytes'),
        Stat('tx_errors', 'errors')
    ]

    def __init__(self):
        BaseTop.__init__(self)
        specific_options = [
            Option('--assert', '--assert-mode', default=False, dest='assert_mode',
                   help='Stops running after errors detected.'),
            Option('--dev', '--devices', default="", dest='devices',
                   help='Comma-separated list of devices to monitor.'),
            Option('--device-regex', default='^.*$',
                   help="Regex-mask for devices to monitor."),
            Option('-s', '--simple', default=False, dest='simple_mode', action='store_true',
                   help='Hides different kinds of error, showing only general counters.'),
            Option('--rx', '--rx-only', dest='rx_only', default=False, action='store_true',
                   help='Hides tx-counters'),
            Option('--bits', default=False, action='store_true'),
            Option('--bytes', default=False, action='store_true'),
            Option('--kbits', default=False, action='store_true'),
            Option('--mbits', default=True, action='store_true'),
        ]
        self.specific_options.extend(specific_options)

    def make_header(self, network_top=False):
        """ generate `table's` header regarding to output options """
        rx_count = 3 if self.options.simple_mode else 10
        tx_count = 0 if self.options.rx_only else 3
        header_columns = [""] + ["RX"] * rx_count + ["TX"] * tx_count
        ncolumns = [self.__indent__(column, value) for column, value in enumerate(header_columns)]
        nstats = list(enumerate([Stat("", "")] + self.stats))
        stats = [self.__indent__(column, stat.shortname) for column, stat in nstats]
        stats_header1 = " ".join(ncolumns)
        stats_header2 = " ".join(stats)
        if network_top:
            return "\n".join([stats_header1, stats_header2])
        return "\n".join([self.header, stats_header1, stats_header2])

    def parse(self):
        return dict((dev, self.__parse_dev__(dev)) for dev in self.options.devices)

    def eval(self):
        self.diff = deepcopy(self.current)
        for dev, data in self.current.iteritems():
            for stat in self.stats:
                if self.options.random:
                    self.diff[dev][stat] = randint(0, 10000)
                else:
                    self.diff[dev][stat] = data[stat] - \
                        self.previous[dev][stat]

    def __repr__(self):
        output = [self.header]
        for dev in self.options.devices:
            output.append("{0:<14} {1}".format(dev, self.__repr_dev__(dev)))
        return "\n".join(output)

    def __repr_dev__(self, dev):
        repr_source = self.current if not self.options.delta_mode else self.diff
        data = [self.__indent__(n, self.spaces(repr_source[dev][stat]), -1)
                for n, stat in enumerate(self.stats)]
        return " ".join(data)

    def __parse_dev__(self, dev):
        return dict((stat, self.__parse_dev_stat__(dev, stat)) for stat in self.stats)

    def __parse_dev_stat__(self, dev, stat):
        if self.options.random:
            return randint(1, 10000)
        with open('/sys/class/net/{0}/statistics/{1}'.format(dev, stat.filename)) as devfile:
            file_value = int(devfile.read().strip())
            if 'bytes' in stat.filename:
                return self.__repr_bytes(file_value)
            return file_value

    def __repr_bytes(self, value):
        if self.options.bytes:
            return value
        if self.options.bits:
            return value * 8
        elif self.options.kbits:
            return value * 8 / 1024
        return value * 8 / 1024 / 1024

    @staticmethod
    def __indent__(column, value, maxvalue=0):
        """ May be used for special indent for first column """
        return "{0:<14}".format(value) if column == maxvalue else "{0:>11}".format(value)

    def devices_list_regex(self):
        """ Returns list of network devices matching --device-regex """
        net_dev_list = listdir('/sys/class/net/')
        return [dev for dev in net_dev_list if match(self.options.device_regex, dev)]

    def devices_list(self):
        """ Return list of network devices regarding --devices / --device-regex """
        if self.options.devices:
            return self.options.devices.split(',')
        return self.devices_list_regex()

    def post_optparse(self):
        """ Asserting and applying parsing options """
        self.options.devices = self.devices_list()
        if not self.options.devices:
            raise ValueError("No devices've been specified")
        if self.options.rx_only:
            self.stats = [
                stat for stat in self.stats if stat.filename.startswith('rx')]
        if self.options.simple_mode:
            simple_stats = ('packets', 'bytes', 'errors')
            self.stats = [
                stat for stat in self.stats if stat.shortname in simple_stats]
        if any([self.options.bits, self.options.kbits, self.options.mbits]):
            for i, stat in enumerate(self.stats):
                if stat.shortname == 'bytes':
                    if self.options.bits:
                        self.stats[i] = Stat(stat.filename, 'bits')
                    elif self.options.kbits:
                        self.stats[i] = Stat(stat.filename, 'kbits')
                    elif self.options.mbits:
                        self.stats[i] = Stat(stat.filename, 'mbits')
        self.header = self.make_header()


if __name__ == '__main__':
    print LinkRateTop().run()