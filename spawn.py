#!/usr/bin/env python

# Christopher Celio


# Build a pk/bbl+linux+initramfs for benchmarking on the FPGA, only include the one benchmark you want.
# Must include benchmark directory and include which directory you want.

import optparse
import subprocess
import getpass
import os
import shutil
from datetime import datetime

LINUX_SOURCE=os.path.join("/scratch", getpass.getuser(), "initramfs_linux_flow")
TARGET="default"
#TARGET="rocket-l2-80btbs"
#TARGET="rocket-l2-160btbs"
#TARGET="rocket-l2-320btbs"
#TARGET="rocket-l2-480btbs"
#TARGET="boom-2w-l2"
#TARGET="boom-2w-tage-l2"
#TARGET="boom-2w-gshare-l2-80btbs"
#TARGET="boom-2w-gshare-l2-320btbs"
#TARGET="boom-2w-gshare-l2-480btbs"
BASE_DIR=os.path.join("/nscratch", getpass.getuser(), "midas-top-sw-cleanup", TARGET)
BUILD_DIR=os.path.join(BASE_DIR, "script")
OUTPUT_DIR=os.path.join(BASE_DIR, "output")
FPGA_BITSTREAM=os.path.join(BASE_DIR, "midas_wrapper.bit")
MEM_LATENCY=80
DEFAULT_SIM_FLAGS="+mm_readLatency=8 +mm_writeLatency=8 +mm_readMaxReqs=4 +mm_writeMaxReqs=4"

EMAIL_ENABLED=True
ENABLE_GCC=False
ENABLE_BASH=False
ENABLE_PYTHON=False
ENABLE_JAVA=False

HOST_FILES_TO_COPY=["memory_stats.csv"]

def main():
    parser = optparse.OptionParser()
    parser.add_option('-f', '--file', dest='filename', help='input command file')
    parser.add_option('-c', '--compile', dest='compile', default=False,
                      action="store_true", help='compile linux')
    parser.add_option('-j', '--java', dest='java', default=False,
                      action="store_true", help='compile java.')
    parser.add_option('-r', '--run', dest='run', default=False,
                      action="store_true", help='run simulation')
    parser.add_option('-d', '--disable_counters', dest='disable_counters', default=False,
                      action="store_true", help='Does not run rv_counters in target machine.')
    parser.add_option('-s', '--sim-flags', dest='sim_flags', default=False, help='simulation flags')
    (options, args) = parser.parse_args()
    if not options.filename:
        parser.error('Please give an input filename with -f')
    
    sim_flags = options.sim_flags if options.sim_flags else DEFAULT_SIM_FLAGS

    f = open(options.filename)
    if not os.path.exists(OUTPUT_DIR):
      os.makedirs(OUTPUT_DIR)
    print OUTPUT_DIR

    # Each line in the command file represents a different ramdisk image and
    # thus the basic unit of qsub-task parallelism
    for line in f:
        if line[0] == '#': continue
        (bmk_str, dir_str, cmd_str) = line.split("#")
        bmk_str = bmk_str.strip()
        dir_str = dir_str.strip()
        cmd_str = cmd_str.lstrip().strip()
        # For come complicated benchmarks consisting of multiple shell commands
        # a file path can be given inplace of a single shell command
        if (cmd_str.startswith("FILE:")):
          with open(cmd_str[5:], 'r') as cmd_file:
            cmd_str = ''.join(cmd_file.readlines())

        print "Benchmark  : ", bmk_str
        if not os.path.exists(BUILD_DIR):
          os.makedirs(BUILD_DIR)
        sfile = os.path.join(BUILD_DIR, 'scmd_' + bmk_str + ".sh")
        initfile = os.path.join(BUILD_DIR, 'init_profile_' + bmk_str)
        print cmd_str
        if options.compile:
          generate_init_file(cmd_str, initfile, options.java, options.disable_counters)
          generate_bblvmlinux(bmk_str, dir_str, initfile, options.java)
        linux = os.path.join("/nscratch", "midas", "build", "bblvmlinux-" + bmk_str)
        generate_qsub_file(bmk_str, cmd_str, sfile, OUTPUT_DIR, linux, sim_flags)
        if options.run:
          # now we can qsub on the file we just created
          print "run:", "sbatch", sfile
          subprocess.check_call(["sbatch", sfile])

#---------------------
def generate_init_file(cmd_str, initfile, java, disable_counters):
    print "Opening initfile: ", initfile
    with open(initfile, 'w') as f:
        # f.write("echo \"\"\n")
        # f.write("uname -a\n")
        # f.write("echo \"\"\n")
        if ENABLE_PYTHON:
            f.write("export PATH=$PATH:/usr/libexec/gcc/riscv64-poky-linux/6.1.1\n")
            f.write("export PYTHONHOME=/usr\n")
            f.write("export PYTHONPATH=/usr/lib/python2.7\n")
        f.write("cd /usr/bin\n")
        if ENABLE_GCC:
            f.write("ln -s riscv64-poky-linux-addr2line addr2line\n")
            f.write("ln -s riscv64-poky-linux-ar ar\n")
            f.write("ln -s riscv64-poky-linux-as as\n")
            f.write("ln -s riscv64-poky-linux-c++filt c++filt\n")
            f.write("ln -s riscv64-poky-linux-elfedit elfedit\n")
            f.write("ln -s riscv64-poky-linux-gcc gcc\n")
            f.write("ln -s riscv64-poky-linux-gprof gprof\n")
            f.write("ln -s riscv64-poky-linux-ld ld\n")
            f.write("ln -s riscv64-poky-linux-ld.bfd ld.bfd\n")
            f.write("ln -s riscv64-poky-linux-nm nm\n")
            f.write("ln -s riscv64-poky-linux-objcopy objcopy\n")
            f.write("ln -s riscv64-poky-linux-objdump objdump\n")
            f.write("ln -s riscv64-poky-linux-ranlib ranlib\n")
            f.write("ln -s riscv64-poky-linux-readelf readlef\n")
            f.write("ln -s riscv64-poky-linux-size size\n")
            f.write("ln -s riscv64-poky-linux-strings strings\n")
            f.write("ln -s riscv64-poky-linux-strip strip\n")
        if ENABLE_PYTHON:
            f.write("\n")
            f.write("ln -s python2.7 python2\n")
            f.write("ln -s python2 python\n")
            f.write("ln -s python2.7-config python2-config\n")
            f.write("ln -s python2-config python-config\n")
 
        # f.write("ls -ls /bin\n")
        # f.write("ls -ls /usr/bin\n")
        if not java:
          f.write("cd /celio\n")
        else:
          f.write("cd /JikesRVM\n")
        f.write("ls\n")
        for cmd in cmd_str.split("\n"):
          f.write("echo " + cmd + "\n")
        if not disable_counters:
          f.write("./rv_counters &\n")
          f.write("sleep 1\n")
        f.write(cmd_str + "\n")
        if not disable_counters:
          f.write("killall rv_counters\n")
          f.write("while pgrep rv_counters > /dev/null; do sleep 1; done\n")
          f.write("sync\n")
        f.write("poweroff -f\n")


#---------------------
def generate_bblvmlinux(bmk_str, dir_str, initfile, java):
    print "Generating bblvmlinux with: ", initfile
    shutil.copyfile(initfile, os.path.join(LINUX_SOURCE, "profile"))
    subprocess.check_call(
      ["./build-initram.py", "--dir", "/nscratch/midas/initram/" + dir_str] + (
      ["--bmark", "java"] if java else []), cwd=LINUX_SOURCE)
    subprocess.check_call(
      ["make", "DIRNAME=" + dir_str] + (
      ["BUILD_JAVA=1"] if java else []), cwd=LINUX_SOURCE, shell=True)
    linux = os.path.join(BUILD_DIR, "bblvmlinux-" + bmk_str)
    shutil.copyfile(os.path.join(LINUX_SOURCE, "bblvmlinux"), linux)

    return linux

#---------------------
def generate_qsub_file(bmk_str, cmd_str, sfile, output_dir, linux, sim_flags):
    with open(sfile, 'w') as f:
        # I can't get this to work with sh for some reason
        f.write("#!/bin/bash\n")
        f.write("### This file was auto-generated by spawn.py\n")
        f.write("### Set the job name\n")
        f.write("#SBATCH -J " + bmk_str + "\n\n")
        # f.write("### Declare myprogram non-rerunable\n")
        # f.write("#SBATCH -r n \n\n")
        f.write("### Email User\n")
        f.write("#SBATCH --uid=" + getpass.getuser() + "\n")
        if (EMAIL_ENABLED):
            f.write("#SBATCH --mail-type=END\n")
            f.write("#SBATCH --mail-user=" + getpass.getuser() + "@eecs.berkeley.edu\n\n")
        else:
            f.write("### #SBATCH --mail-type=NONE\n\n")
         
        f.write("### Assign one FPGA\n\n")
        f.write("#SBATCH -p fpga\n\n")
        f.write("#SBATCH --gres=fpga:1\n\n")
        
#        f.write("### -l walltime=HH:MM:SS and -l cput=HH:MM:SS\n")
        f.write("### Jobs on the public clusters are currently limited to 10 days walltime.\n")
        f.write("#SBATCH --time=120:00:00\n")

        f.write("### Supress messages\n")
        f.write("#SBATCH -Q\n")
        print "Current directory(",os.getcwd(),")"
        f.write("SLURMDIR=" + output_dir + "/" + bmk_str + "\n")
        #f.write("JOBID=`echo $PBS_JOBID | sed -e 's/\..*//'`\n")
        f.write("mkdir -p $SLURMDIR\n")
        f.write("exec > $SLURMDIR/out 2> $SLURMDIR/err\n\n")

        ### Jobs should only be run from /scratch, /nscratch or /vlsi; Torque returns results via NFS.
        #f.write("echo Working directory is $PBS_O_WORKDIR\n")
        #f.write("echo with jobid: $JOBID\n")
        #f.write("cd $PBS_O_WORKDIR\n")
        f.write("cd " + BUILD_DIR + "\n")
         
        ### Run some informational commands.
        f.write("echo Running on host `hostname`\n")
        f.write("echo Time is `date`\n")
        f.write("echo Directory is `pwd`\n")
         
#        f.write("### the command we care about:\n")
#        f.write("echo ['" + cmd_str.replace('\n','') + "']\n")
#        f.write("time spike -g +disk=" + root_bin + " bbl vmlinux")
          
        ### FPGA stuff
        f.write("### FPGA Stuff\n")
        f.write("source /nscratch/fpga-cluster/fpga-scripts/aspire-fpga-cluster-select.sh\n")
        f.write("sleep 1\n")
        f.write("echo \"FPGA ID:\"\n")
        f.write("echo $FPGA_ID\n")
        f.write("echo \"FPGA IP:\"\n")
        f.write("echo $FPGA_IP\n")
        f.write("### Load the fpga bitfile\n")
        f.write("source /ecad/tools/xilinx/Vivado/2016.2/settings64.sh\n")
        f.write("which vivado\n")
        # Reset the FPGA, in case it is in an unusable state
        f.write("### Reset the FPGA in case it hung in an earlier run\n")
        f.write("count=0\n")
        f.write("/opt/apc-8/snmp-apc-set.sh $FPGA_ID 3\n")
        f.write("while true; do\n")
        f.write("    count=$[$count + 1]\n")
        f.write("    if ping -c 1 $FPGA_IP &> /dev/null\n")
        f.write("    then\n")
        f.write("        break\n")
        f.write("    fi\n")
        f.write("    if [ $count -gt 30 ]\n")
        f.write("    then\n")
        f.write("        echo FPGA did not come out of reset.\n")
        f.write("        exit 255\n")
        f.write("    fi\n")
        f.write("done\n\n")

        # Execute FPGA programming as a critical section
        f.write("### Program the FPGA\n")
        f.write("(\n")
        f.write("  flock -e 200\n")
        f.write("  /nscratch/fpga-cluster/fpga-scripts/load-bitstream.sh " + FPGA_BITSTREAM + "\n")
        f.write("  sleep 1\n")
        f.write(") 200>/var/lock/.load-bitstream.sh.lock\n")
        
        f.write("### Copy the MIDAS driver\n")
        key = os.path.join("~", ".ssh", "id_rsa")
        f.write("scp -i %s %s root@$FPGA_IP:/sdcard/midas/MidasTop-zynq\n" % (
                key, os.path.join(BASE_DIR, "MidasTop-zynq")))
        f.write("scp -i %s %s root@$FPGA_IP:/usr/local/lib/libfesvr.so\n" % (
                key, os.path.join(BASE_DIR, "libfesvr.so")))

        f.write("### Send over the image we want to the FPGA\n")
        f.write("scp -i " + key + " " + linux + " root@$FPGA_IP:/sdcard/midas/linux\n")
        f.write("sleep 2\n")

        f.write("### Log-in to the FPGA and run the benchmark\n")
        f.write("echo ['" + cmd_str.replace('\n','') + "']\n")
        f.write("time ssh root@$FPGA_IP -i " + key +
          " -t \"ls; sync; uname -a; ls /sdcard/midas; cd /sdcard/midas; ./MidasTop-zynq " +
          ' '.join(sim_flags.split()) + " ./linux\"\n")

        for fn in HOST_FILES_TO_COPY:
          f.write("scp -i %s root@$FPGA_IP:/sdcard/midas/%s $SLURMDIR/%s" % (key, fn, fn))


if __name__ == '__main__':
    main()

