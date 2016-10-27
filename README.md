
*Example usage:*

    ./spawn.py -b bitfiles/rocket.bit -o output-rocket/ -f commands/hello.txt

*Command files:*

    // benchmark directory # name to apply to benchmark run # commands to execute.

    hello # hello # ./hello.riscv

    The benchmark directory will be copied over and the commands will start from within the directory after boot.
