# Desc: Quick Start

set -x
set -e
# keep track of the last executed command
trap 'last_command=$current_command; current_command=$BASH_COMMAND' DEBUG
# echo an error message before exiting
trap 'echo "\"${last_command}\" command filed with exit code $?."' EXIT

uname_r=$(uname -r)
uname_noarch=${uname_r%.*}
yum install anolis-repos -y
yum install podman kernel-debuginfo-${uname_r} kernel-devel-${uname_r} --enablerepo=Plus-debuginfo --enablerepo=Plus -y

cd /tmp/plugsched
podman build -t plugsched/plugsched-sdk . -f Dockerfile.${arch}
mkdir -p /tmp/work
cd /tmp/work
curl https://mirrors.openanolis.cn/anolis/7.9/Plus/source/Packages/kernel-${uname_noarch}.src.rpm -o kernel-${uname_noarch}.src.rpm
container=$(podman ps | awk '$NF=="plugsched"{print $1}')
if [ -n "$container" ]; then
        podman rm -f ${container}
fi
podman run -itd --name=plugsched -w /root/ -v /tmp/work:/root -v /usr/src/kernels:/usr/src/kernels -v /usr/lib/debug/lib/modules:/usr/lib/debug/lib/modules plugsched/plugsched-sdk /bin/bash
podman exec -it plugsched plugsched-cli extract_src kernel-${uname_noarch}.src.rpm ./kernel
podman exec -it plugsched plugsched-cli init ${uname_r} ./kernel ./scheduler
cat > patch <<EOF
diff --git a/scheduler/kernel/sched/mod/core.c b/scheduler/kernel/sched/mod/core.c
index 9f16b72..21262fd 100644
--- a/scheduler/kernel/sched/mod/core.c
+++ b/scheduler/kernel/sched/mod/core.c
@@ -3234,6 +3234,8 @@ static void __sched notrace __schedule(bool preempt)
 	struct rq *rq;
 	int cpu;

+	printk_once("I am the new scheduler: __schedule\n");
+
 	cpu = smp_processor_id();
 	rq = cpu_rq(cpu);
 	prev = rq->curr;
EOF
podman cp patch plugsched:/root/
podman exec -it plugsched patch -f -p1 -i patch
podman exec -it plugsched plugsched-cli build scheduler
podman exec -it plugsched ls /usr/local/lib/plugsched/rpmbuild/RPMS/${arch}/
podman exec -it plugsched cp /usr/local/lib/plugsched/rpmbuild/RPMS/${arch}/scheduler-xxx-${uname_noarch}.yyy.${arch}.rpm /root
rpm -ivh /tmp/work/scheduler-xxx-${uname_noarch}.yyy.*.rpm
if ! dmesg | grep "I am the new scheduler: __schedule"; then
	2>&1 echo "Failed to install the scheduler module"
	exit 1
fi
