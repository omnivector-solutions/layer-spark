from subprocess import check_call

from charms.reactive import (
    hook,
    when,
    when_not,
    set_flag,
    is_flag_set,
)

from charmhelpers.core import unitdata
from charmhelpers.core.host import (
    add_user_to_group,
    service_start,
    service_stop,
    service_running,
)
from charmhelpers.core.hookenv import (
    application_version_set,
    config,
    log,
    network_get,
    open_port,
)
from charmhelpers.core.templating import render
from charms.layer import status

import charms.leadership

from charms.layer.hadoop_base import (
    provision_hadoop_resource,
)
from charms.layer.spark_base import (
    get_spark_version,
    provision_spark_resource,
)

from charms.layer.spark import (
    render_spark_env_and_defaults,
)


CONFIG = config()
KV = unitdata.kv()
MASTER = 'master'
WORKER = 'worker'


@when_not('spark.bind.address.available')
def bind_address_available():
    """Get the correct ip address for spark to bind.
    """
    ip = network_get('spark')['ingress-addresses'][0]
    KV.set('bind_address', ip)
    set_flag('spark.bind.address.available')


@when_not('spark.node.type.available')
def determine_spark_node_type():
    """Determine what node type we are.
    """
    node_type = ""
    if is_flag_set('leadership.is_leader'):
        node_type = MASTER
    else:
        node_type = WORKER
    KV.set('node_type', node_type)
    set_flag('spark.node.type.{}'.format(node_type))
    set_flag('spark.node.type.available')


@when('leadership.is_leader',
      'spark.node.type.available',
      'spark.node.type.master',
      'spark.bind.address.available')
@when_not('leadership.set.master_uri')
def get_set_master_ip():
    """Get/set the master_uri
    """
    ip = KV.get('bind_address')
    charms.leadership.leader_set(master_uri="spark://{}:7077".format(ip))
    charms.leadership.leader_set(master_ip=ip)


@when('leadership.set.master_uri',
      'spark.bind.address.available',
      'spark.base.available')
@when_not('spark.config.available')
def spark_config_available():
    """Render the spark-env.sh and spark-defaults.conf.
    """
    ctxt = {'bind_address': KV.get('bind_address'),
            'master_ip': _leader_get('master_ip'),
            'master_uri': _leader_get('master_uri')}
    render_spark_env_and_defaults(ctxt)
    set_flag('spark.config.available')


@when('leadership.set.master_uri',
      'spark.bind.address.available')
@when_not('spark.systemd.available')
def install_spark_systemd():
    """Install spark systemd services.
    """

    ctxt = {'bind_address': KV.get('bind_address'),
            'master_uri': _leader_get('master_uri')}

    # Provision the systemd services
    if KV.get('node_type') == MASTER:
        # spark-master
        render('spark-master.service',
               '/etc/systemd/system/spark-master.service',
               context=ctxt)
        check_call(['systemctl', 'enable', 'spark-master'])
        # spark-worker
        render('spark-worker.service',
               '/etc/systemd/system/spark-worker.service',
               context=ctxt)
        check_call(['systemctl', 'enable', 'spark-worker'])
        # spark-history-server
        render('spark-history-server.service',
               '/etc/systemd/system/spark-history-server.service',
               context=ctxt)
        check_call(['systemctl', 'enable', 'spark-history-server'])

    else:
        # spark-worker
        render('spark-worker.service',
               '/etc/systemd/system/spark-worker.service',
               context=ctxt)
        check_call(['systemctl', 'enable', 'spark-worker'])

    set_flag('spark.systemd.available')


@when('hadoop.base.available',
      'spark.config.available',
      'spark.systemd.available',
      'leadership.set.master_uri',
      'spark.node.type.available',
      'spark.bind.address.available')
@when_not('spark.init.complete')
def set_spark_init():
    add_user_to_group('spark', 'hadoop')
    set_flag('spark.init.complete')


# @when('spark.node.type.master',
#      'leadership.set.master_uri',
#      'endpoint.spark.joined')
# @when_not('spark.worker.relation.data.sent')
# def send_worker_relation_data():
#    endpoint = endpoint_from_flag('endpoint.spark.joined')
#    ip = charms.leadership.leader_get(master_uri)
#    endpoint.configure(ip)
#    set_flag('spark.worker.relation.data.sent')


@when('spark.init.complete')
@when_not('spark.version.available')
def set_spark_version():
    application_version_set(get_spark_version())
    set_flag('spark.version.available')


@when('spark.init.complete')
@when_not('spark.init.started')
def start_spark_systemd():
    start_spark()
    set_flag('spark.init.started')


@hook('upgrade-charm')
def reprovision_all_the_things():
    """Stop the appropriate services, reprovision all the things,
    start the services back up.
    """
    if is_flag_set('spark.init.installed'):

        # Stop the things
        if is_flag_set('spark.node.type.master'):
            if service_running('spark-master'):
                service_stop('spark-master')
            if service_running('spark-history-server'):
                service_stop('spark-history-server')
            if service_running('spark-worker'):
                service_stop('spark-worker')
        else:
            if service_running('spark-worker'):
                service_stop('spark-worker')

        # Reprovision/reinstall
        hadoop_resource_provisioned = provision_hadoop_resource()

        if not hadoop_resource_provisioned:
            status.blocked("TROUBLE UNPACKING HADOOP RESOURCE, PLEASE DEBUG")
            log("TROUBLE PROVISIONING HADOOP RESOURCE, PLEASE DEBUG")
            return

        spark_resource_provisioned = provision_spark_resource()

        if not spark_resource_provisioned:
            status.blocked("TROUBLE UNPACKING SPARK RESOURCE, PLEASE DEBUG")
            log("TROUBLE PROVISIONING SPARK RESOURCE, PLEASE DEBUG")
            return

        render_spark_env_and_defaults()

        # Start the appropriate services back up
        if is_flag_set('spark.node.type.master'):
            if not service_running('spark-master'):
                service_start('spark-master')
            if not service_running('spark-history-server'):
                service_start('spark-history-server')
            if not service_running('spark-worker'):
                service_start('spark-worker')
        else:
            if not service_running('spark-worker'):
                service_start('spark-worker')


#
# Utility functions
#


def start_spark():

    """
    Always start the Spark History Server. Start other
    servers and open related ports as appropriate.
    """
    spark_apps = []
    if KV.get('node_type') == MASTER:
        if service_start('spark-master'):
            open_port(7077)
            open_port(8080)
            log('Master service started')
            spark_apps.append('master')
        else:
            log('Spark master not starting', level='WARN')
            status.blocked("'master' serbvice not starting")
            return

        if service_start('spark-worker'):
            open_port(7078)
            open_port(8081)
            log("'spark-worker' service started")
            spark_apps.append('worker')
        else:
            log('Worker did not start', level='WARN')
            status.blocked("'spark-worker' not starting")
            return

        if service_start('spark-history-server'):
            open_port(18080)
            log('Spark history server started')
            spark_apps.append('history')
        else:
            log('Spark history server not starting', level='WARN')
            status.blocked("'spark-history-server' not starting")
            return
        status.active("Running: {}".format(",".join(spark_apps)))
    elif KV.get('node_type') == WORKER:

        if service_start('spark-worker'):
            open_port(7078)
            open_port(8081)
            log("'spark-worker' service started")
            spark_apps.append('worker')
        else:
            log('Worker did not start', level='WARN')
            status.blocked("'spark-worker' not starting")
            return
        status.active("Services: {}".format(",".join(spark_apps)))
    else:
        log('Incorrect node type, spark not starting', level='WARN')
        status.blocked("Incorrect node-type config, not starting")
        return


def _leader_get(key):
    """Wrapper to get value from leader
    """
    return charms.leadership.leader_get(key)
