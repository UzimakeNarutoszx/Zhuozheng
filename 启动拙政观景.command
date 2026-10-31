#!/bin/zsh
cd -- "${0:A:h}" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
python3 scripts/start-local.py "$@"
result=$?
if (( result != 0 )) && [[ -t 0 ]]; then
  printf '\n启动失败，请查看上方提示。按回车关闭。'
  read -r
fi
exit $result
