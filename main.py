#!/usr/bin/env python3
from github import Github, GithubException
import semver, argparse, os, sys
from typing import Optional

def parse_args():
    p = argparse.ArgumentParser(description="Generador de tags SemVer")
    p.add_argument('--repo', required=True)
    p.add_argument('--bump', choices=['major','minor','patch'], default='patch')
    p.add_argument('--channel', choices=['beta','release-candidate','release'], default='release')
    p.add_argument('--sha', help='SHA del commit')
    p.add_argument('--dry-run', action='store_true')
    return p.parse_args()

def get_base_version_by_channel(repo, channel: str) -> Optional[semver.VersionInfo]:
    """
    Encuentra la versión base adecuada según el canal.
    Jerarquía: release -> rc -> beta -> release
    """
    tags = sorted(
        [t for t in repo.get_tags() if t.name.startswith('v')],
        key=lambda t: semver.VersionInfo.parse(t.name[1:]) if semver.VersionInfo.isvalid(t.name[1:]) else semver.VersionInfo.parse("0.0.0"),
        reverse=True
    )

    for tag in tags:
        try:
            ver = semver.VersionInfo.parse(tag.name[1:])
            match channel:
                case 'beta':
                    if not ver.prerelease:  # Basado en última release estable
                        return ver
                case 'release-candidate':
                    if ver.prerelease and ver.prerelease.startswith('beta'):  # Basado en última beta
                        return ver
                case 'release':
                    if ver.prerelease and ver.prerelease.startswith('rc'):  # Basado en última RC
                        return ver
        except ValueError:
            continue
    
    return semver.VersionInfo(major=0, minor=1, patch=0)  # Versión inicial

def get_last_prerelease_number(repo, base_version: str, channel: str) -> int:
    """Obtiene el último número de prerelease para el canal específico"""
    max_num = 0
    channel_prefix = 'rc' if channel == 'release-candidate' else channel
    
    for tag in repo.get_tags():
        if not tag.name.startswith(f"v{base_version}-{channel_prefix}."):
            continue
        
        try:
            prerelease = semver.VersionInfo.parse(tag.name[1:]).prerelease
            if prerelease:
                num = int(prerelease.split('.')[1])
                max_num = max(max_num, num)
        except (ValueError, IndexError):
            continue
    
    return max_num

def generate_new_version(args, repo) -> semver.VersionInfo:
    base_version = get_base_version_by_channel(repo, args.channel)
    
    # Aplicar bump (major, minor, patch)
    bumped_version = getattr(base_version, f"bump_{args.bump}")()
    
    # Manejar prereleases
    if args.channel != "release":
        channel_suffix = 'rc' if args.channel == 'release-candidate' else args.channel
        core_version = str(bumped_version).split('-')[0]
        last_num = get_last_prerelease_number(repo, core_version, args.channel)
        return bumped_version.replace(prerelease=f"{channel_suffix}.{last_num + 1}")
    
    return bumped_version

def main():
    args = parse_args()
    try:
        repo = Github(os.getenv("GITHUB_TOKEN")).get_repo(args.repo)
        new_version = generate_new_version(args, repo)
        new_tag = f"v{new_version}"
        
        print(f"🔍 Versión base: {get_base_version_by_channel(repo, args.channel)}")
        print(f"🚀 Nuevo tag: {new_tag}")
        
        if not args.dry_run:
            repo.create_git_tag(
                tag=new_tag,
                message=f"Release {new_tag}",
                object=args.sha,
                type='commit'
            )
            repo.create_git_ref(f"refs/tags/{new_tag}", args.sha)
            
            # Set output for GitHub Actions
            with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
                fh.write(f'new_tag={new_tag}\n')
            
            print(f"✅ Tag creado exitosamente")
        else:
            print("ℹ️ Modo dry-run: no se creó el tag")
            
    except Exception as e:
        print(f"❌ Error crítico: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()