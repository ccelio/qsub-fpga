#!/bin/bash
#set -e
#INPUT_TYPE=test
INPUT_TYPE=ref
COMMAND_DIR=/nscratch/midas/initram/riscv-spec-${INPUT_TYPE}/commands
OUTPUT_SUBDIR=/nscratch/midas/profile/spec

# the integer set
BENCHMARKS=(400.perlbench 401.bzip2 403.gcc 429.mcf 445.gobmk 456.hmmer 458.sjeng 462.libquantum 464.h264ref 471.omnetpp 473.astar 483.xalancbmk)


QSUB_COMMAND_FILE=spec.$INPUT_TYPE.txt
if [[ -e $QSUB_COMMAND_FILE ]]; then
echo "Removing existing $QSUB_COMMAND_FILE"
rm $QSUB_COMMAND_FILE
fi

mkdir -p $OUTPUT_SUBDIR

for b in ${BENCHMARKS[@]}; do

  SHORT_EXE=${b##*.} # cut off the numbers ###.short_exe
  # handle benchmarks that don't conform to the naming convention
  if [ $b == "482.sphinx3" ]; then SHORT_EXE=sphinx_livepretend; fi
  if [ $b == "483.xalancbmk" ]; then SHORT_EXE=Xalan; fi

  # read the command file
  IFS=$'\n' read -d '' -r -a commands < $COMMAND_DIR/${b}.${INPUT_TYPE}.cmd

  PROFILE_FILE=${OUTPUT_SUBDIR}/${b}.${INPUT_TYPE}.txt
  if [[ -e $PROFILE_FILE ]]; then
    echo "Removing existing $PROFILE_FILE"
    rm $PROFILE_FILE
  fi

  # Write the benchmark to the qsub command file
  echo "${b}.${INPUT_TYPE} # riscv-spec-${INPUT_TYPE}/${b} # FILE:${PROFILE_FILE}" >> $QSUB_COMMAND_FILE

  echo "Generating ${PROFILE_FILE}"
  for input in "${commands[@]}"; do
     if [[ ${input:0:1} != '#' ]]; then # allow us to comment out lines in the cmd files
        echo "./${SHORT_EXE} $input" >> $PROFILE_FILE
     fi
  done

done


echo ""
echo "Done!"
