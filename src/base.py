import os
import ConfigParser
import logging


class Base:
    def __init__(self):
        # script dir
        self.current_dir = os.path.dirname(os.path.abspath(__file__))

        # environment
        self.init = self.current_dir + '/../conf/python/aws.conf'
        self.section = 'environment'
        self.default = 'default'
        self.general = 'general'
        self.box = 'box'
        self.config = ConfigParser.ConfigParser()
        self.config.read(self.init)
        self.log = None
        self.temp = self.config.get(self.general, 'temp_dir')

    def config_logger(self, name):
        # setup logger
        self.log = logging.getLogger(name)
        self.log.setLevel(logging.INFO)
        fh = logging.FileHandler(self.config.get(self.section, 'log_file'))
        ch = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s', '%Y-%m-%d %H:%M:%S')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        self.log.addHandler(ch)
        self.log.addHandler(fh)
        self.log.info("Logger " + name + " ready!")