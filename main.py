#!/usr/bin/env python3
from github import Github, GithubException
import semver, argparse, os, sys

def parse_args():
    p = argparse.ArgumentParser(description="Generador de tags SemVer")
    p.add_argument('--repo', required=True)
    p.add_argument('--bump', choices=['major','minor','patch'], default='patch')
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

def generate_new_version(args, repo):
    base            = get_version_base(repo)
    bumped_version  = getattr(base, f"bump_{args.bump}")() if args.bump else base
    
    return bumped_version

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
            with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
                fh.write(f'new_tag={new_tag}\n')
            print(f"✅ Tag creado")
        else:
            print(f"ℹ️ Dry-run: {new_tag}")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()