""" compu_main.py
 Main automated process
"""
__author__ = 'Marco Albero'
import fabfile
from fabric.api import execute
from ec2 import Ec2
from fabric.api import env
from base import Base


class CompuMain(Base):
    def __init__(self):
        Base.__init__(self)
        self.config_logger(__name__)
        self.ec2 = Ec2()

    def start(self):
        env.hosts = [self.ec2.create_ec2_instance()]
        self.log.info("Starting deployments ...")
        execute(getattr(fabfile, 'deploy'))
        self.log.info("Deployments done!")


if __name__ == "__main__":
    c = CompuMain()
    c.start()