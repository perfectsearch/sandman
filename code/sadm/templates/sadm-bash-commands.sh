# Convenience functions added automatically by sadm.
# Usage: sb cr <sandbox spec>  -- change to code root of specified sandbox
#        sb br <sandbox spec> -- change to built root of specified sandbox
#        sb tr <sandbox spec>  -- change to test root of specified sandbox
#        sb root <sandbox spec>   -- change to root of specified sandbox
#            sandbox spec can use standard wildcards -- anything sadm recognizes
#            as uniquely identifying a single sandbox from its overall inventory.
#        sb build [sandbox spec] [targets] -- build specified targets
#        sb test [sandbox spec] [args]    -- run tests with specified tags, etc

trim() { echo $1; }

sandbox() {
  sbfound=0
  local sb=$(trim "$1")
  if [ "$sb" = "" ]; then
    sb=.
  fi
  local sbroot=$(python "^[app_path]" path "$sb")
  sbroot=$(trim "$sbroot")
  if [ ${#sbroot} -eq 0 ] ; then
    echo "\"$sb\" does not match exactly one sandbox."
  else
    export SANDBOX=$sbroot
    cd "$sbroot"
    sbfound=1
  fi
}

sb() {
  local verb=$(trim "$1")
  if [[ "$verb" = "bzr" ]]; then
    echo "This looks like a \"bzr\" command."
  elif [[ ${verb} =~ (.r|.*root)$ ]]; then
    sandbox $2
    if [ $sbfound -eq 1 ]; then
      case $verb in
        cr | coderoot )
          cd code;;
        tr | testroot )
          cd test;;
        br | builtroot )
          local sb=$(trim "$2")
          if [ "$sb" = "" ]; then
            sb=.
          fi
          local bltpath=$(python "^[app_folder]/sbverb.py" --sandbox=$sb tpv)
          bltpath=$(trim "$bltpath")
          bltpath="built.${bltpath}"
          cd "$bltpath";;
      esac
    fi
  else
    python "^[app_folder]/sbverb.py" "$@"
  fi
}

_sandbox_complete ()
{
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    pushd ^[sandbox_container_folder] > /dev/null 2>&1
    COMPREPLY=( $(compgen -d ${cur}) )
    popd > /dev/null 2>&1
    return 0
}

_sb_complete ()
{
    local cur prev opts
    #COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    
    if [[ ${prev} =~ (.r|.*root)$ ]] ; then
        pushd ^[sandbox_container_folder] > /dev/null 2>&1
        COMPREPLY=( $(compgen -d ${cur}) )
        popd > /dev/null 2>&1
        return 0
    elif [[ ${prev} == "sb" ]]; then
        COMPREPLY=( $(compgen -W "test build clean eval verify publish properties tpv dependencies tools config" ${cur}) )
        return 0
    else
        COMPREPLY=( $(compgen -d ${cur} || compgen -f ${cur}) )
        return 0
    fi
}

complete -F _sandbox_complete sandbox
complete -o default -F _sb_complete sb
