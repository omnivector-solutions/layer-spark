export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64/jre

export SPARK_LOCAL_IP={{bind_address}}
export SPARK_MASTER_HOST={{master_ip}}
export SPARK_MASTER_PORT=7077
export SPARK_MASTER_WEBUI_PORT=8080

export SPARK_WORKER_DIR=/srv/spark/work
export SPARK_WORKER_PORT=7078
export SPARK_WORKER_WEBUI_PORT=8081

export SPARK_HOME=${SPARK_HOME:-/opt/spark}
export SPARK_LOG_DIR=${SPARK_LOG_DIR:-/var/log/spark}
export SPARK_LOCAL_DIRS=/srv/spark_local
export SPARK_WORKER_DIR=/srv/spark_work

# EXTRA SPARK + HADOOP VARS
export HADOOP_HOME=${HADOOP_HOME:-/opt/hadoop}
export HADOOP_LIBRARY_PATH="${HADOOP_LIBRARY_PATH}:${HADOOP_HOME}/lib/native"

export SPARK_DIST_CLASSPATH=$(/opt/hadoop/bin/hadoop classpath)
export SPARK_LIBRARY_PATH="${SPARK_LIBRARY_PATH}:${HADOOP_LIBRARY_PATH}"
export SPARK_EXTRA_CLASSPATH="${SPARK_EXTRA_CLASSPATH}:${SPARK_DIST_CLASSPATH}"
export SPARK_DAEMON_CLASSPATH="${SPARK_DAEMON_CLASSPATH}:${HADOOP_HOME}/share/hadoop/tools/lib/*"
export SPARK_LIBRARY_PATH=$SPARK_LIBRARY_PATH:${HADOOP_HOME}/lib/native

export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:${HADOOP_LIBRARY_PATH}"
