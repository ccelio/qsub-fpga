import subprocess
import os
import shutil

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
          f.write("/celio/rv_counters/rv_counters &\n")
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
    shutil.copyfile(os.path.join(LINUX_SOURCE, "busybox_config_%s" % ("java" if java else "spec")),
                    os.path.join(LINUX_SOURCE, "busybox_config"))
    subprocess.check_call(
      ["./build-initram.py", "--dir", "/nscratch/midas/initram/" + dir_str] + (
      ["--bmark", "java"] if java else []), cwd=LINUX_SOURCE)
    subprocess.check_call(
      ["make", "DIRNAME=" + dir_str] + (
      ["BUILD_JAVA=1"] if java else []), cwd=LINUX_SOURCE, shell=True)
    target_dir = os.path.join("/nscratch", "midas", "build")
    if not os.path.exists(target_dir):
      os.makedirs(target_dir)
    linux = os.path.join(target_dir, "bblvmlinux-" + bmk_str)
    shutil.copyfile(os.path.join(LINUX_SOURCE, "bblvmlinux"), linux)

    return linux

