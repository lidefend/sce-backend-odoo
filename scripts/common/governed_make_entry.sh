#!/usr/bin/env bash

require_governed_make_ancestor() {
  local label="${1:?guard label required}"
  local expected_root="${2:?expected repository root required}"
  local allowed_targets="${3:?allowed make targets required}"
  local pid="${PPID:-0}"
  local depth=0
  local cmd parent
  while [[ "$pid" =~ ^[0-9]+$ ]] && (( pid > 1 )) && (( depth < 16 )); do
    cmd="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)"
    if [[ "$cmd" =~ (^|[[:space:]/])(g?make)([[:space:]]|$) ]]; then
      local make_cwd target make_env arg
      local -a argv targets
      make_cwd="$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)"
      make_env="$(tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null || true)"
      mapfile -d '' -t argv < "/proc/$pid/cmdline" || true
      local injected=0
      if grep -Eq '^MAKEFILES=.+' <<<"$make_env"; then injected=1; fi
      while IFS= read -r make_flag_line; do
        [[ -n "$make_flag_line" ]] || continue
        local make_flag_value="${make_flag_line#*=}"
        local -a make_flag_tokens
        read -r -a make_flag_tokens <<<"$make_flag_value"
        for make_flag in "${make_flag_tokens[@]}"; do
          case "$make_flag" in
            -f*|--f*|--m*|-E*|--e*) injected=1 ;;
          esac
        done
      done < <(grep -E '^(MAKEFLAGS|GNUMAKEFLAGS)=' <<<"$make_env" || true)
      local -a goals
      goals=()
      local index=0
      while (( index < ${#argv[@]} )); do
        arg="${argv[$index]}"
        case "$arg" in
          */make|*/gmake|make|gmake) ;;
          MAKEFILES=*|MAKEFLAGS=*|GNUMAKEFLAGS=*) injected=1 ;;
          # Permit only options that cannot select/inject makefiles, rules, or
          # evaluated source. GNU long-option abbreviations make a denylist
          # unsafe (for example --makef= is accepted as --makefile=).
          -j|--jobs)
            if (( index + 1 < ${#argv[@]} )) && [[ "${argv[$((index + 1))]}" =~ ^[0-9]+$ ]]; then
              index=$((index + 1))
            fi
            ;;
          --output-sync)
            if (( index + 1 < ${#argv[@]} )) && [[ "${argv[$((index + 1))]}" =~ ^(none|line|target|recurse)$ ]]; then
              index=$((index + 1))
            fi
            ;;
          -s|--silent|--quiet|--no-print-directory|-k|--keep-going|-[j][0-9]*|--jobs=[0-9]*|--output-sync=*) ;;
          -*) injected=1 ;;
          *=*) ;;
          *) goals+=("$arg") ;;
        esac
        index=$((index + 1))
      done
      if [[ "$make_cwd" == "$(readlink -f "$expected_root")" && "$injected" == "0" && "${#goals[@]}" == "1" ]]; then
        IFS=',' read -r -a targets <<<"$allowed_targets"
        for target in "${targets[@]}"; do
          [[ "${goals[0]}" == "$target" ]] && return 0
        done
      fi
    fi
    parent="$(awk '{print $4}' "/proc/$pid/stat" 2>/dev/null || true)"
    [[ "$parent" =~ ^[0-9]+$ ]] || break
    pid="$parent"
    depth=$((depth + 1))
  done
  echo "DENY: $label requires a governed repository Make target ($allowed_targets)" >&2
  return 2
}
