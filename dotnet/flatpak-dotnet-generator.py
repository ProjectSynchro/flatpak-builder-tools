#!/usr/bin/env python3

__license__ = 'MIT'

from pathlib import Path

import argparse
import base64
import binascii
import json
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', help='The output JSON sources file')
    parser.add_argument('project', nargs='+', help='The project file(s)')
    parser.add_argument('--runtime', '-r', help='The target runtime to restore packages for')
    parser.add_argument('--freedesktop', '-f', help='The target version of the freedesktop sdk to use', 
                        default='23.08')
    parser.add_argument('--dotnet', '-d', help='The target version of dotnet to use', 
                        type=int, default=7)
    parser.add_argument('--destdir',
                        help='The directory the generated sources file will save sources to',
                        default='nuget-sources')
    args = parser.parse_args()
    
    sources = []

    with tempfile.TemporaryDirectory(dir=Path()) as tmp:
        runtime_args = []
        if args.runtime:
            runtime_args.extend(('-r', args.runtime))

        for project in args.project:
            subprocess.run([
                'flatpak', 'run',
                '--env=DOTNET_CLI_TELEMETRY_OPTOUT=true',
                '--env=DOTNET_SKIP_FIRST_TIME_EXPERIENCE=true',
                '--command=sh', '--runtime=org.freedesktop.Sdk//{}'.format(args.freedesktop), '--share=network',
                '--filesystem=host', 'org.freedesktop.Sdk.Extension.dotnet{}//{}'.format(args.dotnet, args.freedesktop), '-c',
                'PATH="${PATH}:'+'/usr/lib/sdk/dotnet{0}/bin" LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/usr/lib/sdk/dotnet{0}/lib" exec dotnet restore "$@"'.format(args.dotnet),
                '--', '--packages', tmp, project] + runtime_args)

        for path in Path(tmp).glob('**/*.nupkg.sha512'):
            name = path.parent.parent.name
            version = path.parent.name
            filename = '{}.{}.nupkg'.format(name, version)
            url = 'https://api.nuget.org/v3-flatcontainer/{}/{}/{}'.format(name, version,
                                                                           filename)

            with path.open() as fp:
                sha512 = binascii.hexlify(base64.b64decode(fp.read())).decode('ascii')

            sources.append({
                'type': 'file',
                'url': url,
                'sha512': sha512,
                'dest': args.destdir,
                'dest-filename': filename,
            })

    with open(args.output, 'w') as fp:
        json.dump(
            sorted(sources, key=lambda n: n.get("dest-filename")),
            fp,
            indent=4
        )


if __name__ == '__main__':
    main()
