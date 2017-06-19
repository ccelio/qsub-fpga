#!/usr/bin/env python

# Christopher Celio

# Build a pk/bbl+linux+initramfs for benchmarking on the FPGA, only include the one benchmark you want.
# Must include benchmark directory and include which directory you want.

import optparse
import subprocess
import getpass
import os
from datetime import datetime

import python.cluster_scripts
import python.target_software

LINUX_SOURCE=os.path.join("/scratch", getpass.getuser(), "initramfs_linux_flow")
TARGET="rocket"
#TARGET="boom-2w"
BASE_DIR=os.path.join("/nscratch", getpass.getuser(), "boom-thesis", TARGET)
BUILD_DIR=os.path.join(BASE_DIR, "script")
OUTPUT_DIR=os.path.join(BASE_DIR, "output")
DEFAULT_FPGA_BITSTREAM=os.path.join(BASE_DIR, "midas_wrapper.bit")
LATENCY=1
DEFAULT_SIM_FLAGS="+mm_LATENCY=%d" % (LATENCY)
EMAIL_ENABLED=True

ENABLE_GCC=False
ENABLE_BASH=False
ENABLE_PYTHON=False

parser = optparse.OptionParser()
parser.add_option('-f', '--file', dest='filename', help='input command file')
parser.add_option('-b', '--bitstream', dest='bitstream', help='input bitstream file')
parser.add_option('-c', '--compile', dest='compile', default=False,
                  action="store_true", help='compile linux')
parser.add_option('-j', '--java', dest='java', default=False,
                  action="store_true", help='compile java.')
parser.add_option('-r', '--run', dest='run', default=False,
                  action="store_true", help='Submits the jobs to the FPGA cluster')
parser.add_option('-d', '--disable_counters', dest='disable_counters', default=False,
                  action="store_true", help='Does not run rv_counters in target machine.')
parser.add_option('-s', '--sim-flags', dest='sim_flags', default=False, help='simulation flags')
(options, args) = parser.parse_args()
if not options.filename:
    parser.error('Please give an input filename with -f')

fpga_bitstream = options.bitstream if options.bitstream else DEFAULT_FPGA_BITSTREAM
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
    if options.run:
      linux = os.path.join("/nscratch", "midas", "build", "bblvmlinux-" + bmk_str)
      generate_qsub_file(bmk_str, cmd_str, sfile, OUTPUT_DIR, linux, fpga_bitstream, sim_flags)
      # now we can qsub on the file we just created
      print "run:", "sbatch", sfile
      subprocess.check_call(["sbatch", sfile])

