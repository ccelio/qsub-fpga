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

#FPGA_BITSTREAM="rocketchip_wrapper_mig_hpmss.bit"
DEFAULT_FPGA_BITSTREAM="/nscratch/midas/bitstream/midas_wrapper.bit"
LINUX_SOURCE=os.path.join("/scratch", getpass.getuser(), "initramfs_linux_flow")
BMARK_SOURCE="/nscratch/midas/benchmarks"
OUTPUT_DIR="/nscratch/midas/qsub-fpga-initramfs/output"
DEFAULT_SIM_FLAGS="+mm_writeLatency=20 +mm_readLatency=20 +mm_writeMaxReqs=8 +mm_readMaxReqs=8"

EMAIL_ENABLED=True

ENABLE_GCC=False
ENABLE_BASH=False
ENABLE_PYTHON=False

def main():
    parser = optparse.OptionParser()
    parser.add_option('-f', '--file', dest='filename', help='input command file')
    parser.add_option('-b', '--bitstream', dest='bitstream', help='input bitstream file')
    parser.add_option('-o', '--outdir', dest='outdir', help='output directory')
    parser.add_option('-d', '--disable_counters', dest='disable_counters', default=False,
                      action="store_true", help='Does not run rv_counters in target machine.')
    parser.add_option('-s', '--sim-flags', dest='sim_flags', default=False, help='simulation flags')
    (options, args) = parser.parse_args()
    if not options.filename:
        parser.error('Please give an input filename with -f')
    
    fpga_bitstream = options.bitstream if options.bitstream else DEFAULT_FPGA_BITSTREAM
    sim_flags = options.sim_flags if options.sim_flags else DEFAULT_SIM_FLAGS

    f = open(options.filename)
    now = datetime.now()
    global OUTPUT_DIR 
    if options.outdir:
        OUTPUT_DIR = options.outdir
    else:
        OUTPUT_DIR = OUTPUT_DIR + "-" + "midas"
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
        build_dir = os.path.join('/nscratch', 'midas', 'build')
        if not os.path.exists(build_dir):
          os.makedirs(build_dir)
        qfile = os.path.join(build_dir, 'qcmd_' + bmk_str + ".sh")
        initfile = os.path.join(build_dir, 'init_profile_' + bmk_str)
        print cmd_str
        generate_init_file(cmd_str, dir_str, initfile, options.disable_counters)
        linux = generate_bblvmlinux(bmk_str, dir_str, initfile)
        generate_qsub_file(bmk_str, cmd_str, qfile, OUTPUT_DIR, linux, fpga_bitstream, sim_flags)
        # now we can qsub on the file we just created
        print "run:", "qsub", qfile
        subprocess.check_call(["qsub", qfile])

#---------------------
def generate_init_file(cmd_str, dir_str, initfile, disable_counters):
    print "Opening initfile: ", initfile
    with open(initfile, 'w') as f:
        f.write("echo \"\"\n")
        f.write("uname -a\n")
        f.write("echo \"\"\n")
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
        f.write("cd ~\n")

        f.write("ls -ls /bin\n")
        f.write("ls -ls /usr/bin\n")
        f.write("cd /celio\n")
        f.write("ls\n")
        if not disable_counters:
          f.write("/celio/rv_counters/rv_counters &\n")
        f.write("sleep 1\n")
        f.write(cmd_str + "\n")
        f.write("killall rv_counters\n")
        f.write("while pgrep rv_counters > /dev/null; do sleep 1; done\n")
        f.write("sync\n")
        f.write("poweroff -f\n")


#---------------------
def generate_bblvmlinux(bmk_str, dir_str, initfile):
    print "Generating bblvmlinux with: ", initfile
    shutil.copyfile(initfile, os.path.join(LINUX_SOURCE, "profile"))
    subprocess.check_call(["./build-initram.py", "--dir", "/nscratch/midas/initram/" + dir_str], cwd=LINUX_SOURCE)
    subprocess.check_call(["make", "DIRNAME=" + dir_str], cwd=LINUX_SOURCE, shell=True)
    target_dir = os.path.join("/nscratch", "midas", "qsub-fpga-initramfs", "build")
    if not os.path.exists(target_dir):
      os.makedirs(target_dir)
    linux = os.path.join(target_dir, "bblvmlinux-" + bmk_str)
    shutil.copyfile(os.path.join(LINUX_SOURCE, "bblvmlinux"), linux)
    shutil.copymode(os.path.join(LINUX_SOURCE, "bblvmlinux"), linux)

    return linux

#---------------------
def generate_qsub_file(bmk_str, cmd_str, qfile, output_dir, linux, fpga_bitstream, sim_flags):
    with open(qfile, 'w') as f:
        # I can't get this to work with sh for some reason
        f.write("#!/bin/bash\n")
        f.write("### This file was auto-generated by spawn.py\n")
        f.write("### Set the job name\n")
        f.write("#PBS -N " + bmk_str + "\n\n")
        f.write("### Declare myprogram non-rerunable\n")
        f.write("#PBS -r n \n\n")
        f.write("### Email User\n")
        if (EMAIL_ENABLED):
            f.write("#PBS -m ae\n")
            f.write("#PBS -M " + getpass.getuser() + "@eecs.berkeley.edu\n\n")
        else:
            f.write("### #PBS -m ae\n\n")
         
        f.write("#PBS -q fpga\n\n")
        
#        f.write("### -l walltime=HH:MM:SS and -l cput=HH:MM:SS\n")
        f.write("### Jobs on the public clusters are currently limited to 10 days walltime.\n")
        f.write("#PBS -l walltime=72:00:00\n")
        f.write("#PBS -l cput=96:00:00\n")

        f.write("### redirect stdout/stderr below with exec\n")
        f.write("#PBS -e localhost:/dev/null\n")
        f.write("#PBS -o localhost:/dev/null\n")
        print "Current directory(",os.getcwd(),")"
        f.write("QSUBDIR=" + output_dir + "/\n")
        f.write("JOBID=`echo $PBS_JOBID | sed -e 's/\..*//'`\n")
        f.write("mkdir -p $QSUBDIR\n")
        f.write("exec > $QSUBDIR/" + bmk_str + ".out 2> $QSUBDIR/" + bmk_str +".err\n\n")

        ### Jobs should only be run from /scratch, /nscratch or /vlsi; Torque returns results via NFS.
        f.write("echo Working directory is $PBS_O_WORKDIR\n")
        f.write("echo with jobid: $JOBID\n")
        f.write("cd $PBS_O_WORKDIR\n")
         
        ### Run some informational commands.
        f.write("echo Running on host `hostname`\n")
        f.write("echo Time is `date`\n")
        f.write("echo Directory is `pwd`\n")
        f.write("echo This jobs runs on the following processors:\n")
        f.write("echo `cat $PBS_NODEFILE`\n")
         
#        f.write("### the command we care about:\n")
#        f.write("echo ['" + cmd_str.replace('\n','') + "']\n")
#        f.write("time spike -g +disk=" + root_bin + " bbl vmlinux")
          
        ### FPGA stuff
        f.write("### FPGA Stuff\n")
        f.write("source /nscratch/fpga-cluster/fpga-scripts/aspire-fpga-cluster-select.sh\n")
        f.write("sleep 1\n")
        f.write("echo \"FPGA IP:\"\n")
        f.write("echo $FPGA_IP\n")
        f.write("### Load the fpga bitfile\n")
        f.write("source /ecad/tools/xilinx/Vivado/2016.2/settings64.sh\n")
        f.write("which vivado\n")
        f.write("sleep 1\n")
        f.write("/nscratch/fpga-cluster/fpga-scripts/load-bitstream.sh " + fpga_bitstream + "\n")
        f.write("sleep 2\n")
        
        f.write("### Copy the MIDAS driver\n")
        key = os.path.join("/nscratch", "midas", "ssh", "id_rsa")
        f.write("scp -i " + key + " /nscratch/midas/driver/MidasTop-zynq root@$FPGA_IP:/sdcard/midas/MidasTop-zynq\n")
        f.write("scp -i " + key + " /nscratch/midas/driver/libfesvr.so root@$FPGA_IP:/usr/local/lib/libfesvr.so\n")

        f.write("### Send over the image we want to the FPGA\n")
        f.write("scp -i " + key + " " + linux + " root@$FPGA_IP:/sdcard/midas/linux\n")
        f.write("scp -i " + key + " /nscratch/midas/benchmarks/pk root@$FPGA_IP:/sdcard/midas/pk\n")
        f.write("sleep 2\n")

        f.write("### Log-in to the FPGA and run the benchmark\n")
        f.write("echo ['" + cmd_str.replace('\n','') + "']\n")
        f.write("time ssh root@$FPGA_IP -i " + key + 
          " -t \"ls; sync; uname -a; ls /sdcard/midas; cd /sdcard/midas; ./MidasTop-zynq " +
          sim_flags + " ./linux\"\n")
         

if __name__ == '__main__':
    main()

