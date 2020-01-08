#!/bin/bash

script='
export PATH="$PATH":/root/.local/bin
ln -s /work/local ~/.local
ln -s /work/cache ~/.cache
clear
cd js
pip install --user -r requirements.txt
pytest tests/
'

main() {
    [[ -e requirements.txt ]] || poetry export -f requirements.txt --dev -o requirements.txt
    work=/tmp/test-work
    mkdir -p $work/{cache,local}
    docker run --rm -it -v `pwd`:/js -v ${work}:/work python:$1 bash -c "$script"
}

main $1
