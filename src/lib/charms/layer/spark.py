import os
from subprocess import check_call

from charmhelpers.core.hookenv import config
from charmhelpers.core.templating import render
from charmhelpers.core import unitdata


from charms.layer.spark_base import (
    SPARK_ENV_SH,
    SPARK_DEFAULTS,
)


KV = unitdata.kv()


def render_spark_env_and_defaults():
    """Unpack the tarballs, render the config, chown the dirs.
    """
    conf = config()

    ctxt = {}
    # Generate config context
    if conf.get('object-storage-gateway') and \
       conf.get('aws-access-key') and \
       conf.get('aws-secret-key'):

        model_uuid = os.getenv('JUJU_MODEL_UUID')[-6:]
        bucket = "s3a://spark-event-logs/juju-spark-{}".format(model_uuid)
        ctxt['event_log_dir'] = bucket
        ctxt['hadoop_version'] = KV.get('hadoop_version')
        ctxt['object_storage_gateway'] = conf.get('object-storage-gateway')
        ctxt['aws_access_key'] = conf.get('aws-access-key')
        ctxt['aws_secret_key'] = conf.get('aws-secret-key')
        ctxt['s3_ssl_enabled'] = conf.get('s3-ssl-enabled')
    else:
        ctxt['event_log_dir'] = '/tmp/spark-events'

    # Render the configs
    if SPARK_DEFAULTS.exists():
        SPARK_DEFAULTS.unlink()
    render('spark-defaults.conf', str(SPARK_DEFAULTS), context=ctxt)

    if SPARK_ENV.exists():
        SPARK_ENV.unlink()
    render('spark-env.sh', str(SPARK_ENV), context=ctxt)
    check_call(['chmod', '755', str(SPARK_ENV)])
