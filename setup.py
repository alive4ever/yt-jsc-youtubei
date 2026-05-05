import os
import subprocess
import sys
from pathlib import Path
from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

ROOT = Path(__file__).parent.resolve()
TS_DIR = ROOT / "yt_dlp_plugins" / "extractor" / "yt_jsc_youtubei_res"
OUT_DIR = ROOT / "yt_dlp_plugins" / "extractor" / "yt_jsc_youtubei_res"
OUT_FILE = OUT_DIR / "yt_js_extract.js"

class build_py(_build_py):
    _JSX = ''
    def _check_js_runtime(self):
        runtimes = [ 'deno', 'node', 'bun' ]
        for jsx in runtimes:
            try:
                ret = subprocess.run([jsx, '-v'])
                if ret:
                    self._JSX = jsx
                    print(f'Using {jsx} for build')
                    return True
            except Exception as err:
                continue
        self._JSX = ''
        return False

    def run(self):
        has_js_runtime = self._check_js_runtime()
        if has_js_runtime:
            jsx = self._JSX
        else:
            raise SystemExit("No js runtime is found. Supported runtimes: [ deno, node, bun ].")
        install_cmd = {
                'deno': ['deno', 'install'],
                'node': ['npm', 'install', '--no-save' ],
                'bun': ['bun', 'install', '--no-save'],
                }
        exec_cmd = {
                'deno': ['deno', 'x'],
                'node': ['npx'],
                'bun': ['bun', 'x'],
                }
        try:
            if (TS_DIR.exists()):
                print("Building JS assets using esbuild...", file=sys.stderr)
                curdir = os.getcwd()
                os.chdir(str(TS_DIR))
                subprocess.check_call(install_cmd[jsx])
                OUT_DIR.mkdir(parents=True, exist_ok=True)
                subprocess.check_call([
                    *exec_cmd[jsx], "-y", "esbuild",
                    str(TS_DIR / "yt_js_extract.ts"),
                    "--bundle",
                    "--target=node18",
                    "--format=esm",
                    "--outfile=" + str(OUT_FILE),
                ])
                os.chdir(curdir)
            else:
                print("TS source not found, skipping JS build.", file=sys.stderr)
        except subprocess.CalledProcessError as e:
            raise SystemExit(f"JS build failed: {e}") from e

        if not OUT_FILE.exists():
            raise SystemExit(f"Expected built file missing: {OUT_FILE}")

        super().run()

setup(
    name="yt-jsc-youtubei",
    version="0.0.4",
    packages=["yt_dlp_plugins.extractor", "yt_dlp_plugins.extractor.yt_jsc_youtubei_res"],
    include_package_data=True,
    package_data={"yt_dlp_plugins.extractor": ["yt_jsc_youtubei_res/*"]},
    exclude_package_data={"yt_dlp_plugins.extractor": ["*/.git", "*/bun.lock", "*/deno.lock", "*/node_modules"]},
    cmdclass={"build_py": build_py},
)
