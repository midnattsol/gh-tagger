#!/usr/bin/env python3
"""
Script para generar tags SemVer automáticamente en repositorios GitHub.
Requiere PyGithub y semver (especificados en requirements.txt).
"""

import argparse
import os
import sys
from typing import Optional

from github import Github, GithubException
import semver

def parse_args() -> argparse.Namespace:
    """Configura y parsea los argumentos CLI."""
    parser = argparse.ArgumentParser(
        description="Generador de tags SemVer para GitHub",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--repo',
        required=True,
        help='Repositorio en formato "owner/repo" (ej: "midnattsol/metadata")'
    )
    parser.add_argument(
        '--level',
        choices=['major', 'minor', 'patch'],
        default='patch',
        help='Nivel de incremento de versión'
    )
    parser.add_argument(
        '--channel',
        choices=['beta', 'rc', 'release'],
        default='release',
        help='Canal de release (beta/rc para pre-releases)'
    )
    parser.add_argument(
        '--sha',
         help='SHA del commit a taggear')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simula la acción sin crear tags'
    )
    return parser.parse_args()

def get_latest_version(repo) -> Optional[semver.VersionInfo]:
    """Obtiene la última versión taggeada del repo."""
    try:
        for tag in repo.get_tags():
            if tag.name.startswith('v'):
                version_str = tag.name[1:]  # Elimina el 'v' inicial
                if semver.VersionInfo.is_valid(version_str):
                    return semver.VersionInfo.parse(version_str)
        return None
    except GithubException as e:
        print(f"❌ Error al acceder al repo: {e}")
        sys.exit(1)

def generate_new_version(args, latest_version: Optional[semver.VersionInfo]) -> semver.VersionInfo:
    """Genera la nueva versión según el nivel y canal."""
    base_version = latest_version or semver.VersionInfo(major=0, minor=1, patch=0)
    
    # Bump según el nivel
    bump_methods = {
        'major': 'bump_major',
        'minor': 'bump_minor',
        'patch': 'bump_patch'
    }
    new_version = getattr(base_version, bump_methods[args.level])()
    
    # Añadir pre-release si es necesario
    if args.channel != 'release':
        prerelease_tag = f"{args.channel}.1"
        new_version = new_version.replace(prerelease=prerelease_tag)
    
    return new_version

def main():
    args = parse_args()
    
    # Autenticación con GitHub
    try:
        g = Github(os.getenv("GITHUB_TOKEN"))
        repo = g.get_repo(args.repo)
    except GithubException as e:
        print(f"❌ Fallo de autenticación: {e}")
        sys.exit(1)
    
    # Lógica principal
    latest_version = get_latest_version(repo)
    new_version = generate_new_version(args, latest_version)
    new_tag = f"v{new_version}"
    
    print(f"🔍 Última versión encontrada: {latest_version or 'Ninguna'}")
    print(f"🚀 Nueva versión generada: {new_tag}")
    
    # Crear tag (a menos que sea dry-run)
    if not args.dry_run:
        try:
            commit = repo.get_commit("HEAD")
            repo.create_git_tag(
                tag=new_tag,
                message=f"Release {new_tag}",
                object=args.sha,
                type='commit'
            )
            repo.create_git_ref(f"refs/tags/{new_tag}", args.sha)
            print(f"✅ Tag {new_tag} creado exitosamente")
        except GithubException as e:
            print(f"❌ Error al crear tag: {e}")
            sys.exit(1)

    else:
        print("Ejecutando tagging en modo dry-run")
        print(f"new tag is: {new_tag}")

if __name__ == "__main__":
    main()