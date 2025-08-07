#!/usr/bin/env python3
from github import Github, GithubException
import semver, argparse, os, sys
from typing import Optional, List

class ReleaseTagger:
    def __init__(self, repo: str, token: str):
        self.gh = Github(token)
        self.repo = self.gh.get_repo(repo)
        self.all_tags = self._load_valid_tags()

    def _load_valid_tags(self) -> List[dict]:
        """Carga todos los tags válidos ordenados por versión (más reciente primero)"""
        valid_tags = []
        for tag in self.repo.get_tags():
            try:
                version_str = tag.name[1:] if tag.name.startswith('v') else tag.name
                ver = semver.VersionInfo.parse(version_str)
                valid_tags.append({
                    'name': tag.name,
                    'version': ver,
                    'object': tag
                })
            except ValueError:
                continue
        return sorted(valid_tags, key=lambda x: x['version'], reverse=True)

    def _get_latest_stable(self) -> Optional[semver.VersionInfo]:
        """Obtiene la última versión estable"""
        for tag in self.all_tags:
            if not tag['version'].prerelease:
                return tag['version']
        return semver.VersionInfo.parse("0.1.0")

    def _get_latest_rc(self) -> Optional[semver.VersionInfo]:
        """Obtiene la última RC de la próxima versión estable"""
        latest_stable = self._get_latest_stable()
        for tag in self.all_tags:
            if tag['version'].prerelease and tag['version'].prerelease.startswith('rc'):
                if tag['version'].major == latest_stable.major and \
                   tag['version'].minor == latest_stable.minor and \
                   tag['version'].patch == latest_stable.patch:
                    return tag['version']
        return None

    def generate_new_version(self, bump_type: str, release_channel: str) -> semver.VersionInfo:
        """Genera la nueva versión según el tipo de release"""
        base_version = self._get_latest_stable()
        
        # Incrementar según bump-type
        bumped_version = getattr(base_version, f"bump_{bump_type}")()

        if release_channel == "release-candidate":
            latest_rc = self._get_latest_rc()
            rc_number = latest_rc.prerelease.split('.')[1] + 1 if latest_rc else 1
            return bumped_version.replace(prerelease=f"rc.{rc_number}")
        
        return bumped_version  # Versión estable

    def create_tag(self, version: semver.VersionInfo, commit_sha: str):
        """Crea el tag en GitHub"""
        tag_name = f"v{version}"
        try:
            self.repo.create_git_tag(
                tag=tag_name,
                message=f"Auto-generated release: {tag_name}",
                object=commit_sha,
                type='commit'
            )
            self.repo.create_git_ref(f"refs/tags/{tag_name}", commit_sha)
            return tag_name
        except GithubException as e:
            raise RuntimeError(f"GitHub API error: {e.data.get('message', str(e))}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True)
    parser.add_argument('--bump-type', choices=['major','minor','patch'], default='patch')
    parser.add_argument('--release-channel', choices=['release-candidate','release'], default='release-candidate')
    parser.add_argument('--commit-sha', required=True)
    args = parser.parse_args()

    try:
        tagger = ReleaseTagger(args.repo, os.getenv("GITHUB_TOKEN"))
        new_version = tagger.generate_new_version(args.bump_type, args.release_channel)
        new_tag = tagger.create_tag(new_version, args.commit_sha)
        
        # Set GitHub Actions output
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f'new-tag={new_tag}\n')
        
        print(f"✅ Tag creado: {new_tag}")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()