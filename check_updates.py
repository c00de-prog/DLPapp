"""Read-only release diagnostics. Does not download, install or change settings."""
import argparse
import sys
from i18n import AppError
from updates import get_json, parse_release, version_key
from version import VERSION, RELEASE_API


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--current',default=VERSION,help='Version to compare, e.g. 2.0.0')
    args=parser.parse_args()
    version_key(args.current)
    print('API:',RELEASE_API)
    print('Installed version for this check:',args.current)
    data=get_json(RELEASE_API)
    print('Latest published stable tag:',data.get('tag_name'))
    release=parse_release(data,current_version=args.current)
    if release:
        print('UPDATE AVAILABLE:',release.version)
        print('Asset: DLPapp.exe')
        print('Bytes:',release.size)
        print('SHA256:',release.digest)
        print('Release:',release.url)
    else:
        print('No newer stable release. Publish a higher version to test discovery.')


if __name__=='__main__':
    try:main()
    except Exception as error:
        print(error.localized('en') if isinstance(error,AppError) else str(error),file=sys.stderr)
        sys.exit(1)
