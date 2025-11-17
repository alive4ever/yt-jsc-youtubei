from yt_dlp.extractor.youtube.jsc.provider import (
    register_provider,
    register_preference,
    JsChallengeProvider,
    JsChallengeRequest,
    JsChallengeResponse,
    JsChallengeProviderError,
    JsChallengeProviderRejectedRequest,
    JsChallengeType, 
    JsChallengeProviderResponse,
    NChallengeOutput,
    SigChallengeOutput,
)
from yt_dlp.utils import traverse_obj
import json
import os
import subprocess
import re
import typing

@register_provider
class YoutubeiJCP(JsChallengeProvider):
    PROVIDER_VERSION = '0.0.2'
    PROVIDER_NAME = 'yt-jsc-youtubei-provider'
    BUG_REPORT_LOCATION = 'https://github.com/alive4ever/yt-jsc-youtubei'
    
    _SUPPORTED_TYPES = None

    JSX_SELECTED = None
    JSX_VERSION = None

    home_dir = os.path.expanduser('~')
    yt_dlp_cache = os.path.join(home_dir, '.cache', 'yt-dlp')
    js_cachedir = os.path.join(yt_dlp_cache, 'yt-jsc-youtubei')

    def _get_js_runtime(self):
        js_runtimes = [ 'deno', 'node', 'bun' ]
        jsx_selected = ''
        jsx_version = ''
        for jsx in js_runtimes:
            try:
                test_cmd = subprocess.run([jsx, '-v'], capture_output=True)
                test_cmd.check_returncode()
                jsx_selected = jsx
                jsx_version = test_cmd.stdout.decode().strip()
                self.logger.info(f'Using runtime: {jsx} {jsx_version}')
                return [ jsx_selected, jsx_version ]
            except Exception as err:
                pass
        return [ None, None ]

    def is_available(self) -> bool:
        if self.JSX_SELECTED is None:
            self.JSX_SELECTED, self.JSX_VERSION = self._get_js_runtime()
        if self.JSX_SELECTED:
            return True
        else:
            self.logger.error('No js runtime is found. Choose one from [ deno, node, bun ]')
            return False

    def close(self):
        pass

    def _check_js_cachedir(self):
        if os.path.isdir(self.js_cachedir):
            return True
        else:
            os.makedirs(self.js_cachedir)
            self.logger.debug('Creating cache directory')
            return False

    def _check_js_extract_script(self):
        required_files = [ 'yt_js_extract.ts', 'package.json', 'package-lock.json' ]
        resource_base_dir = os.path.join(os.path.dirname(__file__), 'yt_jsc_youtubei_res')
        for filename in required_files:
            if os.path.isfile(os.path.join(self.js_cachedir, filename)):
                pass
            else:
                content = ''
                try:
                    with open(os.path.join(resource_base_dir, filename), 'r') as file:
                        content = file.read()
                except Exception as err:
                    self.logger.error(f'Unable to open resource {filename} from this plugin')
                    pass
                if content:
                    self.logger.debug(f'Got {filename} from resources: { len(content) }')
                    with open(os.path.join(self.js_cachedir, filename), 'w') as file:
                        file.write(content)
                else:
                    raise JsChallengeProviderError(f'Unable to download {filename}')

    def _resolve_js_deps(self, jsx):
        if os.path.isdir(os.path.join(self.js_cachedir, 'node_modules')):
            return True
        else:
            install_cmd = {
                    'deno': 'deno',
                    'node': 'npm',
                    'bun': 'bun',
                    }
            curdir = os.getcwd()
            os.chdir(self.js_cachedir)
            self.logger.info(f'Installing js packages using {install_cmd[self.JSX_SELECTED]}')
            result = subprocess.run([install_cmd[jsx], 'install'])
            os.chdir(curdir)
            try:
                result.check_returncode()
            except Exception as err:
                raise JsChallengeProviderError('Failure installing js packages')
            return True

    def _check_extracted_js_code(self, jsx, player_id):
        js_code_cache = os.path.join(self.js_cachedir, f'extracted_sigcode_{player_id}.js')
        if os.path.isfile(js_code_cache):
            return True
        else:
            jsx_cmd = {
                    'deno': [ 'deno', '--allow-net', '--allow-read' ],
                    'node': [ 'node' ],
                    'bun': [ 'bun' ],
                    'node_old': [ 'npx', '--yes', 'tsx' ],
                    }
            if jsx is 'node':
                major_ver_re = re.compile(r'v(\d+)?\.')
                major_ver_search = re.search(major_ver_re, self.JSX_VERSION)
                if major_ver_search:
                    major_ver = major_ver_search.group(1)
                if int(major_ver) < 22:
                    self.logger.info(f'Old node version is detected {self.JSX_VERSION} is less than 22')
                    actual_jsx = 'node_old'
                else:
                    actual_jsx = 'node'
            else:
                actual_jsx = jsx

            curdir = os.getcwd()
            os.chdir(self.js_cachedir)
            result = subprocess.run([*jsx_cmd[actual_jsx], 'yt_js_extract.ts', player_id], capture_output=True)
            os.chdir(curdir)
            try:
                result.check_returncode()
            except Exception as err:
                raise JsChallengeProviderError('Unable to extract js code')
            js_code = json.loads(result.stdout.decode())
            js_code_output = js_code.get('output')
            if js_code_output:
                with open(js_code_cache, 'w') as file:
                    file.write(js_code_output)
            else:
                raise JsChallengeProviderError('Unable to get extracted js code')
            return True

    def _get_player(self, *args, **kwargs):
        self.logger.info('Player download is handled by youtubei.js')
        return True

    def _load_extracted_js_code(self, player_id):
        js_code_cache = os.path.join(self.js_cachedir, f'extracted_sigcode_{player_id}.js')
        js_code = ''
        with open(js_code_cache, 'r') as file:
            js_code = file.read()
        if js_code:
            return js_code
        else:
            raise JsChallengeProviderError('Unable to load extracted js code.')

    def _real_bulk_solve(self, requests: list[JsChallengeRequest]) -> typing.Generator[JsChallengeProviderResponse, None, None]:

        jsx = self.JSX_SELECTED
        jsx_version = self.JSX_VERSION
        if not jsx:
            raise JsChallengeProviderError('No JS runtime is found.')
        self.logger.info(f'Using {jsx} {jsx_version} to solve YT challenges')
        self._check_js_cachedir()
        self._check_js_extract_script()
        self._resolve_js_deps(jsx)
        self.logger.debug(f'Got {len(requests)} challenges to solve.')
        for item in requests:
            if len(item.input.challenges[0]) >= 255:
                raise JsChallengeProviderRejectedRequest('Challenges longer than 255 is not supported', expected=True)

        player_id = ''
        for request in requests:
            env = request.type
            player_url = request.input.player_url
            if not player_id:
                self.logger.debug(f'Player url is {player_url}')
                player_id_re = re.compile(r'\/s\/player\/([a-fA-F0-9]+)?\/[\w\S]+?\.js')
                player_id_match = re.search(player_id_re, player_url)
                if player_id_match:
                    player_id = player_id_match.group(1)
                    self.logger.debug(f'Using player_id { player_id }')
                else:
                    raise JsChallengeProviderError('Unable to extract player_id')
            self._check_extracted_js_code(jsx, player_id)
            js_code = self._load_extracted_js_code(player_id)
            challenges = []
            for line in request.input.challenges:
                challenges.append(line.strip())
            head_code = '''
            let result = {};
            '''
            tail_code = '''
            const n_responses = {
              'type': 'result',
              'data': n_result,
            };
            const sig_responses = {
              'type': 'result',
              'data': sig_result,
            };
            result['type'] = 'result';
            result['responses'] = [ n_responses, sig_responses ];
            console.log(JSON.stringify(result));
            '''
            decrypt_code = {}
            if env is JsChallengeType.N:
                decrypt_code['n'] = f'''
            const n_challenge = {json.dumps(challenges)};
            const n_result = {{}};
            for (const n of n_challenge) {{
              n_result[n] = exportedVars.nFunction(n);
            }}
            '''.strip()
            elif env is JsChallengeType.SIG:
                decrypt_code['sig'] = f'''
            const sig_challenge = {json.dumps(challenges)};
            const sig_result = {{}};
            for (const sig of sig_challenge) {{
              sig_result[sig] = exportedVars.sigFunction(sig);
            }}
             '''.strip()
            else:
                raise JsChallengeProviderError(f'Unsupported challenge type: {env}.')
            full_decrypt_code = f"{head_code}\n{decrypt_code.get('n', 'const n_result = {};')}\n{decrypt_code.get('sig','const sig_result = {};')}\n{tail_code}"
            js_input = f'{js_code}\n{full_decrypt_code}'

            self.logger.info(f'Executing {jsx} command to decrypt {env} challenges.')
            result = subprocess.run([jsx, '-'], input=js_input.encode(), capture_output=True)
            stdout = result.stdout.decode()
            ret = result.returncode
            if ret != 0:
                
                raise JsChallengeProviderError(f'{jsx} returned unexpected error code {ret}', expected=False)
                
                yield JsChallengeProviderResponse(
                    request=request, 
                    error=JsChallengeProviderError(f'{jsx} returned error code {ret}', expected=False)
                )
                
            challenge_response = json.loads(stdout)
            if env is JsChallengeType.N:
                yield JsChallengeProviderResponse(
                    request=request, 
                    response=JsChallengeResponse(
                        type=JsChallengeType.N,
                        output=NChallengeOutput(results=traverse_obj(challenge_response, ('responses', 0, 'data'), default={}, expected_type=dict)),
                ))
            else:
                yield JsChallengeProviderResponse(
                    request=request,
                    response=JsChallengeResponse(
                        type=JsChallengeType.SIG,
                        output=SigChallengeOutput(results=traverse_obj(challenge_response, ('responses', 1, 'data'), default={}, expected_type=dict)),
                ))
        


@register_preference(YoutubeiJCP)
def my_provider_preference(provider: JsChallengeProvider, requests: list[JsChallengeRequest]) -> int:
    return 50

