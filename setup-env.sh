#!/usr/bin/env bash

# Debe cargarse en la terminal actual para que la activación persista.
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    printf 'Usa: source ./setup-env.sh\n' >&2
    exit 1
fi

_spidertomp3_setup_env() {
    local project_dir venv_dir activate_script requirements_stamp
    local -a interpreter=()

    project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)" || return 1
    venv_dir="$project_dir/.venv"

    if [[ ! -f "$venv_dir/bin/activate" && ! -f "$venv_dir/Scripts/activate" ]]; then
        if [[ -e "$venv_dir" ]]; then
            printf 'El entorno %s está incompleto. Revísalo antes de repetir la instalación.\n' "$venv_dir" >&2
            return 1
        fi

        case "${OSTYPE:-}:${OS:-}" in
            msys*|cygwin*|*:Windows_NT)
                if command -v py >/dev/null 2>&1 && py -3 -c 'import sys; sys.exit(sys.version_info < (3, 12))' >/dev/null 2>&1; then
                    interpreter=(py -3)
                elif command -v python >/dev/null 2>&1 && python -c 'import sys; sys.exit(sys.version_info < (3, 12))' >/dev/null 2>&1; then
                    interpreter=(python)
                fi
                ;;
            *)
                if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(sys.version_info < (3, 12))' >/dev/null 2>&1; then
                    interpreter=(python3)
                elif command -v python >/dev/null 2>&1 && python -c 'import sys; sys.exit(sys.version_info < (3, 12))' >/dev/null 2>&1; then
                    interpreter=(python)
                fi
                ;;
        esac

        if ((${#interpreter[@]} == 0)); then
            printf 'Instala Python 3.12 o superior y comprueba que esté en el PATH.\n' >&2
            return 1
        fi
        "${interpreter[@]}" -m venv "$venv_dir" || return 1
    fi

    if [[ -f "$venv_dir/bin/activate" ]]; then
        activate_script="$venv_dir/bin/activate"
    else
        activate_script="$venv_dir/Scripts/activate"
    fi
    source "$activate_script" || return 1

    if ! python -c 'import sys; sys.exit(sys.version_info < (3, 12))'; then
        printf 'El entorno virtual necesita Python 3.12 o superior.\n' >&2
        return 1
    fi

    requirements_stamp="$venv_dir/.spidertomp3-requirements-installed"
    if ! cmp -s "$project_dir/requirements.txt" "$requirements_stamp"; then
        python -m pip install -r "$project_dir/requirements.txt" || return 1
        cp "$project_dir/requirements.txt" "$requirements_stamp" || return 1
    fi

    printf 'Entorno activo: %s\n' "$venv_dir"
}

if _spidertomp3_setup_env; then
    unset -f _spidertomp3_setup_env
    return 0
else
    unset -f _spidertomp3_setup_env
    return 1
fi
