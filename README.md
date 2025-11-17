# yt-jsc-youtubei

## Description

A `yt-dlp` plugin that uses `youtubei.js` to extract and solve `JsChallenge` for Youtube

## Installation

Clone the repo and perform `pip install .` at the repo top dir.

```sh
git clone https://github.com/alive4ever/yt-jsc-youtubei
cd yt-jsc-youtubei
git submodule init
git submodule update
pip install .
```

Or directly using `pip`

```sh
pip install git+https://github.com/alive4ever/yt-jsc-youtubei
```

Or via pypi (when it is available).

```sh
pip install yt-jsc-youtubei
```

## Usage

The `yt-jsc-youtubei` has priority score of `50`, which means it will be executed last. For comparison, the built-in `deno ejs` has `1000` scores.

The supported js runtimes are `[ 'deno', 'node', 'bun' ]` and will be tried automatically in that order.

In order to use `deno`, `--no-js-runtimes` argument is needed to avoid `ejs` taking over the challenge. For other js runtimes (`node` and `bun`), this plugin will be used automatically. No configuration is needed.

## Acknowledgments

Thanks to `@LuanRT` for `youtubei.js` package and `yt-dlp` teams for the main package.

