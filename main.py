#!/usr/bin/env python3
from github import Github, GithubException
import semver, argparse, os, sys

def parse_args():
    p = argparse.ArgumentParser(description="Generador de tags SemVer")
    p.add_argument('--repo', required=True)
    p.add_argument('--level', choices=['major','minor','patch'], default='patch')
    p.add_argument('--channel', choices=['beta','rc','release'], default='release')
    p.add_argument('--sha', help='SHA del commit')
    p.add_argument('--dry-run', action='store_true')
    return p.parse_args()

def get_version_base(repo):
    for tag in repo.get_tags():
        if tag.name.startswith('v'):
            try:
                ver = semver.VersionInfo.parse(tag.name[1:])
                if not ver.prerelease: return ver
            except ValueError: continue
    return semver.VersionInfo(major=0, minor=1, patch=0)

def get_last_prerelease(repo, base_version, channel):
    max_num = 0
    for tag in repo.get_tags():
        if tag.name.startswith(f"v{base_version}-{channel}."):
            try:
                num = int(semver.VersionInfo.parse(tag.name[1:]).prerelease.split('.')[1])
                max_num = max(max_num, num)
            except (ValueError, IndexError): continue
    return max_num

def generate_new_version(args, repo):
    base = get_version_base(repo)
    if args.channel == "release":
        return getattr(base, f"bump_{args.level}")()
    last_num = get_last_prerelease(repo, str(base).split('-')[0], args.channel)
    return base.replace(prerelease=f"{args.channel}.{last_num + 1}")

def main():
    args = parse_args()
    try:
        repo = Github(os.getenv("GITHUB_TOKEN")).get_repo(args.repo)
        new_tag = f"v{generate_new_version(args, repo)}"
        print(f"🔍 Base: {get_version_base(repo)}\n🚀 Nuevo tag: {new_tag}")
        
        if not args.dry_run:
            repo.create_git_tag(
                tag=new_tag,
                message=f"Release {new_tag}",
                object=args.sha,
                type='commit'
            )
            repo.create_git_ref(f"refs/tags/{new_tag}", args.sha)
            print(f"✅ Tag creado")
        else:
            print(f"ℹ️ Dry-run: {new_tag}")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()