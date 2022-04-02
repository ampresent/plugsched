# Copyright 2019-2022 Alibaba Group Holding Limited.
# SPDX-License-Identifier: GPL-2.0 OR BSD-3-Clause

import time
from os.path import expanduser, join as pjoin, exists
from os import environ, _exit
from sh import sshpass, openssl, ssh_keygen, mkdir
from lib import retry
from typing import List
from runner import Runner
from traceback import format_exc

from alibabacloud_ecs20140526.client import Client as Ecs20140526Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_ecs20140526 import models as ecs_20140526_models
import logging

class Instance:
    @staticmethod
    def copy_credential(host:str, port:str) -> None:
        credential_file = pjoin(expanduser("~"), '.ssh/id_rsa')

        if not exists(credential_file):
            logging.info("Generating credentials and retrying copying")
            ssh_keygen(t='rsa', f=credential_file, q=True, N='')

        logging.info("Copying ssh credentials to the plugsched-test instance")
        retry(sshpass, 30, 'Connection refused',
            '-e', 'ssh-copy-id', host, '-p', port, "-o", "StrictHostKeyChecking=no")

""" This instance type exploits existing machines """
class PhysicalInstance(Instance):
    @staticmethod
    def run_test(test: Runner, host:str, port:str) -> None:
        Instance.copy_credential(host, port)
        logging.info("Running test %s on host %s", test.desc, host)
        test.run_on_instance(host, port)

""" This instance type creates Aliyun ECS automatically """
class AlibabaInstance(Instance):
    def __init__(self):
        pass

    @staticmethod
    def create_client(
        akid: str,
        aksecret: str,
    ) -> Ecs20140526Client:
        config = open_api_models.Config(
            access_key_id=akid,
            access_key_secret=aksecret
        )
        config.endpoint = f'ecs-cn-hangzhou.aliyuncs.com'
        return Ecs20140526Client(config)

    @staticmethod
    def __wait_until_stable(
        client: Ecs20140526Client,
        instance_id: str,
        region_id: str,
        expect: str
    ) -> None:
        describe_instance_status_request = ecs_20140526_models.DescribeInstanceStatusRequest(
            instance_id=[ instance_id ],
            region_id=region_id
        )

        while True:
            response = client.describe_instance_status(describe_instance_status_request)
            status = response.body.instance_statuses.instance_status[0].status
            if status == expect:
                break
            time.sleep(5)

    @staticmethod
    def create_instance(
        client: Ecs20140526Client,
        profile: dict,
    ) -> str:
        describe_images_request = ecs_20140526_models.DescribeImagesRequest(
            region_id=profile['ecs']['region_id'],
            status='Available',
            image_owner_alias='system',
            instance_type=profile['ecs']['instance_type'],
            ostype='linux',
            image_name=profile['image']
        )
        image_id = client.describe_images(describe_images_request).body.images.image[0].image_id
        logging.info("Choosing image %s", image_id)

        #describe_vpcs_request = ecs_20140526_models.DescribeVpcsRequest(
        #    region_id=profile['ecs']['region_id'], page_number=1, page_size=1
        #)
        #result = client.describe_vpcs(describe_vpcs_request)
        #v_switch_id = result.body.vpcs.vpc[0].v_switch_ids.v_switch_id[0]
        #vpc_id = result.body.vpcs.vpc[0].vpc_id
        #logging.info("Choosing vswitch %s/%s", vpc_id, v_switch_id)
        vpc_id = profile['vpc']
        v_switch_id = profile['vswitch']

        describe_security_groups_request = ecs_20140526_models.DescribeSecurityGroupsRequest(
            region_id=profile['ecs']['region_id'], vpc_id=vpc_id, page_number=1, page_size=1
        )
        security_group_id = client.describe_security_groups(describe_security_groups_request).body.security_groups.security_group[0].security_group_id
        logging.info("Choosing security_group %s", security_group_id)

        passwd = 'Pw$' + openssl('rand', '-hex', 12).strip()
        environ['SSHPASS'] = passwd
        system_disk = ecs_20140526_models.CreateInstanceRequestSystemDisk(
            **profile["disk"]
        )
        create_instance_request = ecs_20140526_models.CreateInstanceRequest(
            zone_id='cn-beijing-k', **profile["ecs"], system_disk=system_disk, image_id=image_id, v_switch_id=v_switch_id, password=passwd
        )
        logging.info("Creating plugsched-test instance")
        instance_id = client.create_instance(create_instance_request).body.instance_id
        logging.info("Created plugsched-test instance %s", instance_id)
        return instance_id

    @staticmethod
    def start_instance(
        client: Ecs20140526Client,
        instance_id: str,
        region_id: str
    ) -> str:
        logging.info("Waiting plugsched-test instance to be created")
        AlibabaInstance.__wait_until_stable(client, instance_id, region_id, 'Stopped')

        start_instance_request = ecs_20140526_models.StartInstanceRequest(
            instance_id=instance_id
        )
        logging.info("Starting plugsched-test instance")
        client.start_instance(start_instance_request)

        logging.info("Waiting plugsched-test instance to be started")
        AlibabaInstance.__wait_until_stable(client, instance_id, region_id, 'Running')

        logging.info("Allocating plugsched-test instance with public ip address")
        allocate_public_ip_address_request = ecs_20140526_models.AllocatePublicIpAddressRequest(
            instance_id=instance_id
        )
        ip = client.allocate_public_ip_address(allocate_public_ip_address_request).body.ip_address
        host = 'root@%s' % ip

        Instance.copy_credential(host, '22')
        return host

    @staticmethod
    def run_test(
        akid: str,
        aksecret: str,
        profile: dict,
        test: Runner
    ) -> None:
        client = AlibabaInstance.create_client(akid, aksecret)
        status = 'pending'

        try:
            if status == 'pending':
                instance_id = AlibabaInstance.create_instance(client, profile)
                status = 'created'
        except Exception as e:
            logging.error("Failed to create a plugsched-test instance.")
            logging.error(format_exc())

        try:
            if status == 'created':
                ip = AlibabaInstance.start_instance(client, instance_id, profile['ecs']['region_id'])
                status = 'started'
        except Exception as e:
            logging.error("Failed to start the plugsched-test instance")
            logging.error(format_exc())

        try:
            if status == 'started':
                logging.info("Running test %s on %s", test.desc, ip)
                test.run_on_instance(ip, 22)
                status = 'finished'
        except Exception as e:
            logging.error("Failed to run test %s on %s", test.desc, ip)
            if hasattr(e, 'stderr'):
                logging.error(e.stderr)
            else:
                logging.error(format_exc())

        try:
            if status in ['started', 'created', 'finished']:
                AlibabaInstance.delete_instance(client, instance_id)
        except Exception as e:
            logging.error("Failed to delete the plugsched-test instance")
            logging.error(format_exc())

        if status != 'finished':
            _exit(1)

    @staticmethod
    def delete_instance(
        client: Ecs20140526Client,
        instance_id: str
    ) -> None:
        delete_instance_request = ecs_20140526_models.DeleteInstanceRequest(
            instance_id=instance_id,
            force=True
        )

        logging.info("Deleting plugsched-test instance")
        retry(client.delete_instance, 30,
            'The specified instance status does not support this operation.',
            delete_instance_request
        )
