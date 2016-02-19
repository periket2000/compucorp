""" ec2_test.py
 Process director
"""
__author__ = 'Marco Albero'
import boto.ec2
import boto.vpc
import time
from base import Base
import os
import uuid
import shutil


class Ec2(Base):
    def __init__(self):
        Base.__init__(self)
        self.config_logger(__name__)
        self.host = None

    def create_ec2_instance(self):
        # connect to ec2
        self.log.info("Connecting to ec2 ...")
        ec2 = boto.ec2.connect_to_region(
            self.config.get(self.section, 'region'),
            aws_access_key_id=self.config.get(self.default, 'aws_access_key_id'),
            aws_secret_access_key=self.config.get(self.default, 'aws_secret_access_key')
        )

        vpc_conn = boto.vpc.connect_to_region(
            self.config.get(self.section, 'region'),
            aws_access_key_id=self.config.get(self.default, 'aws_access_key_id'),
            aws_secret_access_key=self.config.get(self.default, 'aws_secret_access_key')
        )

        self.log.info("Ec2 connection success!")
        compu_key = str(uuid.uuid4())
        key = ec2.create_key_pair(compu_key)
        key.save(self.temp)
        os.rename(self.temp + '/' + compu_key + '.pem', self.config.get(self.general, 'ssh_pubkey_path'))
        keys = ec2.get_all_key_pairs()
        for key in keys:
            self.log.info("Key found: " + key.name)

        self.log.info("Starting instance ...")

        # Create a VPC
        vpc = vpc_conn.create_vpc('10.0.0.0/16')

        # Configure the VPC to support DNS resolution and hostname assignment
        vpc_conn.modify_vpc_attribute(vpc.id, enable_dns_support=True)
        vpc_conn.modify_vpc_attribute(vpc.id, enable_dns_hostnames=True)

        # Create an Internet Gateway
        gateway = vpc_conn.create_internet_gateway()

        # Attach the Internet Gateway to our VPC
        vpc_conn.attach_internet_gateway(gateway.id, vpc.id)

        # Create a Route Table
        route_table = vpc_conn.create_route_table(vpc.id)

        # Create a size /16 subnet
        subnet = vpc_conn.create_subnet(vpc.id, '10.0.0.0/24')

        # Associate Route Table with our subnet
        vpc_conn.associate_route_table(route_table.id, subnet.id)

        # Create a Route from our Internet Gateway to the internet
        vpc_conn.create_route(route_table.id, '0.0.0.0/0', gateway.id)

        # Create a new VPC security group
        sg = vpc_conn.create_security_group('compu_group',
                                            'A group for compucorp',
                                            vpc.id)

        # Authorize access to port 22 from anywhere
        sg.authorize(ip_protocol='tcp', from_port=22, to_port=22, cidr_ip='0.0.0.0/0')
        sg.authorize(ip_protocol='tcp', from_port=443, to_port=443, cidr_ip='0.0.0.0/0')

        # Run an instance in our new VPC
        reservation = vpc_conn.run_instances(self.config.get(self.section, 'ami_id'), key_name=compu_key,
                                             security_group_ids=[sg.id],
                                             instance_type=self.config.get(self.section, 'instance_type'),
                                             subnet_id=subnet.id)

        instance = reservation.instances[0]

        # Wait for the instance to be running and have an public DNS name
        while instance.state != 'running':
            self.log.info("Instance state: %s" % instance.state)
            time.sleep(10)
            instance.update()

        # Now create an Elastic IP address for the instance
        # And associate the EIP with our instance
        eip = vpc_conn.allocate_address(domain='vpc')
        eip.associate(instance_id=instance.id)

        # tag machine
        ec2.create_tags([instance.id, vpc.id], {"Name": "deployment_"+eip.public_ip})

        # Copy key as new name
        shutil.copy(self.config.get(self.general, 'ssh_pubkey_path'), self.temp + '/' + eip.public_ip + '.pem')

        self.log.info("Instance state: %s" % instance.state)
        self.log.info("Public IP: %s" % eip.public_ip)
        self.log.info("Waiting for SSH service to be available")
        self.wait_for_ssh(self.config.get(self.general, 'ssh_pubkey_path'),
                          self.config.get(self.box, 'username'),
                          eip.public_ip)

        return eip.public_ip

    def wait_for_ssh(self, pubkey, user, host):
        while True:
            time.sleep(5)
            try:
                code = os.system('ssh -oStrictHostKeyChecking=no -i ' + pubkey + ' ' + user + '@' + host + ' exit')
                if code == 0:
                    self.log.info("SSH available")
                    return
                else:
                    raise Exception("SSH not available")
            except Exception, e:
                self.log.info(e.message)
                pass
